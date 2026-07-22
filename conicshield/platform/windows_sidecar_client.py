"""Native Windows client for the WSL Moreau sidecar worker.

Architecture (v1)
-----------------
* App runs in native Windows Python.
* A **persistent** worker subprocess runs Moreau inside WSL2.
* Transport is stdin/stdout NDJSON (no localhost networking).
* Multiple solves reuse one worker process.
* Worker death / incomplete responses trigger the declared
  :class:`~conicshield.platform.sidecar_protocol.FallbackPolicy` — public
  backends still pass the S2 verification gate. Unverified actions are never
  released.

This client is a **qualification** surface. Do not treat it as production-ready
until qualification notes document what passed vs remaining gaps.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import threading
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.backends.base import Backend
from conicshield.compilation.structural_fingerprint import (
    numerical_signature,
    structural_fingerprint,
)
from conicshield.core.result import ProjectionResult
from conicshield.core.solver_factory import create_projector
from conicshield.platform.paths import (
    detect_wsl_exe,
    is_windows_host,
    repo_root_candidates,
    windows_path_to_wsl,
)
from conicshield.platform.sidecar_protocol import (
    PROTOCOL_VERSION,
    FallbackPolicy,
    MessageType,
    SidecarProtocolError,
    SolveRequest,
    SolveResultMessage,
    decode_message,
    encode_message,
    hello_message,
)
from conicshield.specs.schema import SafetySpec
from conicshield.verification.fallback import FallbackAttempt
from conicshield.verification.feasibility import VerificationReleaseError
from conicshield.verification.release_policy import ReleaseDecision


class SidecarWorkerError(RuntimeError):
    """Worker process died, timed out, or returned an unusable response."""

    def __init__(self, message: str, *, evidence: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.evidence = dict(evidence or {})


@dataclass(slots=True)
class SidecarOverheadSample:
    """One measured client-side overhead sample around a sidecar round-trip."""

    trace_id: str
    client_wait_ms: float
    worker_reported_overhead_ms: float | None
    worker_solve_ms: float | None
    used_fallback: bool
    fallback_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "client_wait_ms": self.client_wait_ms,
            "worker_reported_overhead_ms": self.worker_reported_overhead_ms,
            "worker_solve_ms": self.worker_solve_ms,
            "used_fallback": self.used_fallback,
            "fallback_reason": self.fallback_reason,
        }


@dataclass(slots=True)
class SidecarClientConfig:
    """Startup / restart / fallback policy for the Windows sidecar client."""

    fallback_policy: FallbackPolicy = FallbackPolicy.PUBLIC_CLARABEL
    max_restarts: int = 2
    restart_backoff_sec: float = 0.25
    hello_timeout_sec: float = 30.0
    solve_timeout_sec: float = 60.0
    wsl_distro: str | None = None
    repo_root: Path | None = None
    python_executable: str = "python3"
    require_moreau_on_hello: bool = False
    # When True, start the worker via wsl.exe even if already on Linux (tests).
    force_wsl_launcher: bool = False
    # Test seam: override process spawn (must return a Popen-like object).
    spawn_factory: Any | None = None


@dataclass(slots=True)
class WindowsSidecarClient:
    """Own one persistent Moreau worker; reuse it across solves."""

    config: SidecarClientConfig = field(default_factory=SidecarClientConfig)
    _proc: subprocess.Popen[Any] | None = field(default=None, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _client_id: str = field(default_factory=lambda: f"win-client-{uuid.uuid4().hex[:10]}")
    _worker_id: str | None = field(default=None, init=False)
    _restarts: int = field(default=0, init=False)
    _started: bool = field(default=False, init=False)
    overhead_samples: list[SidecarOverheadSample] = field(default_factory=list)

    # --- lifecycle ---------------------------------------------------------

    def start(self) -> dict[str, Any]:
        """Start (or restart) the worker and complete the hello handshake."""
        with self._lock:
            self._stop_unlocked(send_shutdown=False)
            self._proc = self._spawn_worker()
            assert self._proc is not None
            ack = self._handshake_unlocked()
            self._started = True
            return ack

    def close(self) -> None:
        with self._lock:
            self._stop_unlocked(send_shutdown=True)

    def __enter__(self) -> WindowsSidecarClient:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def _repo_root(self) -> Path:
        if self.config.repo_root is not None:
            return Path(self.config.repo_root).resolve()
        return repo_root_candidates()[0]

    def _spawn_worker(self) -> subprocess.Popen[Any]:
        if self.config.spawn_factory is not None:
            return self.config.spawn_factory()  # type: ignore[no-any-return]
        root = self._repo_root()
        use_wsl = is_windows_host() or self.config.force_wsl_launcher
        if use_wsl:
            wsl = detect_wsl_exe()
            if wsl is None:
                raise SidecarWorkerError(
                    "wsl.exe not found; Windows Moreau sidecar requires WSL2",
                    evidence={"mode": "windows_moreau_sidecar"},
                )
            linux_root = windows_path_to_wsl(root)
            # One persistent bash+python process; no per-solve wsl.exe relaunch.
            distro_args: list[str] = []
            if self.config.wsl_distro:
                distro_args = ["-d", self.config.wsl_distro]
            require_flag = " --require-moreau" if self.config.require_moreau_on_hello else ""
            # Quote carefully for bash -lc.
            inner = (
                f"cd {repr(linux_root)} && "
                f"exec {self.config.python_executable} -m conicshield.workers.moreau_worker"
                f"{require_flag}"
            )
            cmd = [wsl, *distro_args, "-e", "bash", "-lc", inner]
        else:
            cmd = [
                self.config.python_executable,
                "-m",
                "conicshield.workers.moreau_worker",
            ]
            if self.config.require_moreau_on_hello:
                cmd.append("--require-moreau")

        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")
        return subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(root) if not use_wsl else None,
            env=env,
            bufsize=0,
        )

    def _stop_unlocked(self, *, send_shutdown: bool) -> None:
        proc = self._proc
        self._proc = None
        self._started = False
        self._worker_id = None
        if proc is None:
            return
        try:
            if send_shutdown and proc.poll() is None and proc.stdin is not None:
                proc.stdin.write(
                    encode_message({"type": MessageType.SHUTDOWN.value, "protocol_version": PROTOCOL_VERSION})
                )
                proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            with contextlib.suppress(subprocess.TimeoutExpired):
                proc.wait(timeout=2.0)

    def _handshake_unlocked(self) -> dict[str, Any]:
        assert self._proc is not None
        self._write(hello_message(client_id=self._client_id, fallback_policy=self.config.fallback_policy))
        payload = self._read(timeout_sec=self.config.hello_timeout_sec)
        if payload.get("type") != MessageType.HELLO_ACK.value:
            raise SidecarWorkerError(
                f"expected hello_ack, got {payload.get('type')!r}",
                evidence={"payload": payload},
            )
        if self.config.require_moreau_on_hello and not payload.get("moreau_available"):
            raise SidecarWorkerError(
                "worker hello_ack reports moreau_available=false",
                evidence={"payload": payload},
            )
        self._worker_id = str(payload.get("worker_id") or "")
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        proc = self._proc
        if proc is None or proc.stdin is None:
            raise SidecarWorkerError("worker stdin unavailable")
        try:
            proc.stdin.write(encode_message(payload))
            proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise SidecarWorkerError(
                f"worker pipe broken on write: {exc}",
                evidence={"reason": "worker_death_on_write"},
            ) from exc

    def _read(self, *, timeout_sec: float) -> dict[str, Any]:
        proc = self._proc
        if proc is None or proc.stdout is None:
            raise SidecarWorkerError("worker stdout unavailable")

        # Blocking readline with a watchdog thread for timeout.
        holder: dict[str, Any] = {}

        def _reader() -> None:
            try:
                assert proc.stdout is not None
                line = proc.stdout.readline()
                holder["line"] = line
            except Exception as exc:  # noqa: BLE001
                holder["error"] = exc

        thread = threading.Thread(target=_reader, daemon=True)
        thread.start()
        thread.join(timeout=timeout_sec)
        if thread.is_alive():
            raise SidecarWorkerError(
                f"timed out waiting for worker response after {timeout_sec}s",
                evidence={"reason": "timeout"},
            )
        if "error" in holder:
            raise SidecarWorkerError(
                f"worker read failed: {holder['error']}",
                evidence={"reason": "read_error"},
            )
        line = holder.get("line")
        if line is None or line == b"":
            rc = proc.poll()
            raise SidecarWorkerError(
                f"worker exited during read (returncode={rc})",
                evidence={"reason": "worker_death", "returncode": rc},
            )
        try:
            return decode_message(line)
        except SidecarProtocolError as exc:
            raise SidecarWorkerError(
                f"incomplete or invalid worker response: {exc}",
                evidence={"reason": "protocol_error", "raw": line[:500]},
            ) from exc

    def _ensure_running(self) -> None:
        if self.is_running and self._started:
            return
        if self._restarts > self.config.max_restarts:
            raise SidecarWorkerError(
                f"worker restart budget exhausted ({self.config.max_restarts})",
                evidence={"reason": "restart_budget"},
            )
        if self._started or self._proc is not None:
            self._restarts += 1
            time.sleep(self.config.restart_backoff_sec * max(1, self._restarts))
        self.start()

    # --- solve path --------------------------------------------------------

    def project(
        self,
        spec: SafetySpec,
        proposed_action: np.ndarray | Sequence[float],
        previous_action: np.ndarray | Sequence[float] | None = None,
        *,
        reference_action: np.ndarray | Sequence[float] | None = None,
        policy_weight: float = 1.0,
        reference_weight: float = 0.0,
        row_ids: Sequence[str] = (),
        deadline_ms: int | None = None,
        backend: Backend | str = Backend.NATIVE_MOREAU,
        metadata: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> ProjectionResult:
        """Solve via sidecar; on worker death apply declared public fallback.

        Never releases an action from an incomplete/unverified worker response.
        """
        tid = trace_id or uuid.uuid4().hex
        proposed = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        t0 = time.perf_counter()

        try:
            with self._lock:
                self._ensure_running()
                fp = structural_fingerprint(spec, backend=str(backend))
                num = numerical_signature(spec)
                request = SolveRequest(
                    trace_id=tid,
                    spec=spec.model_dump(mode="json"),
                    proposed_action=proposed.tolist(),
                    structural_fingerprint=fp.digest,
                    numerical_parameters={"digest": num.digest},
                    previous_action=(
                        None
                        if previous_action is None
                        else np.asarray(previous_action, dtype=np.float64).reshape(-1).tolist()
                    ),
                    reference_action=(
                        None
                        if reference_action is None
                        else np.asarray(reference_action, dtype=np.float64).reshape(-1).tolist()
                    ),
                    policy_weight=policy_weight,
                    reference_weight=reference_weight,
                    row_ids=tuple(row_ids),
                    deadline_ms=deadline_ms,
                    backend=str(backend),
                    metadata=dict(metadata or {}),
                )
                self._write(request.to_message())
                timeout = self.config.solve_timeout_sec
                if deadline_ms is not None:
                    timeout = min(timeout, max(0.05, deadline_ms / 1000.0))
                payload = self._read(timeout_sec=timeout)
                if payload.get("type") == MessageType.ERROR.value:
                    raise SidecarWorkerError(
                        str(payload.get("error") or "worker error"),
                        evidence={"payload": payload, "reason": "worker_error"},
                    )
                result_msg = SolveResultMessage.from_message(payload)
                wait_ms = (time.perf_counter() - t0) * 1000.0
                if not result_msg.ok or not result_msg.verification_complete:
                    # Fail closed on this attempt — may still public-fallback below.
                    raise SidecarWorkerError(
                        result_msg.error or "worker returned unverified/failed solve",
                        evidence={
                            "reason": result_msg.error_code or "unverified",
                            "verification_complete": result_msg.verification_complete,
                            "result": result_msg.result,
                        },
                    )
                projection = _projection_from_payload(result_msg.result or {})
                self.overhead_samples.append(
                    SidecarOverheadSample(
                        trace_id=tid,
                        client_wait_ms=wait_ms,
                        worker_reported_overhead_ms=result_msg.overhead_ms,
                        worker_solve_ms=result_msg.worker_solve_ms,
                        used_fallback=False,
                    )
                )
                # Annotate sidecar overhead on metadata (non-protected keys only).
                projection.metadata = {
                    **dict(projection.metadata),
                    "sidecar_overhead": {
                        "client_wait_ms": wait_ms,
                        "worker_overhead_ms": result_msg.overhead_ms,
                        "worker_solve_ms": result_msg.worker_solve_ms,
                        "protocol_version": PROTOCOL_VERSION,
                        "worker_id": self._worker_id,
                    },
                }
                return projection
        except SidecarWorkerError as exc:
            wait_ms = (time.perf_counter() - t0) * 1000.0
            return self._apply_fallback(
                spec=spec,
                proposed=proposed,
                previous_action=previous_action,
                reference_action=reference_action,
                policy_weight=policy_weight,
                reference_weight=reference_weight,
                metadata=metadata,
                trace_id=tid,
                wait_ms=wait_ms,
                cause=exc,
            )

    def _apply_fallback(
        self,
        *,
        spec: SafetySpec,
        proposed: np.ndarray,
        previous_action: np.ndarray | Sequence[float] | None,
        reference_action: np.ndarray | Sequence[float] | None,
        policy_weight: float,
        reference_weight: float,
        metadata: dict[str, Any] | None,
        trace_id: str,
        wait_ms: float,
        cause: SidecarWorkerError,
    ) -> ProjectionResult:
        policy = self.config.fallback_policy
        reason = str((cause.evidence or {}).get("reason") or "sidecar_failure")
        if policy is FallbackPolicy.FAIL_CLOSED:
            self.overhead_samples.append(
                SidecarOverheadSample(
                    trace_id=trace_id,
                    client_wait_ms=wait_ms,
                    worker_reported_overhead_ms=None,
                    worker_solve_ms=None,
                    used_fallback=False,
                    fallback_reason=reason,
                )
            )
            raise VerificationReleaseError(
                f"sidecar failed and fallback_policy=fail_closed: {cause}",
                evidence={
                    "sidecar_error": str(cause),
                    "sidecar_evidence": cause.evidence,
                    "fallback_policy": str(policy),
                    "trace_id": trace_id,
                },
            )

        backend = Backend.PUBLIC_CLARABEL if policy is FallbackPolicy.PUBLIC_CLARABEL else Backend.PUBLIC_SCS
        # Attempt a bounded worker restart for subsequent solves; current request
        # uses public fallback and must still pass S2 verification.
        try:
            with self._lock:
                if self._restarts < self.config.max_restarts:
                    self._restarts += 1
                    time.sleep(self.config.restart_backoff_sec)
                    with contextlib.suppress(SidecarWorkerError):
                        self.start()
        except SidecarWorkerError:
            pass

        projector = create_projector(spec=spec, backend=backend)
        result = projector.project(
            proposed,
            None if previous_action is None else np.asarray(previous_action, dtype=np.float64).reshape(-1),
            reference_action=(
                None if reference_action is None else np.asarray(reference_action, dtype=np.float64).reshape(-1)
            ),
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            metadata={
                **dict(metadata or {}),
                "sidecar_fallback": True,
                "sidecar_fallback_policy": str(policy),
                "sidecar_failure_reason": reason,
                "sidecar_trace_id": trace_id,
            },
        )
        # Public projector already ran S2 verification. Record sidecar death as
        # an additional fallback history entry for evidence continuity.
        history = list(result.fallback_history)
        history.append(
            FallbackAttempt(
                kind="sidecar_worker_death_public_fallback",
                raw_status=None,
                canonical_status=None if result.canonical_status is None else str(result.canonical_status),
                decision=str(result.release_decision or ReleaseDecision.ACCEPTED_FALLBACK),
                elapsed_sec=wait_ms / 1000.0,
                reason=f"{reason}: {cause}",
            )
        )
        result.fallback_history = tuple(history)
        if result.verification is None or not result.verification.passed:
            raise VerificationReleaseError(
                "public fallback after sidecar failure did not produce a verified action",
                report=result.verification,
                evidence={
                    "sidecar_error": str(cause),
                    "sidecar_evidence": cause.evidence,
                    "fallback_policy": str(policy),
                    "trace_id": trace_id,
                },
            )
        self.overhead_samples.append(
            SidecarOverheadSample(
                trace_id=trace_id,
                client_wait_ms=wait_ms,
                worker_reported_overhead_ms=None,
                worker_solve_ms=None,
                used_fallback=True,
                fallback_reason=reason,
            )
        )
        return result

    def overhead_report(self) -> dict[str, Any]:
        samples = [s.as_dict() for s in self.overhead_samples]
        waits = [s.client_wait_ms for s in self.overhead_samples]
        return {
            "protocol_version": PROTOCOL_VERSION,
            "sample_count": len(samples),
            "client_wait_ms_mean": None if not waits else float(sum(waits) / len(waits)),
            "client_wait_ms_max": None if not waits else float(max(waits)),
            "fallback_count": sum(1 for s in self.overhead_samples if s.used_fallback),
            "samples": samples,
        }


def _projection_from_payload(payload: dict[str, Any]) -> ProjectionResult:
    """Rebuild a ProjectionResult from a worker ``as_dict`` payload.

    Trust boundary: caller must already have checked ``verification_complete``.
    We still refuse to build a result without verification + release_decision.
    """
    from conicshield.backends.status import CanonicalSolverStatus
    from conicshield.verification.feasibility import VerificationReport
    from conicshield.verification.provenance import SolverProvenance
    from conicshield.verification.release_policy import ReleaseClassification, ReleaseDecision
    from conicshield.verification.residuals import ResidualReport

    if not payload.get("verification") or not payload.get("release_decision"):
        raise SidecarWorkerError(
            "refusing to materialize ProjectionResult without verification evidence",
            evidence={"reason": "missing_verification"},
        )

    ver_raw = payload["verification"]
    residual_raw = ver_raw.get("residual_report") or {}
    rate_raw = residual_raw.get("rate_residuals")
    residual = ResidualReport(
        finite=bool(residual_raw.get("finite", False)),
        action_dim_ok=bool(residual_raw.get("action_dim_ok", False)),
        simplex_residual=float(residual_raw.get("simplex_residual", 0.0)),
        lower_residuals=np.asarray(residual_raw.get("lower_residuals") or [], dtype=np.float64),
        upper_residuals=np.asarray(residual_raw.get("upper_residuals") or [], dtype=np.float64),
        prohibited_residuals=np.asarray(residual_raw.get("prohibited_residuals") or [], dtype=np.float64),
        rate_residuals=(None if rate_raw is None else np.asarray(rate_raw, dtype=np.float64)),
        max_equality_residual=float(residual_raw.get("max_equality_residual", 0.0)),
        max_inequality_residual=float(residual_raw.get("max_inequality_residual", 0.0)),
        objective_residual=(
            None if residual_raw.get("objective_residual") is None else float(residual_raw["objective_residual"])
        ),
        details={str(k): float(v) for k, v in dict(residual_raw.get("details") or {}).items()},
    )
    class_raw = ver_raw.get("classification") or {}
    classification = ReleaseClassification(
        decision=ReleaseDecision(str(class_raw.get("decision"))),
        reasons=tuple(class_raw.get("reasons") or ()),
    )
    verification = VerificationReport(
        passed=bool(ver_raw.get("passed")),
        canonical_status=CanonicalSolverStatus(str(ver_raw.get("canonical_status"))),
        residual_report=residual,
        classification=classification,
        active_constraints=tuple(ver_raw.get("active_constraints") or ()),
        notes=tuple(ver_raw.get("notes") or ()),
    )
    if not verification.passed:
        raise SidecarWorkerError(
            "worker payload verification.passed is false",
            evidence={"reason": "unverified"},
        )

    provenance = None
    if payload.get("solver_provenance"):
        provenance = SolverProvenance(
            **{
                k: v
                for k, v in dict(payload["solver_provenance"]).items()
                if k in SolverProvenance.__dataclass_fields__
            }
        )

    history = tuple(
        FallbackAttempt(
            kind=str(h.get("kind")),
            raw_status=h.get("raw_status"),
            canonical_status=h.get("canonical_status"),
            decision=str(h.get("decision")),
            elapsed_sec=float(h.get("elapsed_sec", 0.0)),
            reason=h.get("reason"),
        )
        for h in (payload.get("fallback_history") or [])
    )

    return ProjectionResult(
        proposed_action=np.asarray(payload["proposed_action"], dtype=np.float64),
        corrected_action=np.asarray(payload["corrected_action"], dtype=np.float64),
        intervened=bool(payload.get("intervened")),
        intervention_norm=float(payload.get("intervention_norm", 0.0)),
        solver_status=str(payload.get("solver_status")),
        objective_value=payload.get("objective_value"),
        active_constraints=list(payload.get("active_constraints") or []),
        warm_started=bool(payload.get("warm_started", False)),
        solve_time_sec=payload.get("solve_time_sec"),
        setup_time_sec=payload.get("setup_time_sec"),
        iterations=payload.get("iterations"),
        construction_time_sec=payload.get("construction_time_sec"),
        device=payload.get("device"),
        metadata=dict(payload.get("metadata") or {}),
        canonical_status=CanonicalSolverStatus(str(payload["canonical_status"]))
        if payload.get("canonical_status")
        else verification.canonical_status,
        release_decision=ReleaseDecision(str(payload["release_decision"])),
        verification=verification,
        solver_provenance=provenance,
        fallback_history=history,
    )


def start_sidecar_from_env() -> WindowsSidecarClient:
    """One-command helper: construct + start using environment overrides."""
    cfg = SidecarClientConfig(
        fallback_policy=FallbackPolicy(
            os.environ.get("CONICSHIELD_SIDECAR_FALLBACK", FallbackPolicy.PUBLIC_CLARABEL.value)
        ),
        wsl_distro=os.environ.get("CONICSHIELD_WSL_DISTRO") or None,
        python_executable=os.environ.get("CONICSHIELD_WSL_PYTHON", "python3"),
        require_moreau_on_hello=os.environ.get("CONICSHIELD_SIDECAR_REQUIRE_MOREAU", "").lower()
        in {"1", "true", "yes"},
    )
    root = os.environ.get("CONICSHIELD_REPO_ROOT")
    if root:
        cfg.repo_root = Path(root)
    client = WindowsSidecarClient(config=cfg)
    client.start()
    return client

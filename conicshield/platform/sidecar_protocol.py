"""Versioned Moreau sidecar protocol (stdin/stdout JSON Lines).

Wire transport is a **persistent subprocess** pipe — not localhost TCP.
Native Windows hosts the client; the worker process runs under WSL2 (or Linux).

Protocol versioning (v2)
------------------------
* ``PROTOCOL_VERSION`` is the wire version this build speaks.
* Clients and workers negotiate via ``supported_protocol_versions`` on hello /
  hello_ack and must reject empty intersections (fail closed).
* v2 requires cryptographic **request binding**: clients attach
  ``request_binding_digest``; workers recompute and reject mismatches.
* hello_ack and solve_result carry worker / solver **provenance** fields.
* Bumping the version requires a coordinated client+worker change.

This module defines message shapes only; it does not start processes.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# Wire protocol version. Bump only with coordinated client/worker changes.
PROTOCOL_VERSION: int = 2
MIN_SUPPORTED_PROTOCOL_VERSION: int = 2
SUPPORTED_PROTOCOL_VERSIONS: tuple[int, ...] = (2,)

# Framing: one JSON object per line, UTF-8, terminated by ``\\n``.
CONTENT_TYPE = "application/x-ndjson; charset=utf-8"


class MessageType(StrEnum):
    HELLO = "hello"
    HELLO_ACK = "hello_ack"
    SOLVE = "solve"
    SOLVE_RESULT = "solve_result"
    CANCEL = "cancel"
    CANCEL_ACK = "cancel_ack"
    PING = "ping"
    PONG = "pong"
    SHUTDOWN = "shutdown"
    ERROR = "error"


class SidecarProtocolError(ValueError):
    """Malformed, version-mismatched, or otherwise illegal protocol payload."""


class FallbackPolicy(StrEnum):
    """Declared recovery when the sidecar worker dies or cannot complete a solve.

    Public fallback still runs the S2 verification gate before any release.
    """

    PUBLIC_CLARABEL = "public_clarabel"
    PUBLIC_SCS = "public_scs"
    FAIL_CLOSED = "fail_closed"


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def negotiate_protocol_version(
    client_supported: Sequence[int],
    worker_supported: Sequence[int] | None = None,
) -> int:
    """Return the highest mutually supported protocol version (fail closed)."""

    worker = tuple(SUPPORTED_PROTOCOL_VERSIONS if worker_supported is None else worker_supported)
    client = tuple(int(v) for v in client_supported)
    worker_i = tuple(int(v) for v in worker)
    common = sorted(set(client) & set(worker_i), reverse=True)
    if not common:
        raise SidecarProtocolError(
            f"protocol version negotiation failed: client={list(client)} worker={list(worker_i)}"
        )
    chosen = int(common[0])
    if chosen < MIN_SUPPORTED_PROTOCOL_VERSION:
        raise SidecarProtocolError(
            f"negotiated protocol_version={chosen} below min supported {MIN_SUPPORTED_PROTOCOL_VERSION}"
        )
    return chosen


def _parse_supported_versions(raw: Any) -> tuple[int, ...]:
    if raw is None:
        # Legacy single-version speakers: treat declared protocol_version alone.
        return ()
    if not isinstance(raw, (list, tuple)):
        raise SidecarProtocolError("supported_protocol_versions must be a list")
    out: list[int] = []
    for item in raw:
        try:
            out.append(int(item))
        except (TypeError, ValueError) as exc:
            raise SidecarProtocolError(f"invalid supported_protocol_versions entry: {item!r}") from exc
    return tuple(out)


def _require_version(payload: dict[str, Any]) -> int:
    raw = payload.get("protocol_version")
    if raw is None:
        raise SidecarProtocolError("missing protocol_version")
    try:
        version = int(raw)
    except (TypeError, ValueError) as exc:
        raise SidecarProtocolError(f"invalid protocol_version: {raw!r}") from exc
    if version != PROTOCOL_VERSION:
        raise SidecarProtocolError(
            f"unsupported protocol_version={version}; this build speaks {PROTOCOL_VERSION}"
        )
    return version


def compute_request_binding_digest(
    *,
    structural_fingerprint: str,
    numerical_parameters: Mapping[str, Any] | None,
    proposed_action: Sequence[float],
    previous_action: Sequence[float] | None,
    reference_action: Sequence[float] | None,
    policy_weight: float,
    reference_weight: float,
    row_ids: Sequence[str] = (),
    backend: str = "native_moreau",
    trace_id: str | None = None,
) -> str:
    """Full SHA-256 binding of solve identity inputs (v2 request binding)."""

    payload = {
        "schema": "sidecar.request_binding.v2",
        "structural_fingerprint": str(structural_fingerprint),
        "numerical_parameters": dict(numerical_parameters or {}),
        "proposed_action": [float(x) for x in proposed_action],
        "previous_action": None if previous_action is None else [float(x) for x in previous_action],
        "reference_action": None if reference_action is None else [float(x) for x in reference_action],
        "policy_weight": float(policy_weight),
        "reference_weight": float(reference_weight),
        "row_ids": [str(x) for x in row_ids],
        "backend": str(backend),
        "trace_id": None if trace_id is None else str(trace_id),
    }
    return sha256_hex(_canonical_json_bytes(payload))


def validate_request_binding(
    *,
    declared_digest: str | None,
    structural_fingerprint: str,
    numerical_parameters: Mapping[str, Any] | None,
    proposed_action: Sequence[float],
    previous_action: Sequence[float] | None,
    reference_action: Sequence[float] | None,
    policy_weight: float,
    reference_weight: float,
    row_ids: Sequence[str] = (),
    backend: str = "native_moreau",
    trace_id: str | None = None,
) -> str:
    """Recompute binding digest and fail closed on missing/mismatched digests."""

    if not declared_digest or not isinstance(declared_digest, str):
        raise SidecarProtocolError("missing request_binding_digest (required in protocol v2)")
    expected = compute_request_binding_digest(
        structural_fingerprint=structural_fingerprint,
        numerical_parameters=numerical_parameters,
        proposed_action=proposed_action,
        previous_action=previous_action,
        reference_action=reference_action,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        row_ids=row_ids,
        backend=backend,
        trace_id=trace_id,
    )
    if declared_digest != expected:
        raise SidecarProtocolError(
            f"request_binding_digest mismatch: declared={declared_digest} recomputed={expected}"
        )
    return expected


def worker_provenance_snapshot(*, moreau_available: bool | None = None) -> dict[str, Any]:
    """Minimal worker-side provenance for hello_ack / solve_result (research + qualification)."""

    moreau_version: str | None = None
    if moreau_available is None:
        try:
            import moreau  # type: ignore[import-not-found]

            moreau_available = True
            moreau_version = getattr(moreau, "__version__", None)
        except Exception:  # noqa: BLE001
            moreau_available = False
    elif moreau_available:
        try:
            import moreau  # type: ignore[import-not-found]

            moreau_version = getattr(moreau, "__version__", None)
        except Exception:  # noqa: BLE001
            moreau_version = None
    return {
        "operating_system": platform.system(),
        "platform": sys.platform,
        "python_version": platform.python_version(),
        "protocol_version": PROTOCOL_VERSION,
        "supported_protocol_versions": list(SUPPORTED_PROTOCOL_VERSIONS),
        "moreau_available": bool(moreau_available),
        "moreau_version": moreau_version,
    }


def protocol_v2_features_complete() -> bool:
    """True when this module exposes the v2 negotiation + binding surface."""

    return (
        int(PROTOCOL_VERSION) >= 2
        and callable(compute_request_binding_digest)
        and callable(negotiate_protocol_version)
        and callable(validate_request_binding)
        and callable(worker_provenance_snapshot)
        and MIN_SUPPORTED_PROTOCOL_VERSION >= 2
        and 2 in SUPPORTED_PROTOCOL_VERSIONS
    )


def encode_message(payload: dict[str, Any]) -> bytes:
    """Serialize a message dict to a single NDJSON line (includes trailing newline)."""
    if "protocol_version" not in payload:
        payload = {**payload, "protocol_version": PROTOCOL_VERSION}
    else:
        _require_version(payload)
    line = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, default=str)
    return (line + "\n").encode("utf-8")


def decode_message(raw: bytes | str) -> dict[str, Any]:
    """Parse one NDJSON line into a dict; enforce protocol version."""
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    text = text.strip()
    if not text:
        raise SidecarProtocolError("empty message")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SidecarProtocolError(f"invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SidecarProtocolError("message must be a JSON object")
    _require_version(payload)
    msg_type = payload.get("type")
    if not msg_type:
        raise SidecarProtocolError("missing message type")
    return payload


@dataclass(frozen=True, slots=True)
class SolveRequest:
    """Client → worker solve envelope.

    ``structural_fingerprint`` and ``numerical_parameters`` travel as opaque
    digests/maps so the worker can validate cache identity without re-deriving
    topology from free-form metadata alone.

    v2 requires ``request_binding_digest`` covering fingerprint + numerical
    parameters + actions + weights + row_ids + backend (+ optional trace_id).
    """

    trace_id: str
    spec: dict[str, Any]
    proposed_action: list[float]
    structural_fingerprint: str
    numerical_parameters: dict[str, Any] = field(default_factory=dict)
    previous_action: list[float] | None = None
    reference_action: list[float] | None = None
    policy_weight: float = 1.0
    reference_weight: float = 0.0
    row_ids: tuple[str, ...] = ()
    deadline_ms: int | None = None
    backend: str = "native_moreau"
    metadata: dict[str, Any] = field(default_factory=dict)
    request_binding_digest: str | None = None

    def binding_digest(self) -> str:
        return compute_request_binding_digest(
            structural_fingerprint=self.structural_fingerprint,
            numerical_parameters=self.numerical_parameters,
            proposed_action=self.proposed_action,
            previous_action=self.previous_action,
            reference_action=self.reference_action,
            policy_weight=self.policy_weight,
            reference_weight=self.reference_weight,
            row_ids=self.row_ids,
            backend=self.backend,
            trace_id=self.trace_id,
        )

    def with_binding(self) -> SolveRequest:
        digest = self.binding_digest()
        if self.request_binding_digest is not None and self.request_binding_digest != digest:
            raise SidecarProtocolError("request_binding_digest does not match request fields")
        return SolveRequest(
            trace_id=self.trace_id,
            spec=self.spec,
            proposed_action=list(self.proposed_action),
            structural_fingerprint=self.structural_fingerprint,
            numerical_parameters=dict(self.numerical_parameters),
            previous_action=None if self.previous_action is None else list(self.previous_action),
            reference_action=None if self.reference_action is None else list(self.reference_action),
            policy_weight=self.policy_weight,
            reference_weight=self.reference_weight,
            row_ids=self.row_ids,
            deadline_ms=self.deadline_ms,
            backend=self.backend,
            metadata=dict(self.metadata),
            request_binding_digest=digest,
        )

    def to_message(self) -> dict[str, Any]:
        bound = self if self.request_binding_digest else self.with_binding()
        return {
            "type": MessageType.SOLVE.value,
            "protocol_version": PROTOCOL_VERSION,
            "trace_id": bound.trace_id,
            "spec": bound.spec,
            "proposed_action": list(bound.proposed_action),
            "structural_fingerprint": bound.structural_fingerprint,
            "numerical_parameters": dict(bound.numerical_parameters),
            "previous_action": None if bound.previous_action is None else list(bound.previous_action),
            "reference_action": None if bound.reference_action is None else list(bound.reference_action),
            "policy_weight": float(bound.policy_weight),
            "reference_weight": float(bound.reference_weight),
            "row_ids": list(bound.row_ids),
            "deadline_ms": bound.deadline_ms,
            "backend": bound.backend,
            "metadata": dict(bound.metadata),
            "request_binding_digest": bound.request_binding_digest,
        }

    @classmethod
    def from_message(cls, payload: dict[str, Any], *, validate_binding: bool = True) -> SolveRequest:
        if payload.get("type") != MessageType.SOLVE.value:
            raise SidecarProtocolError(f"expected type=solve, got {payload.get('type')!r}")
        _require_version(payload)
        row_ids_raw = payload.get("row_ids") or []
        if not isinstance(row_ids_raw, list):
            raise SidecarProtocolError("row_ids must be a list")
        req = cls(
            trace_id=str(payload["trace_id"]),
            spec=dict(payload["spec"]),
            proposed_action=[float(x) for x in payload["proposed_action"]],
            structural_fingerprint=str(payload["structural_fingerprint"]),
            numerical_parameters=dict(payload.get("numerical_parameters") or {}),
            previous_action=(
                None if payload.get("previous_action") is None else [float(x) for x in payload["previous_action"]]
            ),
            reference_action=(
                None if payload.get("reference_action") is None else [float(x) for x in payload["reference_action"]]
            ),
            policy_weight=float(payload.get("policy_weight", 1.0)),
            reference_weight=float(payload.get("reference_weight", 0.0)),
            row_ids=tuple(str(x) for x in row_ids_raw),
            deadline_ms=(None if payload.get("deadline_ms") is None else int(payload["deadline_ms"])),
            backend=str(payload.get("backend") or "native_moreau"),
            metadata=dict(payload.get("metadata") or {}),
            request_binding_digest=(
                None
                if payload.get("request_binding_digest") is None
                else str(payload["request_binding_digest"])
            ),
        )
        if validate_binding:
            validate_request_binding(
                declared_digest=req.request_binding_digest,
                structural_fingerprint=req.structural_fingerprint,
                numerical_parameters=req.numerical_parameters,
                proposed_action=req.proposed_action,
                previous_action=req.previous_action,
                reference_action=req.reference_action,
                policy_weight=req.policy_weight,
                reference_weight=req.reference_weight,
                row_ids=req.row_ids,
                backend=req.backend,
                trace_id=req.trace_id,
            )
        return req


@dataclass(frozen=True, slots=True)
class SolveResultMessage:
    """Worker → client solve outcome.

    When ``ok`` is false, ``result`` must be omitted/null and ``error`` set.
    Clients must never treat a non-ok or incomplete message as a releasable action.

    v2 echoes ``request_binding_digest`` and may attach ``solver_provenance``.
    """

    trace_id: str
    ok: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    error_code: str | None = None
    overhead_ms: float | None = None
    worker_solve_ms: float | None = None
    verification_complete: bool = False
    row_ids: tuple[str, ...] = ()
    request_binding_digest: str | None = None
    solver_provenance: dict[str, Any] | None = None

    def to_message(self) -> dict[str, Any]:
        return {
            "type": MessageType.SOLVE_RESULT.value,
            "protocol_version": PROTOCOL_VERSION,
            "trace_id": self.trace_id,
            "ok": bool(self.ok),
            "result": self.result,
            "error": self.error,
            "error_code": self.error_code,
            "overhead_ms": self.overhead_ms,
            "worker_solve_ms": self.worker_solve_ms,
            "verification_complete": bool(self.verification_complete),
            "row_ids": list(self.row_ids),
            "request_binding_digest": self.request_binding_digest,
            "solver_provenance": None if self.solver_provenance is None else dict(self.solver_provenance),
        }

    @classmethod
    def from_message(cls, payload: dict[str, Any]) -> SolveResultMessage:
        if payload.get("type") != MessageType.SOLVE_RESULT.value:
            raise SidecarProtocolError(f"expected type=solve_result, got {payload.get('type')!r}")
        _require_version(payload)
        row_ids_raw = payload.get("row_ids") or []
        prov = payload.get("solver_provenance")
        return cls(
            trace_id=str(payload["trace_id"]),
            ok=bool(payload.get("ok")),
            result=None if payload.get("result") is None else dict(payload["result"]),
            error=None if payload.get("error") is None else str(payload["error"]),
            error_code=None if payload.get("error_code") is None else str(payload["error_code"]),
            overhead_ms=(None if payload.get("overhead_ms") is None else float(payload["overhead_ms"])),
            worker_solve_ms=(None if payload.get("worker_solve_ms") is None else float(payload["worker_solve_ms"])),
            verification_complete=bool(payload.get("verification_complete", False)),
            row_ids=tuple(str(x) for x in row_ids_raw),
            request_binding_digest=(
                None
                if payload.get("request_binding_digest") is None
                else str(payload["request_binding_digest"])
            ),
            solver_provenance=None if prov is None else dict(prov),
        )


def hello_message(*, client_id: str, fallback_policy: FallbackPolicy) -> dict[str, Any]:
    return {
        "type": MessageType.HELLO.value,
        "protocol_version": PROTOCOL_VERSION,
        "client_id": client_id,
        "fallback_policy": str(fallback_policy),
        "supported_protocol_versions": list(SUPPORTED_PROTOCOL_VERSIONS),
    }


def hello_ack_message(
    *,
    worker_id: str,
    moreau_available: bool,
    capabilities: dict[str, Any] | None = None,
    client_supported_versions: Sequence[int] | None = None,
) -> dict[str, Any]:
    negotiated = negotiate_protocol_version(
        client_supported_versions or SUPPORTED_PROTOCOL_VERSIONS,
        SUPPORTED_PROTOCOL_VERSIONS,
    )
    prov = worker_provenance_snapshot(moreau_available=moreau_available)
    caps = dict(capabilities or {})
    caps.setdefault("protocol_version", PROTOCOL_VERSION)
    caps.setdefault("supported_protocol_versions", list(SUPPORTED_PROTOCOL_VERSIONS))
    caps.setdefault("request_binding", True)
    caps.setdefault("transport", "persistent_subprocess_stdio")
    return {
        "type": MessageType.HELLO_ACK.value,
        "protocol_version": PROTOCOL_VERSION,
        "worker_id": worker_id,
        "moreau_available": bool(moreau_available),
        "capabilities": caps,
        "supported_protocol_versions": list(SUPPORTED_PROTOCOL_VERSIONS),
        "negotiated_protocol_version": negotiated,
        "worker_provenance": prov,
    }


def error_message(
    *,
    code: str,
    message: str,
    trace_id: str | None = None,
) -> dict[str, Any]:
    return {
        "type": MessageType.ERROR.value,
        "protocol_version": PROTOCOL_VERSION,
        "error_code": code,
        "error": message,
        "trace_id": trace_id,
    }

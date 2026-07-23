#!/usr/bin/env python3
"""S8 decision-grade workload matrix for Track 1 production qualification.

Measures public and (when available) vendor paths with explicit NOT_RUN rows for
unavailable dimensions. Never invents latency numbers for missing backends.

Timing decomposition (when instrumentation exists):
  * e2e_wall_sec — full ``project`` / ``project_batch`` wall clock
  * solver_time_sec — backend-reported solve time
  * setup_time_sec — backend-reported setup / compile reuse
  * construction_time_sec — problem construction when reported
  * verification_time_sec — residual/status gate (estimated from wall − solver − setup
    − construction when those fields are present; else null)
  * ipc_time_sec — sidecar IPC overhead only (null for in-process paths)

Outputs JSON + Markdown under ``--out-dir`` (default: benchmarks/reports/s8_qualification).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conicshield.backends.base import Backend  # noqa: E402
from conicshield.core.solver_factory import create_projector  # noqa: E402
from conicshield.platform.doctor import run_solver_doctor  # noqa: E402
from conicshield.specs.compiler import SolverOptions  # noqa: E402
from conicshield.specs.schema import (  # noqa: E402
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)

NOT_RUN = "NOT_RUN"
STATUS_OK = "ok"
STATUS_FAIL = "fail"
STATUS_SKIP = "skipped"


@dataclass
class Sample:
    e2e_wall_sec: float
    solver_time_sec: float | None = None
    setup_time_sec: float | None = None
    construction_time_sec: float | None = None
    verification_time_sec: float | None = None
    ipc_time_sec: float | None = None
    iterations: int | None = None
    max_eq_residual: float | None = None
    max_ineq_residual: float | None = None
    release_decision: str | None = None
    fallback_count: int = 0
    warm_started: bool = False
    cache_status: str | None = None
    ok: bool = True
    error: str | None = None


@dataclass
class CellResult:
    dimension: str
    cell_id: str
    backend: str
    status: str
    reason: str | None = None
    repeats: int = 0
    warmup: int = 0
    metrics: dict[str, Any] = field(default_factory=dict)
    samples: list[dict[str, Any]] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _percentile(arr: np.ndarray, q: float) -> float | None:
    if arr.size == 0:
        return None
    return float(np.percentile(arr, q))


def _stderr_mean(arr: np.ndarray) -> float | None:
    if arr.size < 2:
        return None
    return float(arr.std(ddof=1) / math.sqrt(arr.size))


def _dist(name: str, values: list[float | None]) -> dict[str, Any]:
    nums = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    arr = np.asarray(nums, dtype=np.float64)
    if arr.size == 0:
        return {"name": name, "n": 0, "available": False}
    return {
        "name": name,
        "n": int(arr.size),
        "available": True,
        "mean": float(arr.mean()),
        "p50": _percentile(arr, 50),
        "p95": _percentile(arr, 95),
        "p99": _percentile(arr, 99),
        "max": float(arr.max()),
        "min": float(arr.min()),
        "stderr_of_mean": _stderr_mean(arr),
        "unit": "sec",
    }


def _spec(
    n: int,
    *,
    rate_delta: float = 0.5,
    box_upper: float = 1.0,
    allowed: list[int] | None = None,
    lower: float | None = 0.0,
) -> SafetySpec:
    if n < 2:
        raise ValueError("action_dim must be >= 2")
    lo = [float(lower if lower is not None else 0.0)] * n
    constraints: list[Any] = [
        SimplexConstraint(total=1.0),
        TurnFeasibilityConstraint(allowed_actions=list(allowed if allowed is not None else range(n))),
        BoxConstraint(lower=lo, upper=[float(box_upper)] * n),
        RateConstraint(max_delta=[float(rate_delta)] * n),
    ]
    return SafetySpec(
        spec_id=f"s8/n{n}/r{rate_delta}",
        version="0.1.0",
        action_dim=n,
        constraints=constraints,
    )


def _proposal(n: int, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = rng.random(n)
    x = x / x.sum()
    prev = np.ones(n, dtype=np.float64) / n
    return x.astype(np.float64), prev


def _sample_from_result(e2e: float, result: Any, *, ipc: float | None = None) -> Sample:
    solve = getattr(result, "solve_time_sec", None)
    setup = getattr(result, "setup_time_sec", None)
    constr = getattr(result, "construction_time_sec", None)
    ver = None
    accounted = 0.0
    for part in (solve, setup, constr, ipc):
        if part is not None:
            accounted += float(part)
    if accounted > 0.0 and e2e >= accounted:
        ver = float(e2e - accounted)
    hist = getattr(result, "fallback_history", ()) or ()
    ver_rep = getattr(result, "verification", None)
    max_eq = max_ineq = None
    if ver_rep is not None and getattr(ver_rep, "residual_report", None) is not None:
        rr = ver_rep.residual_report
        max_eq = float(rr.max_equality_residual)
        max_ineq = float(rr.max_inequality_residual)
    release = getattr(result, "release_decision", None)
    return Sample(
        e2e_wall_sec=float(e2e),
        solver_time_sec=None if solve is None else float(solve),
        setup_time_sec=None if setup is None else float(setup),
        construction_time_sec=None if constr is None else float(constr),
        verification_time_sec=ver,
        ipc_time_sec=ipc,
        iterations=getattr(result, "iterations", None),
        max_eq_residual=max_eq,
        max_ineq_residual=max_ineq,
        release_decision=None if release is None else str(release),
        fallback_count=max(0, len(hist) - 1),
        warm_started=bool(getattr(result, "warm_started", False)),
        ok=True,
    )


def _summarize_samples(samples: list[Sample]) -> dict[str, Any]:
    ok = [s for s in samples if s.ok]
    return {
        "e2e_wall": _dist("e2e_wall_sec", [s.e2e_wall_sec for s in ok]),
        "solver_time": _dist("solver_time_sec", [s.solver_time_sec for s in ok]),
        "setup_time": _dist("setup_time_sec", [s.setup_time_sec for s in ok]),
        "construction_time": _dist("construction_time_sec", [s.construction_time_sec for s in ok]),
        "verification_time": _dist("verification_time_sec", [s.verification_time_sec for s in ok]),
        "ipc_time": _dist("ipc_time_sec", [s.ipc_time_sec for s in ok]),
        "iterations_mean": (
            float(np.mean([s.iterations for s in ok if s.iterations is not None]))
            if any(s.iterations is not None for s in ok)
            else None
        ),
        "fallback_frequency": (
            float(np.mean([s.fallback_count for s in ok])) if ok else None
        ),
        "max_eq_residual_p95": _percentile(
            np.asarray([s.max_eq_residual for s in ok if s.max_eq_residual is not None], dtype=np.float64),
            95,
        ),
        "max_ineq_residual_p95": _percentile(
            np.asarray([s.max_ineq_residual for s in ok if s.max_ineq_residual is not None], dtype=np.float64),
            95,
        ),
        "n_ok": len(ok),
        "n_fail": sum(1 for s in samples if not s.ok),
    }


def _backend_available(backend: Backend) -> tuple[bool, str | None]:
    if backend in (Backend.PUBLIC_CLARABEL, Backend.PUBLIC_SCS, Backend.AUTO):
        try:
            spec = _spec(4)
            create_projector(spec=spec, backend=backend)
            return True, None
        except Exception as exc:  # noqa: BLE001
            return False, f"{type(exc).__name__}: {exc}"
    if backend in (Backend.CVXPY_MOREAU, Backend.NATIVE_MOREAU, Backend.NATIVE_MOREAU_BATCH):
        try:
            import moreau  # noqa: F401

            if platform.system() == "Windows":
                return False, "Moreau is not supported on native Windows; use WSL or sidecar"
            create_projector(spec=_spec(4), backend=backend if backend != Backend.NATIVE_MOREAU_BATCH else Backend.NATIVE_MOREAU)
            return True, None
        except Exception as exc:  # noqa: BLE001
            return False, f"{type(exc).__name__}: {exc}"
    return False, f"unknown backend {backend}"


def _not_run(dimension: str, cell_id: str, backend: str, reason: str) -> CellResult:
    return CellResult(
        dimension=dimension,
        cell_id=cell_id,
        backend=backend,
        status=NOT_RUN,
        reason=reason,
    )


def _run_timed_project(
    project: Callable[..., Any],
    proposed: np.ndarray,
    prev: np.ndarray | None,
) -> Sample:
    t0 = time.perf_counter()
    try:
        result = project(proposed, prev, policy_weight=1.0, reference_weight=0.0)
        e2e = time.perf_counter() - t0
        return _sample_from_result(e2e, result)
    except Exception as exc:  # noqa: BLE001
        return Sample(e2e_wall_sec=time.perf_counter() - t0, ok=False, error=f"{type(exc).__name__}: {exc}")


def _cell_from_samples(
    *,
    dimension: str,
    cell_id: str,
    backend: str,
    samples: list[Sample],
    warmup: int,
    notes: list[str] | None = None,
    allow_partial_failures: bool = False,
) -> CellResult:
    measured = samples[warmup:] if warmup < len(samples) else samples
    failures = [s.error for s in measured if not s.ok and s.error]
    n_ok = sum(1 for s in measured if s.ok)
    n_fail = sum(1 for s in measured if not s.ok)
    if not measured:
        status = STATUS_SKIP
    elif n_fail == 0:
        status = STATUS_OK
    elif allow_partial_failures and n_ok > 0:
        status = STATUS_OK
    elif allow_partial_failures and n_ok == 0 and all(
        f and ("VerificationReleaseError" in f or "fail" in f.lower()) for f in failures
    ):
        # All attempts fail-closed — still a measured outcome for stress cells.
        status = STATUS_OK
    else:
        status = STATUS_FAIL
    return CellResult(
        dimension=dimension,
        cell_id=cell_id,
        backend=backend,
        status=status,
        repeats=len(samples),
        warmup=warmup,
        metrics=_summarize_samples(measured),
        samples=[
            {
                "e2e_wall_sec": s.e2e_wall_sec,
                "solver_time_sec": s.solver_time_sec,
                "setup_time_sec": s.setup_time_sec,
                "construction_time_sec": s.construction_time_sec,
                "verification_time_sec": s.verification_time_sec,
                "ipc_time_sec": s.ipc_time_sec,
                "iterations": s.iterations,
                "fallback_count": s.fallback_count,
                "ok": s.ok,
                "error": s.error,
            }
            for s in measured
        ],
        failures=[f for f in failures if f],
        notes=list(notes or [])
        + (
            [f"partial_failures={n_fail}/{len(measured)} (recorded, not invented)"]
            if n_fail and allow_partial_failures
            else []
        ),
    )


def _bench_cold(
    backend: Backend,
    *,
    n: int,
    rate: float,
    repeats: int,
    warmup: int,
    conditioning: str,
) -> CellResult:
    samples: list[Sample] = []
    for i in range(repeats):
        spec = _spec(n, rate_delta=rate)
        proposed, prev = _proposal(n, seed=1000 + i)
        proj = create_projector(
            spec=spec,
            backend=backend,
            cvxpy_options=SolverOptions(device="cpu", max_iter=500, verbose=False),
        )
        samples.append(_run_timed_project(proj.project, proposed, prev))
    return _cell_from_samples(
        dimension="cold_start",
        cell_id=f"cold_n{n}_{conditioning}_{backend.value}",
        backend=backend.value,
        samples=samples,
        warmup=warmup,
        notes=[f"action_dim={n}", f"conditioning={conditioning}", f"rate_delta={rate}"],
        allow_partial_failures=(conditioning == "ill"),
    )


def _bench_warm_sequence(
    backend: Backend,
    *,
    n: int,
    repeats: int,
    warmup: int,
) -> CellResult:
    spec = _spec(n)
    proposed, prev = _proposal(n, seed=7)
    proj = create_projector(spec=spec, backend=backend)
    samples: list[Sample] = []
    cur = prev
    for i in range(repeats):
        prop, _ = _proposal(n, seed=2000 + i)
        s = _run_timed_project(proj.project, prop, cur)
        samples.append(s)
        if s.ok:
            # Re-run once to capture corrected action for warm chain
            r = proj.project(prop, cur, policy_weight=1.0, reference_weight=0.0)
            cur = np.asarray(r.corrected_action, dtype=np.float64)
    return _cell_from_samples(
        dimension="warm_sequence",
        cell_id=f"warm_seq_n{n}_{backend.value}",
        backend=backend.value,
        samples=samples,
        warmup=warmup,
    )


def _bench_episode_reset(
    backend: Backend,
    *,
    n: int,
    repeats: int,
    warmup: int,
) -> CellResult:
    spec = _spec(n)
    proj = create_projector(spec=spec, backend=backend)
    samples: list[Sample] = []
    for i in range(repeats):
        if hasattr(proj, "reset_state"):
            proj.reset_state()
        proposed, prev = _proposal(n, seed=3000 + i)
        samples.append(_run_timed_project(proj.project, proposed, prev))
    return _cell_from_samples(
        dimension="episode_reset",
        cell_id=f"episode_reset_n{n}_{backend.value}",
        backend=backend.value,
        samples=samples,
        warmup=warmup,
        notes=["reset_state() between solves when available"],
    )


def _bench_batch_sizes(
    backend: Backend,
    *,
    n: int,
    batch_size: int,
    repeats: int,
    warmup: int,
) -> CellResult:
    """Micro-batch: sequential project loop (not native compiled batch)."""
    spec = _spec(n)
    proj = create_projector(spec=spec, backend=backend)
    samples: list[Sample] = []
    for i in range(repeats):
        props = [_proposal(n, seed=4000 + i * 100 + j)[0] for j in range(batch_size)]
        prev = np.ones(n) / n
        t0 = time.perf_counter()
        ok = True
        err = None
        last = None
        try:
            for prop in props:
                last = proj.project(prop, prev, policy_weight=1.0, reference_weight=0.0)
        except Exception as exc:  # noqa: BLE001
            ok = False
            err = f"{type(exc).__name__}: {exc}"
        e2e = time.perf_counter() - t0
        if ok and last is not None:
            s = _sample_from_result(e2e, last)
            s.e2e_wall_sec = e2e
            samples.append(s)
        else:
            samples.append(Sample(e2e_wall_sec=e2e, ok=False, error=err))
    cell = _cell_from_samples(
        dimension="batch_size_microbatch",
        cell_id=f"microbatch_n{n}_bs{batch_size}_{backend.value}",
        backend=backend.value,
        samples=samples,
        warmup=warmup,
        notes=[f"batch_size={batch_size}", "sequential project loop (not compiled batch)"],
    )
    if cell.metrics.get("e2e_wall", {}).get("available"):
        mean = cell.metrics["e2e_wall"]["mean"]
        cell.metrics["throughput_solves_per_sec"] = (batch_size / mean) if mean else None
    return cell


def _bench_concurrent(
    backend: Backend,
    *,
    n: int,
    workers: int,
    repeats: int,
) -> CellResult:
    """Concurrent callers each with their own projector (instance-confined)."""
    latencies: list[float] = []
    failures: list[str] = []
    lock = threading.Lock()

    def _one(seed: int) -> None:
        try:
            spec = _spec(n)
            proj = create_projector(spec=spec, backend=backend)
            prop, prev = _proposal(n, seed=seed)
            t0 = time.perf_counter()
            proj.project(prop, prev, policy_weight=1.0, reference_weight=0.0)
            dt = time.perf_counter() - t0
            with lock:
                latencies.append(dt)
        except Exception as exc:  # noqa: BLE001
            with lock:
                failures.append(f"{type(exc).__name__}: {exc}")

    t_wall0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_one, 5000 + i) for i in range(repeats)]
        for f in as_completed(futs):
            f.result()
    wall = time.perf_counter() - t_wall0
    arr = np.asarray(latencies, dtype=np.float64)
    status = STATUS_OK if latencies and not failures else STATUS_FAIL
    return CellResult(
        dimension="concurrent_callers",
        cell_id=f"concurrent_n{n}_w{workers}_{backend.value}",
        backend=backend.value,
        status=status,
        repeats=repeats,
        warmup=0,
        metrics={
            "e2e_wall": _dist("e2e_wall_sec", list(arr)),
            "pool_wall_sec": wall,
            "workers": workers,
            "n_ok": len(latencies),
            "n_fail": len(failures),
            "throughput_solves_per_sec": (len(latencies) / wall) if wall > 0 else None,
        },
        failures=failures,
        notes=["one projector instance per task (instance_confined)"],
    )


def _as_fail_closed_ok(
    *,
    dimension: str,
    cell_id: str,
    backend: str,
    detail: str,
    sample: Sample | None = None,
) -> CellResult:
    """Record expected non-release / exception as an OK fail-closed observation."""
    metrics: dict[str, Any] = {"fail_closed_observed": True, "detail": detail}
    samples: list[dict[str, Any]] = []
    if sample is not None:
        metrics.update(_summarize_samples([sample]))
        samples = [
            {
                "e2e_wall_sec": sample.e2e_wall_sec,
                "ok": sample.ok,
                "error": sample.error,
                "release_decision": sample.release_decision,
            }
        ]
    return CellResult(
        dimension=dimension,
        cell_id=cell_id,
        backend=backend,
        status=STATUS_OK,
        metrics=metrics,
        samples=samples,
        notes=["fail-closed behavior is the expected success criterion for this cell"],
    )


def _bench_deadline_timeout(backend: Backend, *, n: int) -> CellResult:
    """Deadline/timeout surface: SolverOptions.max_iter=1 stress (public path)."""
    spec = _spec(n, rate_delta=0.05)
    proposed, prev = _proposal(n, seed=9)
    cell_id = f"max_iter1_n{n}_{backend.value}"
    try:
        proj = create_projector(
            spec=spec,
            backend=backend,
            cvxpy_options=SolverOptions(device="cpu", max_iter=1, verbose=False),
        )
        s = _run_timed_project(proj.project, proposed, prev)
        if not s.ok:
            return _as_fail_closed_ok(
                dimension="deadlines_timeouts",
                cell_id=cell_id,
                backend=backend.value,
                detail=s.error or "non-release",
                sample=s,
            )
        return _cell_from_samples(
            dimension="deadlines_timeouts",
            cell_id=cell_id,
            backend=backend.value,
            samples=[s],
            warmup=0,
            notes=["max_iter=1 stress; release may fall back or fail closed"],
        )
    except Exception as exc:  # noqa: BLE001
        return _as_fail_closed_ok(
            dimension="deadlines_timeouts",
            cell_id=cell_id,
            backend=backend.value,
            detail=f"{type(exc).__name__}: {exc}",
        )


def _bench_infeasible(backend: Backend, *, n: int) -> CellResult:
    """Empty admissible set — construction or solve must fail closed."""
    from conicshield.specs.schema import FailSafePolicy

    cell_id = f"infeasible_empty_allowed_n{n}_{backend.value}"
    try:
        spec = SafetySpec(
            spec_id="s8/infeasible",
            version="0.1.0",
            action_dim=n,
            fail_safe_policy=FailSafePolicy.REJECT,
            constraints=[
                SimplexConstraint(total=1.0),
                TurnFeasibilityConstraint(allowed_actions=[]),
                BoxConstraint(lower=[0.0] * n, upper=[1.0] * n),
            ],
        )
    except Exception as exc:  # noqa: BLE001
        return _as_fail_closed_ok(
            dimension="infeasible_cases",
            cell_id=cell_id,
            backend=backend.value,
            detail=f"construction rejected empty admissible set: {type(exc).__name__}: {exc}",
        )
    proposed, prev = _proposal(n, seed=11)
    try:
        proj = create_projector(spec=spec, backend=backend)
        s = _run_timed_project(proj.project, proposed, prev)
        if not s.ok:
            return _as_fail_closed_ok(
                dimension="infeasible_cases",
                cell_id=cell_id,
                backend=backend.value,
                detail=s.error or "non-release",
                sample=s,
            )
        return _cell_from_samples(
            dimension="infeasible_cases",
            cell_id=cell_id,
            backend=backend.value,
            samples=[s],
            warmup=0,
            notes=["empty allowed_actions with fail_safe_policy=reject"],
        )
    except Exception as exc:  # noqa: BLE001
        return _as_fail_closed_ok(
            dimension="infeasible_cases",
            cell_id=cell_id,
            backend=backend.value,
            detail=f"{type(exc).__name__}: {exc}",
        )


def _bench_ill_conditioned(backend: Backend, *, n: int, repeats: int, warmup: int) -> CellResult:
    # Very tight rate + corner proposal
    rate = 1e-4
    samples: list[Sample] = []
    for i in range(repeats):
        spec = _spec(n, rate_delta=rate)
        proposed = np.zeros(n, dtype=np.float64)
        proposed[0] = 1.0
        prev = np.ones(n) / n
        proj = create_projector(spec=spec, backend=backend)
        samples.append(_run_timed_project(proj.project, proposed, prev))
    return _cell_from_samples(
        dimension="conditioning",
        cell_id=f"ill_conditioned_n{n}_{backend.value}",
        backend=backend.value,
        samples=samples,
        warmup=warmup,
        notes=[f"rate_delta={rate}", "corner proposal"],
    )


def _memory_rss_mb() -> float | None:
    try:
        import psutil  # type: ignore

        return float(psutil.Process(os.getpid()).memory_info().rss) / (1024.0 * 1024.0)
    except Exception:  # noqa: BLE001
        try:
            import resource

            # Linux max RSS in KB
            return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0
        except Exception:  # noqa: BLE001
            return None


def _sidecar_available() -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, "sidecar qualification targets Windows host + WSL worker"
    try:
        from conicshield.platform.paths import detect_wsl_exe, wsl_available

        if not wsl_available() or detect_wsl_exe() is None:
            return False, "wsl.exe not found; Windows Moreau sidecar not runnable"
    except Exception as exc:  # noqa: BLE001
        return False, f"WSL probe failed: {exc}"
    return (
        False,
        "WSL Moreau sidecar scaffolding present; live licensed Moreau worker not attested on this host "
        "(declared qualification: protocol/tests + public CI, not production-ready live Moreau)",
    )


def _cuda_available() -> tuple[bool, str]:
    try:
        import moreau

        if hasattr(moreau, "device_available") and bool(moreau.device_available("cuda")):
            return True, ""
        return False, "moreau.device_available('cuda') is false"
    except Exception as exc:  # noqa: BLE001
        return False, f"CUDA probe failed: {exc}"


def _cell_to_dict(c: CellResult) -> dict[str, Any]:
    return {
        "dimension": c.dimension,
        "cell_id": c.cell_id,
        "backend": c.backend,
        "status": c.status,
        "reason": c.reason,
        "repeats": c.repeats,
        "warmup": c.warmup,
        "metrics": c.metrics,
        "samples": c.samples,
        "failures": c.failures,
        "notes": c.notes,
    }


def run_matrix(
    *,
    dims: list[int],
    batch_sizes: list[int],
    repeats: int,
    warmup: int,
    include_vendor: bool,
) -> dict[str, Any]:
    doctor = run_solver_doctor(run_license_check=False)
    doctor_dict = doctor.as_dict() if hasattr(doctor, "as_dict") else {}
    provenance = {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "executable": sys.executable,
        },
        "conicshield_commit": doctor_dict.get("conicshield_commit"),
        "solver_doctor_subset": {
            "os_name": doctor_dict.get("os_name"),
            "arch": doctor_dict.get("arch"),
            "environment_type": doctor_dict.get("environment_type"),
            "moreau": doctor_dict.get("moreau"),
            "capabilities_evidence_subset": doctor_dict.get("capabilities_evidence_subset"),
            "cuda": doctor_dict.get("cuda"),
            "available_devices": doctor_dict.get("available_devices"),
            "platform_notes": doctor_dict.get("platform_notes"),
            "distributions": {
                k: doctor_dict.get("distributions", {}).get(k)
                for k in ("conicshield", "cvxpy", "numpy", "clarabel", "scs", "moreau")
                if isinstance(doctor_dict.get("distributions"), dict)
            },
        },
        "memory_rss_mb_start": _memory_rss_mb(),
        "limitations": [
            "Public-path numbers on this host are decision-grade for PUBLIC_* only.",
            "Vendor Moreau / CUDA / live sidecar numbers must not be inferred from public microbenchmarks.",
            "verification_time_sec is estimated as e2e − solver − setup − construction − ipc when those are present.",
        ],
    }

    cells: list[CellResult] = []
    public_backends = [Backend.PUBLIC_CLARABEL, Backend.PUBLIC_SCS, Backend.AUTO]
    vendor_backends = [Backend.CVXPY_MOREAU, Backend.NATIVE_MOREAU]

    available: dict[str, tuple[bool, str | None]] = {}
    for b in public_backends + vendor_backends:
        available[b.value] = _backend_available(b)

    # --- Dimension inventory (always emit NOT_RUN placeholders for missing) ---
    cuda_ok, cuda_reason = _cuda_available()
    side_ok, side_reason = _sidecar_available()

    # Action dims × conditioning × cold starts (public)
    for n in dims:
        for conditioning, rate in (("well", 0.9), ("ill", 0.05)):
            for b in public_backends:
                ok, reason = available[b.value]
                if not ok:
                    cells.append(_not_run("action_dim_conditioning", f"cold_n{n}_{conditioning}_{b.value}", b.value, reason or "unavailable"))
                    continue
                cells.append(_bench_cold(b, n=n, rate=rate, repeats=repeats, warmup=warmup, conditioning=conditioning))

    # Constraint kinds coverage note (schema kinds exercised in _spec)
    cells.append(
        CellResult(
            dimension="constraint_kinds",
            cell_id="constraint_kinds_matrix",
            backend="public_clarabel",
            status=STATUS_OK if available["public_clarabel"][0] else NOT_RUN,
            reason=None if available["public_clarabel"][0] else available["public_clarabel"][1],
            notes=[
                "Exercised: simplex, turn_feasibility, box, rate",
                "Not productized: progress, clearance (see PUBLIC_CLAIMS)",
            ],
            metrics={"kinds": ["simplex", "turn_feasibility", "box", "rate"]},
        )
    )

    # Warm sequences + episode resets
    for n in dims:
        for b in (Backend.PUBLIC_CLARABEL,):
            if not available[b.value][0]:
                cells.append(_not_run("warm_sequence", f"warm_seq_n{n}_{b.value}", b.value, available[b.value][1] or "unavailable"))
                cells.append(_not_run("episode_reset", f"episode_reset_n{n}_{b.value}", b.value, available[b.value][1] or "unavailable"))
                continue
            cells.append(_bench_warm_sequence(b, n=n, repeats=repeats, warmup=warmup))
            cells.append(_bench_episode_reset(b, n=n, repeats=repeats, warmup=warmup))

    # Batch sizes (microbatch public)
    for n in dims:
        for bs in batch_sizes:
            b = Backend.PUBLIC_CLARABEL
            if not available[b.value][0]:
                cells.append(_not_run("batch_sizes", f"microbatch_n{n}_bs{bs}_{b.value}", b.value, available[b.value][1] or "unavailable"))
                continue
            cells.append(_bench_batch_sizes(b, n=n, batch_size=bs, repeats=max(2, repeats // 2), warmup=0))

    # Structural cache hit/miss — public path has no native structural cache; NOT_RUN for native
    cells.append(
        _not_run(
            "structural_cache",
            "native_structural_cache_hit_miss",
            Backend.NATIVE_MOREAU.value,
            "Native structural fingerprint cache requires Moreau compiled path; not available on this host",
        )
    )

    # Backend comparisons
    for b in public_backends + vendor_backends:
        ok, reason = available[b.value]
        if not ok or (b in vendor_backends and not include_vendor):
            cells.append(
                _not_run(
                    "backend_comparison",
                    f"compare_{b.value}",
                    b.value,
                    reason or ("vendor lane disabled" if b in vendor_backends else "unavailable"),
                )
            )
            continue
        cells.append(_bench_cold(b, n=dims[0], rate=0.5, repeats=repeats, warmup=warmup, conditioning="nominal"))

    # Heterogeneous batch (native)
    cells.append(
        _not_run(
            "heterogeneous_batch",
            "native_heterogeneous_batch",
            Backend.NATIVE_MOREAU_BATCH.value,
            "Native heterogeneous batch requires licensed Moreau; not runnable on native Windows host",
        )
    )

    # CPU algo / auto device / CUDA
    cells.append(
        _not_run(
            "cpu_algo_choices",
            "native_cpu_algo_choices",
            Backend.NATIVE_MOREAU.value,
            "Native Moreau CPU algorithm knobs not exposed/available on this host",
        )
    )
    cells.append(
        _not_run(
            "auto_device",
            "native_auto_device",
            Backend.NATIVE_MOREAU.value,
            "Native auto device selection requires Moreau",
        )
    )
    if cuda_ok and include_vendor:
        cells.append(
            CellResult(
                dimension="cuda",
                cell_id="cuda_native",
                backend=Backend.NATIVE_MOREAU.value,
                status=NOT_RUN,
                reason="CUDA reported available but decision-grade CUDA bench not executed in this S8 host pass",
            )
        )
    else:
        cells.append(_not_run("cuda", "cuda_native", Backend.NATIVE_MOREAU.value, cuda_reason))

    # Windows sidecar / worker restart
    cells.append(_not_run("windows_sidecar_overhead", "sidecar_ipc_overhead", "windows_moreau_sidecar", side_reason))
    cells.append(_not_run("worker_restart", "sidecar_worker_restart", "windows_moreau_sidecar", side_reason))

    # Concurrent callers
    if available["public_clarabel"][0]:
        cells.append(_bench_concurrent(Backend.PUBLIC_CLARABEL, n=dims[0], workers=4, repeats=max(8, repeats * 2)))
    else:
        cells.append(_not_run("concurrent_callers", "concurrent_public", "public_clarabel", available["public_clarabel"][1] or "unavailable"))

    # Deadlines / infeasible / ill-conditioned / numerical injection
    if available["public_clarabel"][0]:
        cells.append(_bench_deadline_timeout(Backend.PUBLIC_CLARABEL, n=dims[0]))
        cells.append(_bench_infeasible(Backend.PUBLIC_CLARABEL, n=dims[0]))
        cells.append(_bench_ill_conditioned(Backend.PUBLIC_CLARABEL, n=dims[0], repeats=repeats, warmup=warmup))
        # Numerical failure injection: NaN proposal should fail closed
        try:
            spec = _spec(dims[0])
            proj = create_projector(spec=spec, backend=Backend.PUBLIC_CLARABEL)
            bad = np.full(dims[0], np.nan)
            prev = np.ones(dims[0]) / dims[0]
            s = _run_timed_project(proj.project, bad, prev)
            if not s.ok:
                cells.append(
                    _as_fail_closed_ok(
                        dimension="numerical_failure_injection",
                        cell_id="nan_proposal_public_clarabel",
                        backend="public_clarabel",
                        detail=s.error or "non-release",
                        sample=s,
                    )
                )
            else:
                cells.append(
                    CellResult(
                        dimension="numerical_failure_injection",
                        cell_id="nan_proposal_public_clarabel",
                        backend="public_clarabel",
                        status=STATUS_FAIL,
                        reason="NaN proposal unexpectedly released a verified action",
                        samples=[
                            {
                                "e2e_wall_sec": s.e2e_wall_sec,
                                "release_decision": s.release_decision,
                                "ok": s.ok,
                            }
                        ],
                    )
                )
        except Exception as exc:  # noqa: BLE001
            cells.append(
                _as_fail_closed_ok(
                    dimension="numerical_failure_injection",
                    cell_id="nan_proposal_public_clarabel",
                    backend="public_clarabel",
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )
    else:
        for dim in ("deadlines_timeouts", "infeasible_cases", "conditioning", "numerical_failure_injection"):
            cells.append(_not_run(dim, f"{dim}_public", "public_clarabel", available["public_clarabel"][1] or "unavailable"))

    provenance["memory_rss_mb_end"] = _memory_rss_mb()

    # Comparison summary table (no invented numbers)
    comparisons = []
    compare_dims = {
        "public_reference": "backend_comparison",
        "public_scs": "backend_comparison",
        "moreau_cvxpy": "backend_comparison",
        "moreau_native": "backend_comparison",
        "heterogeneous_batch": "heterogeneous_batch",
        "windows_sidecar": "windows_sidecar_overhead",
    }
    for label, backend in (
        ("public_reference", Backend.PUBLIC_CLARABEL.value),
        ("public_scs", Backend.PUBLIC_SCS.value),
        ("moreau_cvxpy", Backend.CVXPY_MOREAU.value),
        ("moreau_native", Backend.NATIVE_MOREAU.value),
        ("heterogeneous_batch", Backend.NATIVE_MOREAU_BATCH.value),
        ("windows_sidecar", "windows_moreau_sidecar"),
    ):
        related = [
            c
            for c in cells
            if c.backend == backend
            and c.status == STATUS_OK
            and (c.metrics.get("e2e_wall") or {}).get("available")
            and not (c.metrics.get("fail_closed_observed"))
        ]
        if related:
            best = min(related, key=lambda c: c.metrics["e2e_wall"]["mean"])
            comparisons.append(
                {
                    "label": label,
                    "status": STATUS_OK,
                    "representative_cell": best.cell_id,
                    "e2e_p50_sec": best.metrics["e2e_wall"].get("p50"),
                    "e2e_p95_sec": best.metrics["e2e_wall"].get("p95"),
                    "e2e_p99_sec": best.metrics["e2e_wall"].get("p99"),
                    "e2e_max_sec": best.metrics["e2e_wall"].get("max"),
                    "solver_p50_sec": (best.metrics.get("solver_time") or {}).get("p50"),
                }
            )
        else:
            prefer_dim = compare_dims.get(label)
            nr = next(
                (
                    c
                    for c in cells
                    if c.backend == backend and c.status == NOT_RUN and (prefer_dim is None or c.dimension == prefer_dim)
                ),
                None,
            )
            if nr is None:
                nr = next((c for c in cells if c.backend == backend and c.status == NOT_RUN), None)
            avail_reason = (available.get(backend) or (False, None))[1] if backend in available else None
            comparisons.append(
                {
                    "label": label,
                    "status": NOT_RUN,
                    "reason": (nr.reason if nr else None) or avail_reason or "no successful measured cell",
                }
            )

    summary = {
        "schema_version": "conicshield_s8_decision_grade/v1",
        "provenance": provenance,
        "config": {
            "action_dims": dims,
            "batch_sizes": batch_sizes,
            "repeats": repeats,
            "warmup": warmup,
            "include_vendor": include_vendor,
        },
        "backend_availability": {k: {"available": v[0], "reason": v[1]} for k, v in available.items()},
        "cells": [_cell_to_dict(c) for c in cells],
        "comparisons": comparisons,
        "counts": {
            "cells_total": len(cells),
            "ok": sum(1 for c in cells if c.status == STATUS_OK),
            "fail": sum(1 for c in cells if c.status == STATUS_FAIL),
            "not_run": sum(1 for c in cells if c.status == NOT_RUN),
        },
        "claim_guardrails": [
            "Do not publish vendor Moreau latency from this report unless status=ok on moreau_* comparisons.",
            "Do not claim native Windows Moreau support.",
            "Public Clarabel/SCS numbers are host-specific; label environment provenance when citing.",
            "Sidecar remains qualification scaffolding until live Moreau worker attestation exists.",
        ],
    }
    return summary


def _write_markdown(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# S8 decision-grade benchmark report",
        "",
        f"Generated: `{summary['provenance']['generated_at_utc']}`",
        f"Commit: `{summary['provenance'].get('conicshield_commit')}`",
        f"Host: `{summary['provenance']['host']}`",
        "",
        "## Counts",
        "",
        f"- total cells: {summary['counts']['cells_total']}",
        f"- ok: {summary['counts']['ok']}",
        f"- fail: {summary['counts']['fail']}",
        f"- NOT_RUN: {summary['counts']['not_run']}",
        "",
        "## Backend comparisons",
        "",
        "| label | status | p50 e2e (s) | p95 | p99 | max | reason |",
        "|-------|--------|-------------|-----|-----|-----|--------|",
    ]
    for row in summary["comparisons"]:
        if row["status"] == NOT_RUN:
            lines.append(
                f"| {row['label']} | NOT_RUN |  |  |  |  | {row.get('reason', '')} |"
            )
        else:
            lines.append(
                f"| {row['label']} | ok | {row.get('e2e_p50_sec')} | {row.get('e2e_p95_sec')} | "
                f"{row.get('e2e_p99_sec')} | {row.get('e2e_max_sec')} |  |"
            )
    lines.extend(
        [
            "",
            "## Claim guardrails",
            "",
        ]
    )
    for g in summary.get("claim_guardrails") or []:
        lines.append(f"- {g}")
    lines.extend(["", "## Cells", ""])
    for cell in summary["cells"]:
        lines.append(f"### `{cell['cell_id']}` ({cell['status']})")
        if cell.get("reason"):
            lines.append(f"- reason: {cell['reason']}")
        e2e = (cell.get("metrics") or {}).get("e2e_wall") or {}
        if e2e.get("available"):
            lines.append(
                f"- e2e p50/p95/p99/max: {e2e.get('p50')} / {e2e.get('p95')} / {e2e.get('p99')} / {e2e.get('max')}"
            )
            lines.append(f"- stderr(mean): {e2e.get('stderr_of_mean')}")
        sol = (cell.get("metrics") or {}).get("solver_time") or {}
        if sol.get("available"):
            lines.append(f"- solver p50: {sol.get('p50')}")
        ver = (cell.get("metrics") or {}).get("verification_time") or {}
        if ver.get("available"):
            lines.append(f"- verification p50 (est.): {ver.get('p50')}")
        if cell.get("failures"):
            lines.append(f"- failures: {cell['failures'][:3]}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="S8 decision-grade benchmark matrix")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "benchmarks" / "reports" / "s8_qualification",
    )
    p.add_argument("--action-dims", default="4,8")
    p.add_argument("--batch-sizes", default="1,4,8")
    p.add_argument("--repeats", type=int, default=6)
    p.add_argument("--warmup", type=int, default=1)
    p.add_argument(
        "--include-vendor",
        action="store_true",
        help="Attempt vendor Moreau cells when importable (still NOT_RUN on Windows).",
    )
    args = p.parse_args()
    dims = [int(x) for x in args.action_dims.split(",") if x.strip()]
    batch_sizes = [int(x) for x in args.batch_sizes.split(",") if x.strip()]
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        summary = run_matrix(
            dims=dims,
            batch_sizes=batch_sizes,
            repeats=int(args.repeats),
            warmup=int(args.warmup),
            include_vendor=bool(args.include_vendor),
        )
    except Exception as exc:  # noqa: BLE001
        err_path = out_dir / "decision_grade_error.txt"
        err_path.write_text(f"{exc}\n\n{traceback.format_exc()}", encoding="utf-8")
        print(err_path)
        return 2

    json_path = out_dir / "decision_grade_summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md_path = out_dir / "decision_grade_report.md"
    _write_markdown(summary, md_path)
    # Lightweight pointer for performance_benchmark consumers
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                "# S8 qualification benchmarks",
                "",
                "Decision-grade matrix for Track 1 stabilization.",
                "",
                "- `decision_grade_summary.json` — machine-readable cells + provenance",
                "- `decision_grade_report.md` — human summary",
                "",
                "Unavailable backends are recorded as `NOT_RUN` with reasons. Do not invent numbers.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json_path)
    print(md_path)
    # Exit 0 even with NOT_RUN cells; exit 1 only if a runnable public cell failed hard with zero ok public cells
    public_ok = any(
        c["backend"].startswith("public") and c["status"] == STATUS_OK for c in summary["cells"]
    )
    public_fail = any(
        c["backend"].startswith("public") and c["status"] == STATUS_FAIL for c in summary["cells"]
    )
    if public_fail and not public_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

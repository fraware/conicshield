"""Shared helpers to release only verified projection results."""

from __future__ import annotations

from typing import Any

import numpy as np

from conicshield.backends.status import CanonicalSolverStatus
from conicshield.core.result import ProjectionResult, sanitize_metadata
from conicshield.verification.fallback import FallbackAttempt, FallbackOutcome
from conicshield.verification.provenance import SolverProvenance
from conicshield.verification.release_policy import ReleasePolicy, intervention_threshold


def build_verified_projection_result(
    *,
    proposed_action: np.ndarray,
    outcome: FallbackOutcome,
    telemetry: dict[str, Any],
    provenance: SolverProvenance | None = None,
    metadata: dict[str, Any] | None = None,
    release_policy: ReleasePolicy | None = None,
) -> ProjectionResult:
    """Assemble a ``ProjectionResult`` from a verified fallback outcome.

    The corrected action is taken exclusively from the verified candidate.
    """
    policy = release_policy or ReleasePolicy()
    proposed = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
    corrected = np.asarray(outcome.candidate, dtype=np.float64).reshape(-1)
    diff = float(np.linalg.norm(corrected - proposed))
    thr = intervention_threshold(
        proposed,
        abs_tol=policy.intervention_abs_tol,
        rel_tol=policy.intervention_rel_tol,
    )
    intervened = diff > thr

    solver_status = str(telemetry.get("solver_status") or outcome.report.canonical_status.value)
    return ProjectionResult(
        proposed_action=proposed,
        corrected_action=corrected,
        intervened=intervened,
        intervention_norm=diff,
        solver_status=solver_status,
        objective_value=telemetry.get("objective_value"),
        active_constraints=list(outcome.report.active_constraints),
        warm_started=bool(telemetry.get("warm_started", False)),
        solve_time_sec=telemetry.get("solve_time_sec"),
        setup_time_sec=telemetry.get("setup_time_sec"),
        iterations=telemetry.get("iterations"),
        construction_time_sec=telemetry.get("construction_time_sec"),
        device=telemetry.get("device"),
        metadata=sanitize_metadata(metadata),
        canonical_status=outcome.report.canonical_status,
        release_decision=outcome.release_decision,
        verification=outcome.report,
        solver_provenance=provenance,
        fallback_history=tuple(outcome.history),
    )


def provenance_for_backend(
    *,
    backend_id: str,
    solver_name: str,
    device: str | None = None,
    settings: dict[str, Any] | None = None,
    warm_start_policy: str | None = None,
    package_distribution: str | None = None,
) -> SolverProvenance:
    version = None
    try:
        if package_distribution == "moreau":
            import moreau as _mod

            version = getattr(_mod, "__version__", None)
        elif package_distribution == "cvxpy":
            import cvxpy as _mod

            version = getattr(_mod, "__version__", None)
    except Exception:
        version = None
    return SolverProvenance(
        backend_id=backend_id,
        solver_name=solver_name,
        solver_version=None if version is None else str(version),
        package_distribution=package_distribution,
        package_version=None if version is None else str(version),
        device=device,
        settings=dict(settings or {}),
        warm_start_policy=warm_start_policy,
    )


def history_as_dicts(history: tuple[FallbackAttempt, ...]) -> list[dict[str, Any]]:
    return [h.as_dict() for h in history]


def status_value(status: CanonicalSolverStatus | None) -> str | None:
    return None if status is None else str(status)

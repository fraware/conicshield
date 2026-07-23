"""Configurable fallback with shared deadline budget and fail-safe actions."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.backends.status import CanonicalSolverStatus
from conicshield.specs.schema import FailSafePolicy
from conicshield.specs.shield_qp import ShieldQPData
from conicshield.verification.feasibility import (
    VerificationReleaseError,
    VerificationReport,
    verify_candidate_before_release,
)
from conicshield.verification.release_policy import ReleaseDecision, ReleasePolicy


@dataclass(frozen=True, slots=True)
class FallbackAttempt:
    """One recorded attempt in the release pipeline."""

    kind: str
    raw_status: str | None
    canonical_status: str | None
    decision: str
    elapsed_sec: float
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "raw_status": self.raw_status,
            "canonical_status": self.canonical_status,
            "decision": self.decision,
            "elapsed_sec": float(self.elapsed_sec),
            "reason": self.reason,
        }


@dataclass(slots=True)
class FallbackConfig:
    """Deterministic fallback ladder with a shared deadline budget."""

    enable_cold_retry: bool = True
    max_attempts: int = 4
    deadline_sec: float | None = None
    release_policy: ReleasePolicy = field(default_factory=ReleasePolicy)
    fail_safe_policy: FailSafePolicy | None = None
    # Optional public fallback: callable returning (x, raw_status, objective|None)
    public_fallback: Callable[..., tuple[np.ndarray, Any, float | None]] | None = None


@dataclass(slots=True)
class SolveAttemptResult:
    candidate: np.ndarray | None
    raw_status: Any
    objective: float | None = None
    error: BaseException | None = None
    warm_started: bool = False
    kind: str = "primary"


SolveFn = Callable[..., SolveAttemptResult]


def build_fail_safe_action(
    data: ShieldQPData,
    *,
    policy: FailSafePolicy,
    proposed_action: np.ndarray | None = None,
) -> np.ndarray:
    """Construct a declared fail-safe action (still must be verified before release)."""
    if policy is FailSafePolicy.REJECT:
        raise VerificationReleaseError(
            "fail-safe policy REJECT: refusing to synthesize an action",
            evidence={"fail_safe_policy": str(policy)},
        )

    n = int(data.n)
    allowed = np.asarray(data.allowed_mask, dtype=bool).reshape(-1)
    if not np.any(allowed):
        raise VerificationReleaseError(
            "fail-safe cannot synthesize an action: empty admissible set",
            evidence={"fail_safe_policy": str(policy)},
        )

    if policy is FailSafePolicy.UNIFORM_ADMISSIBLE:
        x = np.zeros(n, dtype=np.float64)
        idx = np.flatnonzero(allowed)
        # Seed with mid-box values on admissible coordinates, then project to simplex.
        lower = np.asarray(data.lower, dtype=np.float64)
        upper = np.asarray(data.upper, dtype=np.float64)
        mid = 0.5 * (lower + upper)
        x[idx] = mid[idx]
        # Respect prohibited coords.
        x[~allowed] = 0.0
        # Clip to box.
        x = np.minimum(np.maximum(x, lower), upper)
        x[~allowed] = 0.0
        mass = float(np.sum(x[idx]))
        target = float(data.simplex_total)
        if mass <= 0.0:
            # Fall back to equal weights on admissible indices clipped later.
            x[idx] = target / float(len(idx))
        else:
            x[idx] = x[idx] * (target / mass)
        x = np.minimum(np.maximum(x, lower), upper)
        x[~allowed] = 0.0
        # Final simplex repair on admissible support.
        mass2 = float(np.sum(x[idx]))
        if mass2 <= 0.0:
            raise VerificationReleaseError(
                "fail-safe UNIFORM_ADMISSIBLE could not form a positive mass",
                evidence={"fail_safe_policy": str(policy)},
            )
        x[idx] = x[idx] * (target / mass2)
        return x

    if policy is FailSafePolicy.CLAMPED_PROPOSED:
        if proposed_action is None:
            raise VerificationReleaseError(
                "fail-safe CLAMPED_PROPOSED requires proposed_action",
                evidence={"fail_safe_policy": str(policy)},
            )
        p = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        if p.shape[0] != n:
            raise ValueError("proposed_action length mismatch for fail-safe")
        lower = np.asarray(data.lower, dtype=np.float64)
        upper = np.asarray(data.upper, dtype=np.float64)
        x = np.minimum(np.maximum(p, lower), upper)
        x[~allowed] = 0.0
        idx = np.flatnonzero(allowed)
        mass = float(np.sum(x[idx]))
        target = float(data.simplex_total)
        if mass <= 0.0:
            x[idx] = target / float(len(idx))
        else:
            x[idx] *= target / mass
        x = np.minimum(np.maximum(x, lower), upper)
        x[~allowed] = 0.0
        mass2 = float(np.sum(x[idx]))
        if mass2 <= 0.0:
            raise VerificationReleaseError(
                "fail-safe CLAMPED_PROPOSED could not form a feasible action",
                evidence={"fail_safe_policy": str(policy)},
            )
        x[idx] *= target / mass2
        return x

    raise VerificationReleaseError(
        f"unsupported fail-safe policy: {policy!r}",
        evidence={"fail_safe_policy": str(policy)},
    )


@dataclass(slots=True)
class FallbackOutcome:
    candidate: np.ndarray
    report: VerificationReport
    history: tuple[FallbackAttempt, ...]
    release_decision: ReleaseDecision


def run_verified_release_pipeline(
    *,
    data: ShieldQPData,
    proposed_action: np.ndarray,
    previous_action: np.ndarray | None,
    reference_action: np.ndarray | None,
    policy_weight: float,
    reference_weight: float,
    primary_solve: SolveFn,
    config: FallbackConfig,
    clear_warm_start: Callable[[], None] | None = None,
    status_normalizer: Callable[[Any], CanonicalSolverStatus] | None = None,
) -> FallbackOutcome:
    """Primary → optional cold retry → public fallback → fail-safe.

    Never loops indefinitely. Every attempt consumes the shared deadline budget.
    """
    history: list[FallbackAttempt] = []
    t0 = time.perf_counter()
    attempts = 0
    max_attempts = max(1, int(config.max_attempts))
    deadline = config.deadline_sec
    last_report: VerificationReport | None = None

    def _budget_exhausted() -> bool:
        if deadline is None:
            return False
        return (time.perf_counter() - t0) >= float(deadline)

    def _record(kind: str, attempt: SolveAttemptResult, report: VerificationReport | None) -> None:
        elapsed = time.perf_counter() - t0
        history.append(
            FallbackAttempt(
                kind=kind,
                raw_status=None if attempt.raw_status is None else str(attempt.raw_status),
                canonical_status=None if report is None else str(report.canonical_status),
                decision="error" if attempt.error is not None else (
                    str(report.classification.decision) if report is not None else "no_candidate"
                ),
                elapsed_sec=elapsed,
                reason=None if attempt.error is None else f"{type(attempt.error).__name__}: {attempt.error}",
            )
        )

    def _try_candidate(
        attempt: SolveAttemptResult,
        *,
        attempt_kind: str,
    ) -> FallbackOutcome | None:
        nonlocal last_report, attempts
        attempts += 1
        if attempt.error is not None or attempt.candidate is None:
            err_status = CanonicalSolverStatus.BACKEND_ERROR
            # synthesize a nonfinite residual path for evidence
            bogus = np.array([np.nan], dtype=np.float64)
            report = verify_candidate_before_release(
                bogus if attempt.candidate is None else attempt.candidate,
                data,
                raw_status=attempt.raw_status or "backend_error",
                previous_action=previous_action,
                proposed_action=proposed_action,
                reference_action=reference_action,
                policy_weight=policy_weight,
                reference_weight=reference_weight,
                reported_objective=attempt.objective,
                policy=config.release_policy,
                attempt_kind=attempt_kind,
                status_normalizer=status_normalizer,
            )
            # Force backend-error classification when the solve raised.
            if attempt.error is not None:
                from conicshield.verification.release_policy import ReleaseClassification

                report = VerificationReport(
                    passed=False,
                    canonical_status=err_status,
                    residual_report=report.residual_report,
                    classification=ReleaseClassification(
                        ReleaseDecision.REJECTED_BACKEND_ERROR,
                        (f"solve_error:{type(attempt.error).__name__}",),
                    ),
                    active_constraints=(),
                    notes=("backend_exception",),
                )
            last_report = report
            _record(attempt_kind, attempt, report)
            return None

        report = verify_candidate_before_release(
            attempt.candidate,
            data,
            raw_status=attempt.raw_status,
            previous_action=previous_action,
            proposed_action=proposed_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            reported_objective=attempt.objective,
            policy=config.release_policy,
            attempt_kind=attempt_kind,
            status_normalizer=status_normalizer,
        )
        last_report = report
        _record(attempt_kind, attempt, report)
        if report.passed:
            return FallbackOutcome(
                candidate=np.asarray(attempt.candidate, dtype=np.float64).reshape(-1),
                report=report,
                history=tuple(history),
                release_decision=report.classification.decision,
            )
        return None

    # 1) Primary
    if attempts >= max_attempts or _budget_exhausted():
        raise VerificationReleaseError(
            "release pipeline exhausted before primary solve",
            report=last_report,
            evidence={"fallback_history": [h.as_dict() for h in history]},
        )
    primary = primary_solve(warm_start=True)
    primary.kind = "primary"
    outcome = _try_candidate(primary, attempt_kind="primary")
    if outcome is not None:
        return outcome

    # 2) Optional cold retry when warm-start primary failed policy
    if (
        config.enable_cold_retry
        and primary.warm_started
        and attempts < max_attempts
        and not _budget_exhausted()
    ):
        if clear_warm_start is not None:
            clear_warm_start()
        cold = primary_solve(warm_start=False)
        cold.kind = "cold_retry"
        outcome = _try_candidate(cold, attempt_kind="cold_retry")
        if outcome is not None:
            return outcome

    # 3) Configured public fallback
    if (
        config.public_fallback is not None
        and attempts < max_attempts
        and not _budget_exhausted()
    ):
        try:
            fx, fstatus, fobj = config.public_fallback(
                proposed_action=proposed_action,
                previous_action=previous_action,
                reference_action=reference_action,
                policy_weight=policy_weight,
                reference_weight=reference_weight,
            )
            fb = SolveAttemptResult(
                candidate=np.asarray(fx, dtype=np.float64),
                raw_status=fstatus,
                objective=fobj,
                warm_started=False,
                kind="public_fallback",
            )
        except Exception as exc:  # noqa: BLE001 — recorded as backend error attempt
            fb = SolveAttemptResult(
                candidate=None,
                raw_status="backend_error",
                objective=None,
                error=exc,
                warm_started=False,
                kind="public_fallback",
            )
        outcome = _try_candidate(fb, attempt_kind="fallback")
        if outcome is not None:
            return outcome

    # 4) Declared fail-safe
    fs_policy = config.fail_safe_policy or data.fail_safe_policy
    if (
        fs_policy is not None
        and fs_policy is not FailSafePolicy.REJECT
        and attempts < max_attempts
        and not _budget_exhausted()
    ):
        try:
            fs_x = build_fail_safe_action(
                data, policy=fs_policy, proposed_action=proposed_action
            )
            # Fail-safe actions are treated as OPTIMAL only after residual gate;
            # use a synthetic status that is acceptable only if residuals pass and
            # we mark attempt_kind=fail_safe. Status must still be acceptable —
            # use OPTIMAL for the synthetic candidate (residuals are the real gate).
            fs = SolveAttemptResult(
                candidate=fs_x,
                raw_status="optimal",
                objective=None,
                warm_started=False,
                kind="fail_safe",
            )
            outcome = _try_candidate(fs, attempt_kind="fail_safe")
            if outcome is not None:
                return outcome
        except VerificationReleaseError as exc:
            history.append(
                FallbackAttempt(
                    kind="fail_safe",
                    raw_status=None,
                    canonical_status=None,
                    decision=str(ReleaseDecision.REJECTED_BACKEND_ERROR),
                    elapsed_sec=time.perf_counter() - t0,
                    reason=str(exc),
                )
            )

    # 5) Failure event with full evidence
    raise VerificationReleaseError(
        "no verified action could be released after fallback ladder",
        report=last_report,
        evidence={
            "fallback_history": [h.as_dict() for h in history],
            "last_verification": None if last_report is None else last_report.as_dict(),
        },
    )

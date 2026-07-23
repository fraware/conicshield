"""Risk-based shadow sampling policy prototypes (Track 2 R1)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

import numpy as np

from conicshield.experimental.adapters.projection import ResearchProjectionResult


class SamplingPolicyId(StrEnum):
    RANDOM = "random"
    RESIDUAL = "residual"
    ITERATION = "iteration"
    WARM_START_REJECTION = "warm_start_rejection"
    ACTIVE_SET_CHANGE = "active_set_change"
    DISTANCE_FROM_BOUNDARIES = "distance_from_boundaries"
    GRADIENT_CONDITION = "gradient_condition"
    RECENT_FAILURES = "recent_failures"
    UNSEEN_FINGERPRINT = "unseen_fingerprint"
    SOLVER_PLATFORM_UPGRADE = "solver_platform_upgrade"


@dataclass(slots=True)
class SamplingContext:
    scenario_id: str
    structural_fingerprint: str
    primary: ResearchProjectionResult
    previous_active_set: tuple[str, ...] | None = None
    boundary_distance: float | None = None
    gradient_condition_number: float | None = None
    recent_failure_count: int = 0
    fingerprint_seen: bool = False
    upgrade_event: bool = False
    warm_start_rejected: bool = False


class SamplingPolicy(Protocol):
    policy_id: SamplingPolicyId

    def score(self, ctx: SamplingContext) -> float:
        """Higher score => more valuable to shadow-solve."""


@dataclass(slots=True)
class RandomSamplingPolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.RANDOM
    seed: int = 0

    def score(self, ctx: SamplingContext) -> float:
        rng = np.random.default_rng(abs(hash((self.seed, ctx.scenario_id))) % (2**32))
        return float(rng.random())


@dataclass(slots=True)
class ResidualSamplingPolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.RESIDUAL

    def score(self, ctx: SamplingContext) -> float:
        eq = float(ctx.primary.equality_residual or 0.0)
        ineq = float(ctx.primary.inequality_residual or 0.0)
        return abs(eq) + abs(ineq)


@dataclass(slots=True)
class IterationSamplingPolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.ITERATION

    def score(self, ctx: SamplingContext) -> float:
        return float(ctx.primary.iterations or 0)


@dataclass(slots=True)
class WarmStartRejectionPolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.WARM_START_REJECTION

    def score(self, ctx: SamplingContext) -> float:
        return 1.0 if ctx.warm_start_rejected else 0.0


@dataclass(slots=True)
class ActiveSetChangePolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.ACTIVE_SET_CHANGE

    def score(self, ctx: SamplingContext) -> float:
        if ctx.previous_active_set is None:
            return 0.0
        cur = set(ctx.primary.active_constraints)
        prev = set(ctx.previous_active_set)
        return float(len(cur.symmetric_difference(prev)))


@dataclass(slots=True)
class BoundaryDistancePolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.DISTANCE_FROM_BOUNDARIES

    def score(self, ctx: SamplingContext) -> float:
        # Closer to boundary => higher score
        d = ctx.boundary_distance
        if d is None:
            return 0.0
        return float(1.0 / (abs(d) + 1e-12))


@dataclass(slots=True)
class GradientConditionPolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.GRADIENT_CONDITION

    def score(self, ctx: SamplingContext) -> float:
        return float(ctx.gradient_condition_number or 0.0)


@dataclass(slots=True)
class RecentFailuresPolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.RECENT_FAILURES

    def score(self, ctx: SamplingContext) -> float:
        return float(ctx.recent_failure_count)


@dataclass(slots=True)
class UnseenFingerprintPolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.UNSEEN_FINGERPRINT

    def score(self, ctx: SamplingContext) -> float:
        return 0.0 if ctx.fingerprint_seen else 1.0


@dataclass(slots=True)
class SolverPlatformUpgradePolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.SOLVER_PLATFORM_UPGRADE

    def score(self, ctx: SamplingContext) -> float:
        return 1.0 if ctx.upgrade_event else 0.0


def all_sampling_policies(*, seed: int = 0) -> list[Any]:
    return [
        RandomSamplingPolicy(seed=seed),
        ResidualSamplingPolicy(),
        IterationSamplingPolicy(),
        WarmStartRejectionPolicy(),
        ActiveSetChangePolicy(),
        BoundaryDistancePolicy(),
        GradientConditionPolicy(),
        RecentFailuresPolicy(),
        UnseenFingerprintPolicy(),
        SolverPlatformUpgradePolicy(),
    ]


def select_for_shadow(
    contexts: list[SamplingContext],
    policy: SamplingPolicy,
    *,
    budget_fraction: float,
) -> list[str]:
    """Select scenario ids for optional secondary (shadow) solve."""

    if not contexts:
        return []
    frac = min(max(budget_fraction, 0.0), 1.0)
    k = max(1, int(round(len(contexts) * frac))) if frac > 0 else 0
    ranked = sorted(contexts, key=lambda c: policy.score(c), reverse=True)
    return [c.scenario_id for c in ranked[:k]]

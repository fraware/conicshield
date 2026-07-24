"""Risk-based shadow sampling policy prototypes (Track 2 R10).

Stable ranks are derived from cryptographic hashes of
``(master_seed, scenario_id, policy_id)`` so selection is identical across
separate Python processes. Skipped shadows are handled by the harness as
``None`` (never a copied primary).
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Protocol

import numpy as np

from conicshield.experimental.adapters.projection import ResearchProjectionResult

# Deterministic tie-break after primary score (and ranking value for random).
TIE_BREAK_RULE = "score_desc_then_ranking_value_desc_then_scenario_id_asc"


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


def ranking_value(*, master_seed: int, scenario_id: str, policy_id: str) -> float:
    """Stable uniform-[0, 1) rank from SHA-256 of ``(master_seed, scenario_id, policy_id)``."""

    payload = f"{int(master_seed)}\0{scenario_id}\0{policy_id}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    # First 8 bytes as big-endian u64 → [0, 1)
    u64 = struct.unpack(">Q", digest[:8])[0]
    return float(u64) / float(2**64)


def scenario_seed_from_master(*, master_seed: int, scenario_id: str) -> int:
    """Derive a per-scenario seed recorded in sampling provenance."""

    payload = f"scenario_seed\0{int(master_seed)}\0{scenario_id}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int(struct.unpack(">Q", digest[:8])[0] & 0x7FFF_FFFF_FFFF_FFFF)


@dataclass(slots=True)
class BoundaryFeatures:
    """True boundary / difficulty features (not residual-proxy distance)."""

    min_normalized_inequality_slack: float | None = None
    equality_conditioning: float | None = None
    dual_pressure: float | None = None
    active_set_change: float = 0.0
    warm_start_acceptance: float | None = None
    iterations: float | None = None
    verified_equality_residual: float | None = None
    verified_inequality_residual: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SamplingRankRecord:
    master_seed: int
    scenario_seed: int
    scenario_id: str
    policy_id: str
    ranking_value: float
    score: float
    tie_break_rule: str = TIE_BREAK_RULE
    selected: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SamplingContext:
    scenario_id: str
    structural_fingerprint: str
    primary: ResearchProjectionResult
    previous_active_set: tuple[str, ...] | None = None
    boundary_features: BoundaryFeatures | None = None
    gradient_condition_number: float | None = None
    recent_failure_count: int = 0
    fingerprint_seen: bool = False
    upgrade_event: bool = False
    warm_start_rejected: bool = False
    scenario_seed: int | None = None

    @property
    def boundary_distance(self) -> float | None:
        """Deprecated residual-proxy alias; prefer ``boundary_features``."""

        if self.boundary_features is None:
            return None
        return self.boundary_features.min_normalized_inequality_slack


@dataclass(slots=True)
class ShadowSelection:
    selected_ids: list[str]
    rank_records: list[SamplingRankRecord]
    master_seed: int
    policy_id: str
    budget_fraction: float
    tie_break_rule: str = TIE_BREAK_RULE

    def as_dict(self) -> dict[str, Any]:
        return {
            "selected_ids": list(self.selected_ids),
            "rank_records": [r.as_dict() for r in self.rank_records],
            "master_seed": self.master_seed,
            "policy_id": self.policy_id,
            "budget_fraction": self.budget_fraction,
            "tie_break_rule": self.tie_break_rule,
        }


class SamplingPolicy(Protocol):
    policy_id: SamplingPolicyId

    def score(self, ctx: SamplingContext) -> float:
        """Higher score => more valuable to shadow-solve."""


@dataclass(slots=True)
class RandomSamplingPolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.RANDOM
    master_seed: int = 0

    def score(self, ctx: SamplingContext) -> float:
        return ranking_value(
            master_seed=self.master_seed,
            scenario_id=ctx.scenario_id,
            policy_id=str(self.policy_id),
        )


@dataclass(slots=True)
class ResidualSamplingPolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.RESIDUAL

    def score(self, ctx: SamplingContext) -> float:
        feats = ctx.boundary_features
        if feats is not None:
            eq = float(feats.verified_equality_residual or 0.0)
            ineq = float(feats.verified_inequality_residual or 0.0)
            return abs(eq) + abs(ineq)
        eq = float(ctx.primary.equality_residual or 0.0)
        ineq = float(ctx.primary.inequality_residual or 0.0)
        return abs(eq) + abs(ineq)


@dataclass(slots=True)
class IterationSamplingPolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.ITERATION

    def score(self, ctx: SamplingContext) -> float:
        feats = ctx.boundary_features
        if feats is not None and feats.iterations is not None:
            return float(feats.iterations)
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
        feats = ctx.boundary_features
        if feats is not None:
            return float(feats.active_set_change)
        if ctx.previous_active_set is None:
            return 0.0
        cur = set(ctx.primary.active_constraints)
        prev = set(ctx.previous_active_set)
        return float(len(cur.symmetric_difference(prev)))


@dataclass(slots=True)
class BoundaryDistancePolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.DISTANCE_FROM_BOUNDARIES

    def score(self, ctx: SamplingContext) -> float:
        # Closer to boundary (smaller slack) => higher score
        feats = ctx.boundary_features
        if feats is None or feats.min_normalized_inequality_slack is None:
            return 0.0
        d = float(feats.min_normalized_inequality_slack)
        return float(1.0 / (abs(d) + 1e-12))


@dataclass(slots=True)
class GradientConditionPolicy:
    policy_id: SamplingPolicyId = SamplingPolicyId.GRADIENT_CONDITION

    def score(self, ctx: SamplingContext) -> float:
        feats = ctx.boundary_features
        if feats is not None and feats.equality_conditioning is not None:
            # Prefer recorded conditioning; fall back to explicit gradient condition.
            return float(max(feats.equality_conditioning, ctx.gradient_condition_number or 0.0))
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


def compute_boundary_features(
    *,
    corrected_action: np.ndarray,
    previous_action: np.ndarray | None,
    lower: np.ndarray,
    upper: np.ndarray,
    max_delta: np.ndarray | None,
    simplex_total: float,
    active_constraints: list[str] | tuple[str, ...],
    previous_active_set: tuple[str, ...] | None,
    equality_residual: float | None,
    inequality_residual: float | None,
    iterations: int | None,
    warm_started: bool,
    warm_start_rejected: bool,
    dual_values: np.ndarray | None = None,
    policy_weight: float = 1.0,
    reference_weight: float = 0.0,
) -> BoundaryFeatures:
    """Compute true boundary features from a verified primal solution + spec geometry."""

    x = np.asarray(corrected_action, dtype=np.float64).reshape(-1)
    lo = np.asarray(lower, dtype=np.float64).reshape(-1)
    hi = np.asarray(upper, dtype=np.float64).reshape(-1)
    if x.size == 0 or not np.all(np.isfinite(x)):
        return BoundaryFeatures(
            verified_equality_residual=equality_residual,
            verified_inequality_residual=inequality_residual,
            iterations=None if iterations is None else float(iterations),
            warm_start_acceptance=0.0 if warm_start_rejected else (1.0 if warm_started else None),
        )

    n = min(x.size, lo.size, hi.size)
    x = x[:n]
    lo = lo[:n]
    hi = hi[:n]
    width = np.maximum(hi - lo, 1e-12)
    slack_lo = (x - lo) / width
    slack_hi = (hi - x) / width
    slacks = [float(np.min(slack_lo)), float(np.min(slack_hi))]
    if previous_action is not None and max_delta is not None:
        prev = np.asarray(previous_action, dtype=np.float64).reshape(-1)[:n]
        md = np.asarray(max_delta, dtype=np.float64).reshape(-1)
        if md.size == 1:
            md = np.full(n, float(md[0]), dtype=np.float64)
        else:
            md = md[:n]
        md = np.maximum(md, 1e-12)
        rate_slack = (md - np.abs(x - prev)) / md
        slacks.append(float(np.min(rate_slack)))
    min_slack = float(min(slacks)) if slacks else None

    eq_res = equality_residual
    if eq_res is None and np.all(np.isfinite(x)):
        eq_res = float(abs(float(np.sum(x)) - float(simplex_total)))
    # Conditioning proxy: equality residual scale + objective weight imbalance.
    weight_ratio = abs(float(policy_weight)) / max(abs(float(reference_weight)), 1e-16)
    eq_cond = None
    if eq_res is not None:
        eq_cond = float(abs(eq_res) / max(abs(float(simplex_total)), 1.0)) + float(
            np.log10(max(weight_ratio, 1e-16))
        )

    if dual_values is not None and np.asarray(dual_values).size:
        d = np.asarray(dual_values, dtype=np.float64).reshape(-1)
        dual_pressure = float(np.max(np.abs(d))) if np.all(np.isfinite(d)) else None
    elif min_slack is not None:
        # Binding pressure when solver duals are unavailable (labeled via field semantics).
        dual_pressure = float(1.0 / (abs(min_slack) + 1e-12))
    else:
        dual_pressure = None

    if previous_active_set is None:
        active_change = 0.0
    else:
        active_change = float(len(set(active_constraints).symmetric_difference(set(previous_active_set))))

    if warm_start_rejected:
        warm_acc: float | None = 0.0
    elif warm_started:
        warm_acc = 1.0
    else:
        warm_acc = None

    return BoundaryFeatures(
        min_normalized_inequality_slack=min_slack,
        equality_conditioning=eq_cond,
        dual_pressure=dual_pressure,
        active_set_change=active_change,
        warm_start_acceptance=warm_acc,
        iterations=None if iterations is None else float(iterations),
        verified_equality_residual=None if equality_residual is None else float(equality_residual),
        verified_inequality_residual=None if inequality_residual is None else float(inequality_residual),
    )


def all_sampling_policies(*, master_seed: int = 0) -> list[Any]:
    return [
        RandomSamplingPolicy(master_seed=master_seed),
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


def select_for_shadow_detailed(
    contexts: list[SamplingContext],
    policy: SamplingPolicy,
    *,
    budget_fraction: float,
    master_seed: int = 0,
) -> ShadowSelection:
    """Select scenario ids for optional secondary (shadow) solve with rank provenance."""

    policy_id = str(policy.policy_id)
    if not contexts:
        return ShadowSelection(
            selected_ids=[],
            rank_records=[],
            master_seed=master_seed,
            policy_id=policy_id,
            budget_fraction=budget_fraction,
        )
    frac = min(max(budget_fraction, 0.0), 1.0)
    k = max(1, int(round(len(contexts) * frac))) if frac > 0 else 0

    records: list[SamplingRankRecord] = []
    for ctx in contexts:
        rv = ranking_value(master_seed=master_seed, scenario_id=ctx.scenario_id, policy_id=policy_id)
        sc = float(policy.score(ctx))
        sid_seed = (
            int(ctx.scenario_seed)
            if ctx.scenario_seed is not None
            else scenario_seed_from_master(master_seed=master_seed, scenario_id=ctx.scenario_id)
        )
        records.append(
            SamplingRankRecord(
                master_seed=master_seed,
                scenario_seed=sid_seed,
                scenario_id=ctx.scenario_id,
                policy_id=policy_id,
                ranking_value=rv,
                score=sc,
                tie_break_rule=TIE_BREAK_RULE,
            )
        )

    # Higher score first; tie-break by ranking_value desc, then scenario_id asc.
    ordered = sorted(
        records,
        key=lambda r: (-r.score, -r.ranking_value, r.scenario_id),
    )
    selected = {r.scenario_id for r in ordered[:k]}
    for r in records:
        r.selected = r.scenario_id in selected
    return ShadowSelection(
        selected_ids=[r.scenario_id for r in ordered[:k]],
        rank_records=records,
        master_seed=master_seed,
        policy_id=policy_id,
        budget_fraction=budget_fraction,
    )


def select_for_shadow(
    contexts: list[SamplingContext],
    policy: SamplingPolicy,
    *,
    budget_fraction: float,
    master_seed: int = 0,
) -> list[str]:
    """Select scenario ids for optional secondary (shadow) solve."""

    return select_for_shadow_detailed(
        contexts,
        policy,
        budget_fraction=budget_fraction,
        master_seed=master_seed,
    ).selected_ids

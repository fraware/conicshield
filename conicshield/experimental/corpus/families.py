"""Deterministic scenario family generators for Track 2 R0 corpus."""

from __future__ import annotations

from typing import Any

import numpy as np

from conicshield.experimental.corpus.paths import CORPUS_FAMILY_ID, CORPUS_VERSION


def _base_spec(
    *,
    spec_id: str,
    action_dim: int = 4,
    lower: list[float] | None = None,
    upper: list[float] | None = None,
    max_delta: list[float] | None = None,
    allowed: list[int] | None = None,
    simplex_total: float = 1.0,
) -> dict[str, Any]:
    n = action_dim
    return {
        "spec_id": spec_id,
        "version": "0.1.0",
        "action_dim": n,
        "slack_weight": 10.0,
        "constraints": [
            {"kind": "simplex", "total": simplex_total},
            {"kind": "turn_feasibility", "allowed_actions": allowed if allowed is not None else list(range(n))},
            {
                "kind": "box",
                "lower": lower if lower is not None else [0.0] * n,
                "upper": upper if upper is not None else [1.0] * n,
            },
            {
                "kind": "rate",
                "max_delta": max_delta if max_delta is not None else [1.0] * n,
            },
        ],
    }


def _scenario(
    *,
    scenario_id: str,
    family: str,
    seed: int,
    spec: dict[str, Any],
    proposed: list[float],
    previous: list[float],
    reference: list[float],
    expected_regime: str,
    notes: str,
    weights: dict[str, float] | None = None,
    generation_commit: str,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "scenario_id": scenario_id,
        "family": family,
        "seed": seed,
        "spec": spec,
        "proposed_action": proposed,
        "previous_action": previous,
        "reference_action": reference,
        "weights": weights or {"policy_weight": 1.0, "reference_weight": 0.0},
        "expected_regime": expected_regime,
        "generation_commit": generation_commit,
        "notes": notes,
        "corpus_version": CORPUS_VERSION,
        "corpus_family_id": CORPUS_FAMILY_ID,
    }
    if extras:
        out["extras"] = extras
    return out


def generate_family_scenarios(*, family: str, generation_commit: str, rng: np.random.Generator) -> list[dict[str, Any]]:
    """Generate one or more deterministic scenarios for a family."""

    if family == "interior_feasible":
        seed = 101
        rng = np.random.default_rng(seed)
        proposed = rng.dirichlet(np.ones(4)).tolist()
        previous = [0.25] * 4
        return [
            _scenario(
                scenario_id=f"{family}/s{seed:04d}",
                family=family,
                seed=seed,
                spec=_base_spec(spec_id=f"research/{family}"),
                proposed=proposed,
                previous=previous,
                reference=previous,
                expected_regime="interior_feasible",
                notes="Proposal already near-feasible interior of simplex+box.",
                generation_commit=generation_commit,
            )
        ]

    if family == "single_active_bound":
        seed = 201
        return [
            _scenario(
                scenario_id=f"{family}/s{seed:04d}",
                family=family,
                seed=seed,
                spec=_base_spec(spec_id=f"research/{family}", upper=[0.4, 1.0, 1.0, 1.0]),
                proposed=[0.7, 0.1, 0.1, 0.1],
                previous=[0.25] * 4,
                reference=[0.25] * 4,
                expected_regime="single_active_bound",
                notes="Upper bound on dim0 expected active.",
                generation_commit=generation_commit,
            )
        ]

    if family == "multiple_active_bounds":
        seed = 301
        return [
            _scenario(
                scenario_id=f"{family}/s{seed:04d}",
                family=family,
                seed=seed,
                spec=_base_spec(spec_id=f"research/{family}", upper=[0.3, 0.3, 1.0, 1.0]),
                proposed=[0.5, 0.5, 0.0, 0.0],
                previous=[0.25] * 4,
                reference=[0.25] * 4,
                expected_regime="multiple_active_bounds",
                notes="Two upper bounds expected active.",
                generation_commit=generation_commit,
            )
        ]

    if family == "simplex_corner":
        seed = 401
        return [
            _scenario(
                scenario_id=f"{family}/s{seed:04d}",
                family=family,
                seed=seed,
                spec=_base_spec(spec_id=f"research/{family}"),
                proposed=[1.2, -0.1, 0.0, 0.0],
                previous=[1.0, 0.0, 0.0, 0.0],
                reference=[1.0, 0.0, 0.0, 0.0],
                expected_regime="simplex_corner",
                notes="Projection toward a simplex vertex.",
                generation_commit=generation_commit,
            )
        ]

    if family == "rate_limited_transitions":
        seed = 501
        return [
            _scenario(
                scenario_id=f"{family}/s{seed:04d}",
                family=family,
                seed=seed,
                spec=_base_spec(spec_id=f"research/{family}", max_delta=[0.05] * 4),
                proposed=[0.7, 0.1, 0.1, 0.1],
                previous=[0.25] * 4,
                reference=[0.25] * 4,
                expected_regime="rate_limited",
                notes="Tight rate limits force gradual transition.",
                generation_commit=generation_commit,
            )
        ]

    if family == "changing_admissibility_masks":
        seed = 601
        return [
            _scenario(
                scenario_id=f"{family}/s{seed:04d}",
                family=family,
                seed=seed,
                spec=_base_spec(spec_id=f"research/{family}", allowed=[0, 1]),
                proposed=[0.4, 0.4, 0.1, 0.1],
                previous=[0.5, 0.5, 0.0, 0.0],
                reference=[0.5, 0.5, 0.0, 0.0],
                expected_regime="admissibility_mask",
                notes="Mask excludes actions 2 and 3.",
                generation_commit=generation_commit,
            )
        ]

    if family == "near_infeasible":
        seed = 701
        return [
            _scenario(
                scenario_id=f"{family}/s{seed:04d}",
                family=family,
                seed=seed,
                spec=_base_spec(
                    spec_id=f"research/{family}",
                    lower=[0.4, 0.4, 0.0, 0.0],
                    upper=[0.5, 0.5, 0.1, 0.1],
                    max_delta=[0.01] * 4,
                ),
                proposed=[0.45, 0.45, 0.05, 0.05],
                previous=[0.49, 0.49, 0.01, 0.01],
                reference=[0.45, 0.45, 0.05, 0.05],
                expected_regime="near_infeasible",
                notes="Tight box+rate; residuals expected elevated.",
                generation_commit=generation_commit,
            )
        ]

    if family == "infeasible":
        seed = 801
        return [
            _scenario(
                scenario_id=f"{family}/s{seed:04d}",
                family=family,
                seed=seed,
                spec=_base_spec(
                    spec_id=f"research/{family}",
                    lower=[0.6, 0.6, 0.0, 0.0],
                    upper=[0.7, 0.7, 0.1, 0.1],
                ),
                proposed=[0.65, 0.65, 0.0, 0.0],
                previous=[0.65, 0.65, 0.0, 0.0],
                reference=[0.65, 0.65, 0.0, 0.0],
                expected_regime="infeasible",
                notes="Lower bounds sum above simplex total — disagreement/failure regime.",
                generation_commit=generation_commit,
            )
        ]

    if family == "poorly_conditioned_objectives":
        seed = 901
        return [
            _scenario(
                scenario_id=f"{family}/s{seed:04d}",
                family=family,
                seed=seed,
                spec=_base_spec(spec_id=f"research/{family}"),
                proposed=[1e6, 1e-8, 1e-8, 1e-8],
                previous=[0.25] * 4,
                reference=[0.0, 0.0, 0.0, 1.0],
                weights={"policy_weight": 1e8, "reference_weight": 1e-8},
                expected_regime="poorly_conditioned",
                notes="Extreme weight scale and proposal magnitude.",
                generation_commit=generation_commit,
            )
        ]

    if family == "active_set_transition_neighborhoods":
        # Dense trajectories crossing activation boundaries for each constraint family.
        # Records both sides of the boundary for FD / observatory studies.
        scenarios: list[dict[str, Any]] = []
        seed = 1001
        # Box upper-bound trajectory (denser near the transition for R2.H3)
        for i, upper0 in enumerate([0.45, 0.47, 0.48, 0.49, 0.495, 0.50, 0.505, 0.51, 0.52, 0.55]):
            side = "below" if upper0 < 0.50 else ("at" if upper0 == 0.50 else "above")
            pre = upper0 < 0.50 and upper0 >= 0.48
            scenarios.append(
                _scenario(
                    scenario_id=f"{family}/s{seed + i:04d}",
                    family=family,
                    seed=seed + i,
                    spec=_base_spec(spec_id=f"research/{family}/box", upper=[upper0, 1.0, 1.0, 1.0]),
                    proposed=[0.55, 0.15, 0.15, 0.15],
                    previous=[0.25] * 4,
                    reference=[0.25] * 4,
                    expected_regime="active_set_transition_neighborhood",
                    notes=f"Box-bound trajectory; upper0={upper0}.",
                    generation_commit=generation_commit,
                    extras={
                        "constraint_family": "box",
                        "bound_param": upper0,
                        "trajectory_id": "box_upper0",
                        "side": side,
                        "pre_transition": pre,
                        "disagreement_regime": "bound_neighborhood",
                    },
                )
            )
        # Rate-limit trajectory
        seed_r = 1100
        for i, md in enumerate([0.20, 0.24, 0.26, 0.28, 0.29, 0.30, 0.31, 0.32, 0.35, 0.40]):
            side = "tight" if md < 0.30 else ("at" if md == 0.30 else "loose")
            pre = md < 0.30 and md >= 0.26
            scenarios.append(
                _scenario(
                    scenario_id=f"{family}/s{seed_r + i:04d}",
                    family=family,
                    seed=seed_r + i,
                    spec=_base_spec(spec_id=f"research/{family}/rate", max_delta=[md] * 4),
                    proposed=[0.70, 0.10, 0.10, 0.10],
                    previous=[0.40, 0.20, 0.20, 0.20],
                    reference=[0.40, 0.20, 0.20, 0.20],
                    expected_regime="active_set_transition_neighborhood",
                    notes=f"Rate-limit trajectory; max_delta={md}.",
                    generation_commit=generation_commit,
                    extras={
                        "constraint_family": "rate",
                        "bound_param": md,
                        "trajectory_id": "rate_max_delta",
                        "side": side,
                        "pre_transition": pre,
                        "disagreement_regime": "rate_neighborhood",
                    },
                )
            )
        # Simplex / admissibility mask trajectory (allowed set changes)
        seed_m = 1200
        masks = [
            ([0, 1, 2, 3], "full"),
            ([0, 1, 2], "drop3"),
            ([0, 1], "drop23"),
            ([0], "corner"),
        ]
        for i, (allowed, label) in enumerate(masks):
            scenarios.append(
                _scenario(
                    scenario_id=f"{family}/s{seed_m + i:04d}",
                    family=family,
                    seed=seed_m + i,
                    spec=_base_spec(spec_id=f"research/{family}/mask", allowed=allowed),
                    proposed=[0.40, 0.30, 0.20, 0.10],
                    previous=[0.25] * 4,
                    reference=[0.25] * 4,
                    expected_regime="active_set_transition_neighborhood",
                    notes=f"Admissibility trajectory; mask={label}.",
                    generation_commit=generation_commit,
                    extras={
                        "constraint_family": "turn_feasibility",
                        "bound_param": float(len(allowed)),
                        "trajectory_id": "admissibility_mask",
                        "side": label,
                        "pre_transition": label in {"drop3", "drop23"},
                        "disagreement_regime": "admissibility_change",
                    },
                )
            )
        return scenarios

    if family == "solver_timeout_iteration_limit":
        seed = 1101
        return [
            _scenario(
                scenario_id=f"{family}/s{seed:04d}",
                family=family,
                seed=seed,
                spec=_base_spec(spec_id=f"research/{family}"),
                proposed=[0.4, 0.3, 0.2, 0.1],
                previous=[0.25] * 4,
                reference=[0.25] * 4,
                expected_regime="timeout_or_iteration_limit",
                notes="Harness should apply tiny max_iter / time_limit.",
                generation_commit=generation_commit,
                extras={"suggested_max_iter": 1, "suggested_time_limit": 1e-9},
            )
        ]

    if family == "warm_start_success_failure":
        seed = 1201
        return [
            _scenario(
                scenario_id=f"{family}/s{seed:04d}a",
                family=family,
                seed=seed,
                spec=_base_spec(spec_id=f"research/{family}"),
                proposed=[0.3, 0.3, 0.2, 0.2],
                previous=[0.28, 0.28, 0.22, 0.22],
                reference=[0.25] * 4,
                expected_regime="warm_start_candidate_success",
                notes="Nearby previous action — warm start likely helpful.",
                generation_commit=generation_commit,
                extras={"warm_start_hint": "reuse_previous"},
            ),
            _scenario(
                scenario_id=f"{family}/s{seed:04d}b",
                family=family,
                seed=seed + 1,
                spec=_base_spec(spec_id=f"research/{family}", allowed=[2, 3]),
                proposed=[0.0, 0.0, 0.6, 0.4],
                previous=[0.6, 0.4, 0.0, 0.0],
                reference=[0.0, 0.0, 0.5, 0.5],
                expected_regime="warm_start_candidate_failure",
                notes="Mask flip vs previous — warm start likely harmful.",
                generation_commit=generation_commit,
                extras={"warm_start_hint": "stale_mask"},
            ),
        ]

    if family == "heterogeneous_batches":
        seed = 1301
        return [
            _scenario(
                scenario_id=f"{family}/s{seed:04d}",
                family=family,
                seed=seed,
                spec=_base_spec(spec_id=f"research/{family}"),
                proposed=[0.4, 0.3, 0.2, 0.1],
                previous=[0.25] * 4,
                reference=[0.25] * 4,
                expected_regime="heterogeneous_batch_member",
                notes="Member of a heterogeneous batch; batching via research adapter until Track 1 S4.",
                generation_commit=generation_commit,
                extras={
                    "batch_peers": [
                        {"proposed_action": [0.1, 0.2, 0.3, 0.4], "spec_variant": "default"},
                        {"proposed_action": [0.9, 0.05, 0.05, 0.0], "spec_variant": "tight_box"},
                    ]
                },
            )
        ]

    if family == "sidecar_interruption":
        seed = 1401
        return [
            _scenario(
                scenario_id=f"{family}/s{seed:04d}",
                family=family,
                seed=seed,
                spec=_base_spec(spec_id=f"research/{family}"),
                proposed=[0.35, 0.35, 0.15, 0.15],
                previous=[0.25] * 4,
                reference=[0.25] * 4,
                expected_regime="sidecar_interruption",
                notes="Stub regime for Windows-sidecar interruption studies (backend may be unavailable).",
                generation_commit=generation_commit,
                extras={"backend_stub": "windows_sidecar", "interrupt_policy": "hard_timeout"},
            )
        ]

    if family == "backend_version_changes":
        seed = 1501
        return [
            _scenario(
                scenario_id=f"{family}/s{seed:04d}",
                family=family,
                seed=seed,
                spec=_base_spec(spec_id=f"research/{family}"),
                proposed=[0.2, 0.3, 0.3, 0.2],
                previous=[0.25] * 4,
                reference=[0.25] * 4,
                expected_regime="backend_version_change",
                notes="Compare candidate vs approved solver versions in shadow harness.",
                generation_commit=generation_commit,
                extras={"approved_label": "approved", "candidate_label": "candidate"},
            )
        ]

    if family == "consequential_disagreement_regimes":
        # Explicit fault-injection and conditioning regimes that enrich the 100% shadow
        # baseline with consequential primary/shadow disagreements for sampling science.
        return [
            _scenario(
                scenario_id=f"{family}/s1601",
                family=family,
                seed=1601,
                spec=_base_spec(spec_id=f"research/{family}/shadow_iter_starve"),
                proposed=[0.55, 0.25, 0.15, 0.05],
                previous=[0.25] * 4,
                reference=[0.25] * 4,
                expected_regime="fault_injection_shadow_iteration_limit",
                notes=(
                    "Fault injection: starve shadow solver iterations/time while primary "
                    "uses defaults — induces status/timeout asymmetry."
                ),
                generation_commit=generation_commit,
                extras={
                    "fault_injection": True,
                    "fault_injection_kind": "shadow_iteration_limit",
                    "fault_injection_label": "shadow_iteration_limit",
                    "fault_injection_notes": "shadow_overrides.max_iter/time_limit only",
                    "shadow_overrides": {
                        "suggested_max_iter": 1,
                        "suggested_time_limit": 1e-9,
                    },
                    "disagreement_regime": "iteration_limit_asymmetry",
                },
            ),
            _scenario(
                scenario_id=f"{family}/s1602",
                family=family,
                seed=1602,
                spec=_base_spec(
                    spec_id=f"research/{family}/conditioning",
                    upper=[0.35, 1.0, 1.0, 1.0],
                    max_delta=[0.05] * 4,
                ),
                proposed=[1e5, 1e-6, 1e-6, 1e-6],
                previous=[0.30, 0.30, 0.20, 0.20],
                reference=[0.0, 0.0, 0.0, 1.0],
                weights={"policy_weight": 1e10, "reference_weight": 1e-10},
                expected_regime="conditioning_cross_solver",
                notes=(
                    "Ill-conditioned weights + tight rate/box neighborhood — "
                    "Clarabel vs SCS residual/action disagreement regime (not fault injection)."
                ),
                generation_commit=generation_commit,
                extras={
                    "fault_injection": False,
                    "disagreement_regime": "conditioning_tolerance",
                    "constraint_family": "box_rate",
                },
            ),
            _scenario(
                scenario_id=f"{family}/s1603",
                family=family,
                seed=1603,
                spec=_base_spec(
                    spec_id=f"research/{family}/warm_cold",
                    allowed=[0, 1],
                ),
                proposed=[0.7, 0.3, 0.0, 0.0],
                previous=[0.0, 0.0, 0.6, 0.4],
                reference=[0.5, 0.5, 0.0, 0.0],
                expected_regime="fault_injection_warm_vs_cold",
                notes=(
                    "Fault injection: shadow warm-starts from stale previous under a mask "
                    "flip; primary stays cold."
                ),
                generation_commit=generation_commit,
                extras={
                    "fault_injection": True,
                    "fault_injection_kind": "shadow_warm_start_stale",
                    "fault_injection_label": "shadow_warm_start_stale",
                    "fault_injection_notes": "shadow warm_start=True with stale previous under new mask",
                    "primary_overrides": {"warm_start": False},
                    "shadow_overrides": {"warm_start": True},
                    "warm_start_rejected": True,
                    "disagreement_regime": "warm_cold_asymmetry",
                },
            ),
            _scenario(
                scenario_id=f"{family}/s1604",
                family=family,
                seed=1604,
                spec=_base_spec(
                    spec_id=f"research/{family}/active_set_nbhd",
                    upper=[0.495, 1.0, 1.0, 1.0],
                ),
                proposed=[0.55, 0.15, 0.15, 0.15],
                previous=[0.25] * 4,
                reference=[0.25] * 4,
                expected_regime="active_set_neighborhood_perturbation",
                notes=(
                    "Active-set neighborhood just below box activation; "
                    "paired with shadow iteration starve for compound disagreement."
                ),
                generation_commit=generation_commit,
                extras={
                    "fault_injection": True,
                    "fault_injection_kind": "shadow_iteration_limit_at_boundary",
                    "fault_injection_label": "shadow_iteration_limit_at_boundary",
                    "fault_injection_notes": "boundary neighborhood + shadow iter starve",
                    "shadow_overrides": {"suggested_max_iter": 2, "suggested_time_limit": 1e-8},
                    "constraint_family": "box",
                    "disagreement_regime": "active_set_neighborhood",
                    "pre_transition": True,
                },
            ),
        ]

    raise ValueError(f"unknown scenario family: {family}")

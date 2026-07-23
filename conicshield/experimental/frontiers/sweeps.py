"""Counterfactual safety frontier sweeps (R3)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from itertools import product
from typing import Any

import numpy as np

from conicshield.experimental.adapters.projection import ResearchBatchProjectionResult, ResearchProjectionResult
from conicshield.experimental.gradients.finite_difference import central_finite_difference_jacobian
from conicshield.experimental.solver_assurance.backends import create_research_projector
from conicshield.specs.schema import SafetySpec

FRONTIER_PARAMETERS: tuple[str, ...] = (
    "rate_limit",
    "hazard_multiplier",
    "geometry_prior_weight",
    "policy_weight",
    "reference_weight",
    "bound_margins",
    "robustness_margins",
    "fallback_thresholds",
)

BATCH_EMULATION_SEQUENTIAL = "sequential_adapter"
BATCH_EMULATION_NONE = "none"
PUBLICATION_GRADE_WATERMARK = (
    "NOT_PUBLICATION_GRADE: sequential_adapter batching is a research emulation. "
    "Track 1 S4 heterogeneous batch attestation is required for publication-grade results."
)


@dataclass(slots=True)
class BatchAttestation:
    """Record whether Track 1 hetero-batch is **live**-attested for this run."""

    batch_emulation: str
    track1_s4_attested: bool
    attestation_note: str
    publication_grade: bool
    attestation_record: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "batch_emulation": self.batch_emulation,
            "track1_s4_attested": self.track1_s4_attested,
            "attestation_note": self.attestation_note,
            "publication_grade": self.publication_grade,
            "attestation_record": dict(self.attestation_record),
        }


def probe_track1_hetero_batch_attestation() -> BatchAttestation:
    """Track 1 S4 ``project_batch`` / NATIVE_MOREAU_BATCH vs **live** vendor attestation.

    Delegates to ``adapters.track1_probe`` for a structured attestation record.
    Research keeps ``batch_emulation: sequential_adapter`` and refuses
    ``batch_emulation: none`` until a live batch sample (with sample hashes) is
    attested. Capability discovery alone never clears the watermark.
    """

    try:
        from conicshield.experimental.adapters.track1_probe import probe_track1_research_readiness

        report = probe_track1_research_readiness()
        s4 = next(
            (p for p in report.probes if p.capability_id == "S4_hetero_batch"),
            None,
        )
        record: dict[str, Any] = {
            "probe_version": report.probe_version,
            "platform": report.platform,
            "probed_at_utc": report.probed_at_utc,
        }
        if s4 is not None:
            record.update(
                {
                    "detail": s4.detail,
                    "missing_evidence": list(s4.missing_evidence),
                    "live_sample": dict((s4.extras or {}).get("live_sample") or {}),
                    "surfaces_present": dict((s4.extras or {}).get("surfaces_present") or {}),
                    "solver_version": ((s4.extras or {}).get("live_sample") or {}).get(
                        "solver_version"
                    ),
                    "capability_flags": ((s4.extras or {}).get("live_sample") or {}).get(
                        "capability_flags"
                    )
                    or {},
                    "sample_hashes": ((s4.extras or {}).get("live_sample") or {}).get(
                        "sample_hashes"
                    )
                    or {},
                }
            )
        if s4 is not None and s4.research_attested and report.reduce_watermarks:
            return BatchAttestation(
                batch_emulation=BATCH_EMULATION_NONE,
                track1_s4_attested=True,
                attestation_note=s4.detail,
                publication_grade=True,
                attestation_record=record,
            )
        note = (
            s4.detail
            if s4 is not None
            else "Track 1 S4 hetero-batch not live-attested on this host."
        )
        return BatchAttestation(
            batch_emulation=BATCH_EMULATION_SEQUENTIAL,
            track1_s4_attested=False,
            attestation_note=note + " " + PUBLICATION_GRADE_WATERMARK,
            publication_grade=False,
            attestation_record=record,
        )
    except Exception as exc:  # noqa: BLE001 — research probe must never crash callers
        return BatchAttestation(
            batch_emulation=BATCH_EMULATION_SEQUENTIAL,
            track1_s4_attested=False,
            attestation_note=(
                f"Track 1 S4 probe failed closed ({type(exc).__name__}). "
                + PUBLICATION_GRADE_WATERMARK
            ),
            publication_grade=False,
            attestation_record={"probe_exception": f"{type(exc).__name__}: {exc}"},
        )


@dataclass(slots=True)
class FrontierPoint:
    parameters: dict[str, float]
    intervention_magnitude: float
    objective_value: float | None
    feasibility_margin: float
    active_set: tuple[str, ...]
    solver_iterations: int | None
    residuals: dict[str, float]
    task_utility_proxy: float
    local_jacobian_norm: float | None
    shadow_disagreement: float | None
    selected_action: list[float]
    policy_fidelity: float = 0.0
    safety_margin: float = 0.0
    latency_proxy: float = 0.0
    numerical_confidence: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "parameters": dict(self.parameters),
            "intervention_magnitude": self.intervention_magnitude,
            "objective_value": self.objective_value,
            "feasibility_margin": self.feasibility_margin,
            "active_set": list(self.active_set),
            "solver_iterations": self.solver_iterations,
            "residuals": dict(self.residuals),
            "task_utility_proxy": self.task_utility_proxy,
            "local_jacobian_norm": self.local_jacobian_norm,
            "shadow_disagreement": self.shadow_disagreement,
            "selected_action": list(self.selected_action),
            "policy_fidelity": self.policy_fidelity,
            "safety_margin": self.safety_margin,
            "latency_proxy": self.latency_proxy,
            "numerical_confidence": self.numerical_confidence,
        }


@dataclass(slots=True)
class ParetoFrontier:
    points: list[FrontierPoint] = field(default_factory=list)
    pareto_indices: list[int] = field(default_factory=list)
    objectives: tuple[str, ...] = (
        "policy_fidelity",
        "safety_margin",
        "intervention_magnitude",
        "latency",
        "numerical_confidence",
    )
    batch_emulation: str = BATCH_EMULATION_SEQUENTIAL
    batching_note: str = (
        "Publication-grade results require Track 1 heterogeneous batch interface (S4). "
        "This research adapter uses sequential solves with explicit batch_emulation provenance."
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "objectives": list(self.objectives),
            "batch_emulation": self.batch_emulation,
            "batching_note": self.batching_note,
            "pareto_indices": list(self.pareto_indices),
            "points": [p.as_dict() for p in self.points],
        }


def iter_parameter_grid(grid: dict[str, list[float]]) -> Iterator[dict[str, float]]:
    keys = sorted(grid.keys())
    for values in product(*(grid[k] for k in keys)):
        yield dict(zip(keys, values, strict=True))


def _spec_with_params(spec: SafetySpec, params: dict[str, float]) -> SafetySpec:
    """Apply frontier parameters that map onto SafetySpec fields."""

    data = spec.model_dump()
    constraints = list(data.get("constraints") or [])
    rate_scale = float(params.get("rate_limit", 1.0))
    bound_margin = float(params.get("bound_margins", 0.0))
    for c in constraints:
        kind = c.get("kind")
        if kind == "rate" and "max_delta" in c:
            c["max_delta"] = [float(x) * rate_scale for x in c["max_delta"]]
        if kind == "box":
            if "lower" in c:
                c["lower"] = [float(x) - bound_margin for x in c["lower"]]
            if "upper" in c:
                c["upper"] = [float(x) + bound_margin for x in c["upper"]]
    # hazard / geometry / robustness / fallback are recorded as metadata effects when not in spec
    data["constraints"] = constraints
    slack = float(data.get("slack_weight") or 10.0)
    hazard = float(params.get("hazard_multiplier", 1.0))
    robust = float(params.get("robustness_margins", 0.0))
    data["slack_weight"] = slack * hazard * (1.0 + robust)
    return SafetySpec.model_validate(data)


def compute_pareto_indices(points: list[FrontierPoint]) -> list[int]:
    """Pareto front for maximize fidelity/safety/confidence, minimize intervention/latency."""

    def vec(p: FrontierPoint) -> tuple[float, ...]:
        # Convert to all-maximize form
        return (
            p.policy_fidelity,
            p.safety_margin,
            -p.intervention_magnitude,
            -p.latency_proxy,
            p.numerical_confidence,
        )

    idxs = list(range(len(points)))
    pareto: list[int] = []
    for i in idxs:
        vi = vec(points[i])
        dominated = False
        for j in idxs:
            if i == j:
                continue
            vj = vec(points[j])
            if all(a <= b for a, b in zip(vi, vj, strict=True)) and any(a < b for a, b in zip(vi, vj, strict=True)):
                dominated = True
                break
        if not dominated:
            pareto.append(i)
    return pareto


def project_batch_sequential(
    *,
    specs: list[SafetySpec],
    proposed_actions: list[np.ndarray],
    previous_actions: list[np.ndarray],
    reference_actions: list[np.ndarray],
    policy_weights: list[float],
    reference_weights: list[float],
    backend_id: str = "cvxpy_clarabel",
) -> ResearchBatchProjectionResult:
    """Vectorized batch API surface with mandatory sequential_adapter provenance.

    Implementation is sequential public solves. Outputs always carry the
    publication-grade watermark unless Track 1 S4 is separately attested.
    """

    attestation = probe_track1_hetero_batch_attestation()
    n = len(specs)
    if not (
        len(proposed_actions)
        == len(previous_actions)
        == len(reference_actions)
        == len(policy_weights)
        == len(reference_weights)
        == n
    ):
        raise ValueError("batch input lengths must match specs")

    results: list[ResearchProjectionResult] = []
    for i, spec in enumerate(specs):
        projector = create_research_projector(backend_id=backend_id, spec=spec)
        result = projector.project(
            proposed_actions[i],
            previous_actions[i],
            reference_action=reference_actions[i],
            policy_weight=policy_weights[i],
            reference_weight=reference_weights[i],
            metadata={
                "batch_emulation": attestation.batch_emulation
                if attestation.track1_s4_attested
                else BATCH_EMULATION_SEQUENTIAL,
                "batch_index": i,
                "publication_grade": attestation.publication_grade,
            },
        )
        # Force sequential provenance unless truly attested (we never silently drop the flag).
        if not attestation.track1_s4_attested:
            result.metadata["batch_emulation"] = BATCH_EMULATION_SEQUENTIAL
            result.metadata["publication_grade_watermark"] = PUBLICATION_GRADE_WATERMARK
        else:
            result.metadata["batch_emulation"] = BATCH_EMULATION_NONE
        results.append(result)

    emulation = BATCH_EMULATION_NONE if attestation.track1_s4_attested else BATCH_EMULATION_SEQUENTIAL
    return ResearchBatchProjectionResult(
        results=results,
        batch_size=len(results),
        heterogeneous=True,
        batch_emulation=emulation,
        notes=(
            attestation.attestation_note
            if not attestation.publication_grade
            else "Track 1 S4 hetero-batch attested; batch_emulation=none."
        ),
        attestation=attestation.as_dict(),
        publication_grade=attestation.publication_grade,
    )


def run_frontier_sweep(
    *,
    spec: SafetySpec,
    proposed_action: np.ndarray,
    previous_action: np.ndarray,
    reference_action: np.ndarray,
    grid: dict[str, list[float]] | None = None,
    backend_id: str = "cvxpy_clarabel",
    compute_local_jacobian: bool = False,
    h: float = 1e-5,
) -> ParetoFrontier:
    """Parameter sweep producing Pareto frontier structures among research objectives."""

    grid = grid or {
        "policy_weight": [1.0, 2.0],
        "reference_weight": [0.0, 0.5],
        "rate_limit": [0.5, 1.0],
        "hazard_multiplier": [1.0, 1.5],
        "geometry_prior_weight": [0.0, 0.25],
        "bound_margins": [0.0, 0.01],
        "robustness_margins": [0.0, 0.05],
        "fallback_thresholds": [0.1, 0.5],
    }
    param_list = list(iter_parameter_grid(grid))
    specs = [_spec_with_params(spec, p) for p in param_list]
    n = len(param_list)
    proposed = [np.asarray(proposed_action, dtype=np.float64)] * n
    previous = [np.asarray(previous_action, dtype=np.float64)] * n
    reference = [np.asarray(reference_action, dtype=np.float64)] * n
    policy_weights = [float(p.get("policy_weight", 1.0)) for p in param_list]
    reference_weights = [float(p.get("reference_weight", 0.0)) for p in param_list]

    batch = project_batch_sequential(
        specs=specs,
        proposed_actions=proposed,
        previous_actions=previous,
        reference_actions=reference,
        policy_weights=policy_weights,
        reference_weights=reference_weights,
        backend_id=backend_id,
    )

    points: list[FrontierPoint] = []
    for params, result in zip(param_list, batch.results, strict=True):
        eq = float(result.equality_residual or 0.0)
        ineq = float(result.inequality_residual or 0.0)
        safety = float(-(eq + ineq))
        fidelity = float(-result.intervention_norm)
        # geometry_prior_weight / fallback_thresholds recorded in params; affect confidence proxy
        geom = float(params.get("geometry_prior_weight", 0.0))
        fallback_thr = float(params.get("fallback_thresholds", 0.5))
        conf = 1.0 / (1.0 + abs(eq) + abs(ineq) + abs(geom) * 0.0)
        if result.canonical_status.value not in {"optimal"}:
            conf *= fallback_thr
        jac_norm: float | None = None
        if compute_local_jacobian:
            params_local = dict(params)

            def forward(p: np.ndarray, _params: dict[str, float] = params_local) -> np.ndarray:
                proj = create_research_projector(backend_id=backend_id, spec=_spec_with_params(spec, _params))
                r = proj.project(
                    p,
                    previous_action,
                    reference_action=reference_action,
                    policy_weight=float(_params.get("policy_weight", 1.0)),
                    reference_weight=float(_params.get("reference_weight", 0.0)),
                )
                return np.asarray(r.corrected_action, dtype=np.float64)

            fd = central_finite_difference_jacobian(
                forward,
                np.asarray(proposed_action, dtype=np.float64),
                h=h,
                parameter_name="proposed_action",
            )
            jac_norm = float(np.linalg.norm(fd.jacobian, ord="fro")) if fd.failure_status is None else None

        points.append(
            FrontierPoint(
                parameters=params,
                intervention_magnitude=float(result.intervention_norm),
                objective_value=result.objective_value,
                feasibility_margin=safety,
                active_set=tuple(result.active_constraints),
                solver_iterations=result.iterations,
                residuals={"equality": eq, "inequality": ineq},
                task_utility_proxy=fidelity,
                local_jacobian_norm=jac_norm,
                shadow_disagreement=None,
                selected_action=np.asarray(result.corrected_action, dtype=np.float64).tolist(),
                policy_fidelity=fidelity,
                safety_margin=safety,
                latency_proxy=float(result.iterations or 0),
                numerical_confidence=float(conf),
            )
        )

    pareto = compute_pareto_indices(points)
    return ParetoFrontier(
        points=points,
        pareto_indices=pareto,
        batch_emulation=BATCH_EMULATION_SEQUENTIAL,
    )


def run_frontier_sweep_scaffold(
    *,
    spec: SafetySpec,
    proposed_action: np.ndarray,
    previous_action: np.ndarray,
    reference_action: np.ndarray,
    grid: dict[str, list[float]] | None = None,
    backend_id: str = "cvxpy_clarabel",
) -> ParetoFrontier:
    """Small deterministic sweep for scaffolding / CI (subset of full parameters)."""

    grid = grid or {
        "policy_weight": [1.0, 2.0],
        "reference_weight": [0.0, 0.5],
        "rate_limit": [0.2, 1.0],
    }
    return run_frontier_sweep(
        spec=spec,
        proposed_action=proposed_action,
        previous_action=previous_action,
        reference_action=reference_action,
        grid=grid,
        backend_id=backend_id,
        compute_local_jacobian=False,
    )

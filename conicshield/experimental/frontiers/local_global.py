"""Local-to-global consistency: FD gradient predicts nearby frontier movement (R3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.experimental.frontiers.sweeps import BATCH_EMULATION_SEQUENTIAL, FrontierPoint
from conicshield.experimental.gradients.finite_difference import central_finite_difference_jacobian
from conicshield.experimental.solver_assurance.backends import create_research_projector
from conicshield.specs.schema import SafetySpec


@dataclass(slots=True)
class LocalGlobalConsistencyDesign:
    """Experiment design: use R2 gradients to predict nearby frontier movement."""

    description: str = (
        "Use the gradient from R2 to predict nearby frontier movement. "
        "Compare the prediction against actual batched solves. Large discrepancies "
        "identify active-set changes, strong nonlinearity, unreliable local sensitivities, "
        "or regions requiring denser sampling."
    )
    requires_track1: str = "S4 heterogeneous batch interface for final reported results"
    status: str = "implemented_research_adapter"

    def as_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "requires_track1": self.requires_track1,
            "status": self.status,
            "batch_emulation": BATCH_EMULATION_SEQUENTIAL,
        }


@dataclass(slots=True)
class LocalGlobalFlag:
    parameter_name: str
    predicted_delta: float
    actual_delta: float
    relative_error: float
    absolute_error: float
    active_set_changed: bool
    flag: str  # ok | active_set_change | nonlinearity | unreliable_sensitivity
    regime_tag: str = "unknown"

    def as_dict(self) -> dict[str, Any]:
        return {
            "parameter_name": self.parameter_name,
            "predicted_delta": self.predicted_delta,
            "actual_delta": self.actual_delta,
            "relative_error": self.relative_error,
            "absolute_error": self.absolute_error,
            "active_set_changed": self.active_set_changed,
            "flag": self.flag,
            "regime_tag": self.regime_tag,
        }


@dataclass(slots=True)
class LocalGlobalConsistencyResult:
    base_active_set: tuple[str, ...]
    flags: list[LocalGlobalFlag] = field(default_factory=list)
    batch_emulation: str = BATCH_EMULATION_SEQUENTIAL
    notes: str = ""
    mean_relative_error: float | None = None
    mean_absolute_error: float | None = None
    regime_counts: dict[str, int] = field(default_factory=dict)
    consistency_rate: float | None = None
    active_set_change_rate: float | None = None
    flag_counts: dict[str, int] = field(default_factory=dict)
    publication_grade_watermark: str = "NOT_PUBLICATION_GRADE: local-global analysis used research sequential batching."

    def as_dict(self) -> dict[str, Any]:
        return {
            "base_active_set": list(self.base_active_set),
            "flags": [f.as_dict() for f in self.flags],
            "batch_emulation": self.batch_emulation,
            "notes": self.notes,
            "mean_relative_error": self.mean_relative_error,
            "mean_absolute_error": self.mean_absolute_error,
            "regime_counts": dict(self.regime_counts),
            "consistency_rate": self.consistency_rate,
            "active_set_change_rate": self.active_set_change_rate,
            "flag_counts": dict(self.flag_counts),
            "publication_grade_watermark": self.publication_grade_watermark,
        }


def run_local_global_consistency(
    *,
    spec: SafetySpec,
    proposed_action: np.ndarray,
    previous_action: np.ndarray,
    reference_action: np.ndarray,
    base_params: dict[str, float],
    neighbor_params: list[dict[str, float]],
    backend_id: str = "cvxpy_clarabel",
    h: float = 1e-5,
    error_threshold: float = 0.5,
) -> LocalGlobalConsistencyResult:
    """Predict action change from FD Jacobian; compare to actual neighbor solves."""

    from conicshield.experimental.frontiers.sweeps import _spec_with_params

    x0 = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
    base_spec = _spec_with_params(spec, base_params)

    def forward(p: np.ndarray) -> np.ndarray:
        proj = create_research_projector(backend_id=backend_id, spec=base_spec)
        r = proj.project(
            p,
            previous_action,
            reference_action=reference_action,
            policy_weight=float(base_params.get("policy_weight", 1.0)),
            reference_weight=float(base_params.get("reference_weight", 0.0)),
        )
        return np.asarray(r.corrected_action, dtype=np.float64)

    base_proj = create_research_projector(backend_id=backend_id, spec=base_spec)
    base_res = base_proj.project(
        x0,
        previous_action,
        reference_action=reference_action,
        policy_weight=float(base_params.get("policy_weight", 1.0)),
        reference_weight=float(base_params.get("reference_weight", 0.0)),
    )
    y0 = np.asarray(base_res.corrected_action, dtype=np.float64).reshape(-1)
    base_active = tuple(base_res.active_constraints)

    fd = central_finite_difference_jacobian(forward, x0, h=h, parameter_name="proposed_action")
    jac = fd.jacobian

    flags: list[LocalGlobalFlag] = []
    for neigh in neighbor_params:
        # Parameter delta that also perturbs the proposed action slightly as a probe
        delta_x = np.zeros_like(x0)
        # Encode policy_weight change as a synthetic direction on first coord if present
        pw_delta = float(neigh.get("policy_weight", base_params.get("policy_weight", 1.0))) - float(
            base_params.get("policy_weight", 1.0)
        )
        if abs(pw_delta) > 0:
            delta_x[0] = 0.01 * pw_delta
        rate_delta = float(neigh.get("rate_limit", base_params.get("rate_limit", 1.0))) - float(
            base_params.get("rate_limit", 1.0)
        )
        if abs(rate_delta) > 0 and delta_x.size > 1:
            delta_x[1] = 0.01 * rate_delta

        predicted = jac @ delta_x if jac.size and jac.shape[1] == delta_x.size else np.zeros_like(y0)
        pred_norm = float(np.linalg.norm(predicted))

        n_spec = _spec_with_params(spec, {**base_params, **neigh})
        n_proj = create_research_projector(backend_id=backend_id, spec=n_spec)
        n_res = n_proj.project(
            x0 + delta_x,
            previous_action,
            reference_action=reference_action,
            policy_weight=float(neigh.get("policy_weight", base_params.get("policy_weight", 1.0))),
            reference_weight=float(neigh.get("reference_weight", base_params.get("reference_weight", 0.0))),
            metadata={"batch_emulation": BATCH_EMULATION_SEQUENTIAL},
        )
        y1 = np.asarray(n_res.corrected_action, dtype=np.float64).reshape(-1)
        actual = y1 - y0
        actual_norm = float(np.linalg.norm(actual)) if np.all(np.isfinite(actual)) else float("nan")
        rel_err = (
            float(np.linalg.norm(predicted - actual) / max(actual_norm, 1e-12))
            if np.isfinite(actual_norm)
            else float("nan")
        )
        active_changed = set(n_res.active_constraints) != set(base_active)
        if active_changed:
            flag = "active_set_change"
            regime = "active_set_transition"
        elif not np.isfinite(rel_err):
            flag = "unreliable_sensitivity"
            regime = "unreliable"
        elif rel_err > error_threshold:
            flag = "nonlinearity"
            regime = "strong_nonlinearity"
        else:
            flag = "ok"
            regime = "locally_consistent"
        abs_err = float(np.linalg.norm(predicted - actual)) if np.isfinite(actual_norm) else float("nan")
        flags.append(
            LocalGlobalFlag(
                parameter_name=",".join(sorted(neigh.keys())),
                predicted_delta=pred_norm,
                actual_delta=actual_norm if np.isfinite(actual_norm) else float("nan"),
                relative_error=rel_err if np.isfinite(rel_err) else float("nan"),
                absolute_error=abs_err,
                active_set_changed=active_changed,
                flag=flag,
                regime_tag=regime,
            )
        )

    rels = [f.relative_error for f in flags if np.isfinite(f.relative_error)]
    abss = [f.absolute_error for f in flags if np.isfinite(f.absolute_error)]
    regime_counts: dict[str, int] = {}
    for f in flags:
        regime_counts[f.regime_tag] = regime_counts.get(f.regime_tag, 0) + 1

    flag_counts: dict[str, int] = {}
    for f in flags:
        flag_counts[f.flag] = flag_counts.get(f.flag, 0) + 1
    consistency_rate = float(flag_counts.get("ok", 0) / max(len(flags), 1)) if flags else None
    active_set_change_rate = (
        float(sum(1 for f in flags if f.active_set_changed) / max(len(flags), 1)) if flags else None
    )

    return LocalGlobalConsistencyResult(
        base_active_set=base_active,
        flags=flags,
        notes=(
            "Research adapter only; publication-grade requires Track 1 S4 batching. "
            f"consistency_rate={consistency_rate} active_set_change_rate={active_set_change_rate}"
        ),
        mean_relative_error=float(np.mean(rels)) if rels else None,
        mean_absolute_error=float(np.mean(abss)) if abss else None,
        regime_counts=regime_counts,
        consistency_rate=consistency_rate,
        active_set_change_rate=active_set_change_rate,
        flag_counts=flag_counts,
    )


def frontier_points_as_neighbors(points: list[FrontierPoint], *, base_index: int = 0) -> list[dict[str, float]]:
    base = points[base_index].parameters
    return [p.parameters for i, p in enumerate(points) if i != base_index and p.parameters != base]

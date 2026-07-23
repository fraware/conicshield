"""Sensitivity metrics required by Track 2 R2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.experimental.gradients.modes import GradientMode


@dataclass(slots=True)
class SensitivityMetrics:
    parameter_name: str
    mode: GradientMode
    jacobian: np.ndarray
    jacobian_norm: float
    largest_singular_value: float
    directional_derivatives: dict[str, float]
    finite_difference_agreement: float | None
    exact_versus_smoothed_agreement: float | None
    perturbation_radius: float
    active_set_identity: tuple[str, ...]
    active_set_change_within_perturbation: bool
    primal_residual_before: float
    primal_residual_after: float
    shadow_solver_gradient_disagreement: float | None
    backward_pass_runtime_sec: float | None
    backward_pass_failure_status: str | None
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "parameter_name": self.parameter_name,
            "mode": str(self.mode),
            "jacobian": self.jacobian.tolist(),
            "jacobian_norm": self.jacobian_norm,
            "largest_singular_value": self.largest_singular_value,
            "directional_derivatives": dict(self.directional_derivatives),
            "finite_difference_agreement": self.finite_difference_agreement,
            "exact_versus_smoothed_agreement": self.exact_versus_smoothed_agreement,
            "perturbation_radius": self.perturbation_radius,
            "active_set_identity": list(self.active_set_identity),
            "active_set_change_within_perturbation": self.active_set_change_within_perturbation,
            "primal_residual_before": self.primal_residual_before,
            "primal_residual_after": self.primal_residual_after,
            "shadow_solver_gradient_disagreement": self.shadow_solver_gradient_disagreement,
            "backward_pass_runtime_sec": self.backward_pass_runtime_sec,
            "backward_pass_failure_status": self.backward_pass_failure_status,
            "extras": dict(self.extras),
        }


def metrics_from_jacobian(
    *,
    parameter_name: str,
    mode: GradientMode,
    jacobian: np.ndarray,
    perturbation_radius: float,
    active_set_identity: tuple[str, ...] = (),
    active_set_change_within_perturbation: bool = False,
    primal_residual_before: float = 0.0,
    primal_residual_after: float = 0.0,
    finite_difference_agreement: float | None = None,
    exact_versus_smoothed_agreement: float | None = None,
    shadow_solver_gradient_disagreement: float | None = None,
    backward_pass_runtime_sec: float | None = None,
    backward_pass_failure_status: str | None = None,
    direction: np.ndarray | None = None,
) -> SensitivityMetrics:
    jac = np.asarray(jacobian, dtype=np.float64)
    fro = float(np.linalg.norm(jac, ord="fro"))
    if jac.size == 0:
        sigma_max = 0.0
    else:
        try:
            sigma_max = float(np.linalg.svd(jac, compute_uv=False)[0])
        except np.linalg.LinAlgError:
            sigma_max = float("nan")
    dir_derivs: dict[str, float] = {}
    if direction is not None and jac.ndim == 2 and jac.shape[1] == direction.size:
        d = np.asarray(direction, dtype=np.float64).reshape(-1)
        v = jac @ d
        dir_derivs["custom"] = float(np.linalg.norm(v))
    if jac.ndim == 2 and jac.shape[1] > 0:
        e0 = np.zeros(jac.shape[1], dtype=np.float64)
        e0[0] = 1.0
        dir_derivs["e0"] = float(np.linalg.norm(jac @ e0))
    return SensitivityMetrics(
        parameter_name=parameter_name,
        mode=mode,
        jacobian=jac,
        jacobian_norm=fro,
        largest_singular_value=sigma_max,
        directional_derivatives=dir_derivs,
        finite_difference_agreement=finite_difference_agreement,
        exact_versus_smoothed_agreement=exact_versus_smoothed_agreement,
        perturbation_radius=perturbation_radius,
        active_set_identity=active_set_identity,
        active_set_change_within_perturbation=active_set_change_within_perturbation,
        primal_residual_before=primal_residual_before,
        primal_residual_after=primal_residual_after,
        shadow_solver_gradient_disagreement=shadow_solver_gradient_disagreement,
        backward_pass_runtime_sec=backward_pass_runtime_sec,
        backward_pass_failure_status=backward_pass_failure_status,
    )

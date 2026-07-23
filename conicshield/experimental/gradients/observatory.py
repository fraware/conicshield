"""Safety-Gradient Observatory (R2 depth)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.experimental.gradients.exact_backend import exact_backend_gradient
from conicshield.experimental.gradients.finite_difference import (
    central_finite_difference_jacobian,
    fd_agreement_metric,
    one_sided_finite_difference_jacobian,
)
from conicshield.experimental.gradients.kkt_research import exact_research_kkt_jacobian
from conicshield.experimental.gradients.metrics import SensitivityMetrics, metrics_from_jacobian
from conicshield.experimental.gradients.modes import GradientMode
from conicshield.experimental.gradients.smoothed_backend import smoothed_backend_gradient
from conicshield.experimental.gradients.smoothed_research import smoothed_research_projection_jacobian
from conicshield.experimental.solver_assurance.backends import create_research_projector
from conicshield.specs.schema import SafetySpec

DIFFERENTIATION_TARGETS: tuple[str, ...] = (
    "policy_logits",
    "proposed_action_probabilities",
    "previous_action",
    "reference_action",
    "policy_weight",
    "reference_weight",
    "box_bounds",
    "rate_limits",
    "hazard_derived_parameters",
    "robustness_margins",
)


@dataclass(slots=True)
class ObservatoryReport:
    scenario_id: str
    metrics: list[SensitivityMetrics] = field(default_factory=list)
    exact_backend: dict[str, Any] = field(default_factory=dict)
    smoothed_backend: dict[str, Any] = field(default_factory=dict)
    exact_research_kkt: dict[str, Any] = field(default_factory=dict)
    smoothed_research_projection: dict[str, Any] = field(default_factory=dict)
    active_set_at_base: tuple[str, ...] = ()
    notes: str = ""
    corpus_version: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "corpus_version": self.corpus_version,
            "metrics": [m.as_dict() for m in self.metrics],
            "exact_backend": self.exact_backend,
            "smoothed_backend": self.smoothed_backend,
            "exact_research_kkt": self.exact_research_kkt,
            "smoothed_research_projection": self.smoothed_research_projection,
            "active_set_at_base": list(self.active_set_at_base),
            "notes": self.notes,
            "differentiation_targets": list(DIFFERENTIATION_TARGETS),
            "mode_separation_note": (
                "Gradient modes are recorded distinctly. "
                "exact_backend_gradient uses Moreau CompiledSolver.backward; "
                "smoothed_backend_gradient uses softplus inequality softening on the "
                "Moreau shield QP (experimental). "
                "exact_research_kkt / smoothed_research_projection are research adapters "
                "and must never be relabeled as native Moreau backend gradients. "
                "Production BackendCapabilities.differentiation_api remains a separate "
                "identity-symbol flag."
            ),
        }


def observe_proposed_action_fd(
    *,
    spec: SafetySpec,
    proposed_action: np.ndarray,
    previous_action: np.ndarray,
    reference_action: np.ndarray,
    policy_weight: float = 1.0,
    reference_weight: float = 0.0,
    h: float = 1e-5,
    backend_id: str = "cvxpy_clarabel",
    scenario_id: str = "adhoc",
    corpus_version: str | None = None,
    include_research_gradients: bool = True,
    smoothing_epsilon: float = 1e-2,
) -> ObservatoryReport:
    """FD sensitivities of corrected action w.r.t. proposed action (+ optional research grads)."""

    def _project(p: np.ndarray) -> Any:
        projector = create_research_projector(backend_id=backend_id, spec=spec)
        return projector.project(
            p,
            previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
        )

    def forward(p: np.ndarray) -> np.ndarray:
        return np.asarray(_project(p).corrected_action, dtype=np.float64)

    def active_set_fn(p: np.ndarray) -> tuple[str, ...]:
        return tuple(_project(p).active_constraints)

    def residual_fn(p: np.ndarray) -> tuple[float, float]:
        r = _project(p)
        return float(r.equality_residual or 0.0), float(r.inequality_residual or 0.0)

    x0 = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
    central = central_finite_difference_jacobian(
        forward,
        x0,
        h=h,
        parameter_name="proposed_action",
        active_set_fn=active_set_fn,
        residual_fn=residual_fn,
    )
    onesided = one_sided_finite_difference_jacobian(
        forward,
        x0,
        h=h,
        parameter_name="proposed_action",
        active_set_fn=active_set_fn,
        residual_fn=residual_fn,
    )
    agree = fd_agreement_metric(central.jacobian, onesided.jacobian)

    metrics = [
        metrics_from_jacobian(
            parameter_name="proposed_action",
            mode=GradientMode.CENTRAL_FINITE_DIFFERENCE,
            jacobian=central.jacobian,
            perturbation_radius=h,
            finite_difference_agreement=agree,
            active_set_identity=central.active_set_at_base,
            active_set_change_within_perturbation=central.active_set_changed,
            primal_residual_before=central.primal_residual_before,
            primal_residual_after=central.primal_residual_after,
            backward_pass_runtime_sec=central.runtime_sec,
            backward_pass_failure_status=central.failure_status,
            exact_versus_smoothed_agreement=None,
        ),
        metrics_from_jacobian(
            parameter_name="proposed_action",
            mode=GradientMode.ONE_SIDED_FINITE_DIFFERENCE,
            jacobian=onesided.jacobian,
            perturbation_radius=h,
            finite_difference_agreement=agree,
            active_set_identity=onesided.active_set_at_base,
            active_set_change_within_perturbation=onesided.active_set_changed,
            primal_residual_before=onesided.primal_residual_before,
            primal_residual_after=onesided.primal_residual_after,
            backward_pass_runtime_sec=onesided.runtime_sec,
            backward_pass_failure_status=onesided.failure_status,
        ),
    ]

    kkt_dict: dict[str, Any] = {}
    sm_dict: dict[str, Any] = {}
    if include_research_gradients:
        kkt = exact_research_kkt_jacobian(
            spec=spec,
            proposed_action=x0,
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            backend_id=backend_id,
            compare_central_fd=True,
            fd_h=h,
        )
        kkt_dict = kkt.as_dict()
        if kkt.available and kkt.jacobian is not None:
            metrics.append(
                metrics_from_jacobian(
                    parameter_name="proposed_action",
                    mode=GradientMode.EXACT_RESEARCH_KKT,
                    jacobian=kkt.jacobian,
                    perturbation_radius=0.0,
                    finite_difference_agreement=kkt.agreement_vs_central_fd,
                    active_set_identity=kkt.active_set,
                    active_set_change_within_perturbation=False,
                    backward_pass_runtime_sec=kkt.runtime_sec,
                    backward_pass_failure_status=None,
                )
            )
        else:
            metrics.append(
                metrics_from_jacobian(
                    parameter_name="proposed_action",
                    mode=GradientMode.EXACT_RESEARCH_KKT,
                    jacobian=np.zeros((x0.size, x0.size)),
                    perturbation_radius=0.0,
                    active_set_identity=kkt.active_set,
                    active_set_change_within_perturbation="active_set_change" in (kkt.reason or ""),
                    backward_pass_runtime_sec=kkt.runtime_sec,
                    backward_pass_failure_status=kkt.reason,
                )
            )

        sm = smoothed_research_projection_jacobian(
            spec=spec,
            proposed_action=x0,
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            epsilon=smoothing_epsilon,
            backend_id=backend_id,
            compare_fd=True,
            fd_h=h,
        )
        sm_dict = sm.as_dict()
        if sm.available and sm.jacobian is not None:
            metrics.append(
                metrics_from_jacobian(
                    parameter_name="proposed_action",
                    mode=GradientMode.SMOOTHED_RESEARCH_PROJECTION,
                    jacobian=sm.jacobian,
                    perturbation_radius=float(smoothing_epsilon),
                    finite_difference_agreement=sm.agreement_vs_hard_central_fd,
                    active_set_identity=central.active_set_at_base,
                    backward_pass_runtime_sec=sm.runtime_sec,
                    backward_pass_failure_status=None,
                )
            )
        else:
            metrics.append(
                metrics_from_jacobian(
                    parameter_name="proposed_action",
                    mode=GradientMode.SMOOTHED_RESEARCH_PROJECTION,
                    jacobian=np.zeros((x0.size, x0.size)),
                    perturbation_radius=float(smoothing_epsilon),
                    active_set_identity=central.active_set_at_base,
                    backward_pass_runtime_sec=sm.runtime_sec,
                    backward_pass_failure_status=sm.reason,
                )
            )

    return ObservatoryReport(
        scenario_id=scenario_id,
        metrics=metrics,
        exact_backend=exact_backend_gradient(
            spec=spec,
            proposed_action=x0,
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            compare_central_fd=False,
        ).as_dict(),
        smoothed_backend=smoothed_backend_gradient(
            spec=spec,
            proposed_action=x0,
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            smoothing_parameter=smoothing_epsilon,
            compare_central_fd=False,
            compare_exact_backend=False,
        ).as_dict(),
        exact_research_kkt=kkt_dict,
        smoothed_research_projection=sm_dict,
        active_set_at_base=central.active_set_at_base,
        corpus_version=corpus_version,
        notes=(
            "FD modes implemented with active-set / residual / runtime / failure fields. "
            "exact_backend_gradient uses CompiledSolver.backward when Moreau is live; "
            "smoothed_backend_gradient uses softplus inequality softening on the Moreau QP. "
            "Both fail closed (UNAVAILABLE) when Moreau is absent (e.g. native Windows). "
            "exact_research_kkt / smoothed_research_projection are labeled research adapters."
        ),
    )


def render_observatory_report_markdown(
    reports: list[ObservatoryReport] | list[dict[str, Any]],
    *,
    template_path: Path | None = None,
) -> str:
    """Fill GRADIENT_OBSERVATORY_REPORT.md from machine-readable observatory data."""

    rows: list[dict[str, Any]] = []
    for r in reports:
        rows.append(r.as_dict() if isinstance(r, ObservatoryReport) else dict(r))

    n = len(rows)
    jac_norms: list[float] = []
    agrees: list[float] = []
    active_changes = 0
    failures = 0
    kkt_ok = 0
    kkt_fail = 0
    sm_ok = 0
    sm_fail = 0
    kkt_fd_agrees: list[float] = []
    exact_backend_statuses: list[str] = []
    smoothed_backend_statuses: list[str] = []
    for row in rows:
        eb = row.get("exact_backend") or {}
        sb = row.get("smoothed_backend") or {}
        if eb.get("status") is not None:
            exact_backend_statuses.append(str(eb.get("status")))
        if sb.get("status") is not None:
            smoothed_backend_statuses.append(str(sb.get("status")))
        for m in row.get("metrics") or []:
            if m.get("mode") == str(GradientMode.CENTRAL_FINITE_DIFFERENCE):
                jac_norms.append(float(m.get("jacobian_norm") or 0.0))
                if m.get("finite_difference_agreement") is not None:
                    agrees.append(float(m["finite_difference_agreement"]))
                if m.get("active_set_change_within_perturbation"):
                    active_changes += 1
                if m.get("backward_pass_failure_status"):
                    failures += 1
            if m.get("mode") == str(GradientMode.EXACT_RESEARCH_KKT):
                if m.get("backward_pass_failure_status"):
                    kkt_fail += 1
                else:
                    kkt_ok += 1
                    if m.get("finite_difference_agreement") is not None:
                        kkt_fd_agrees.append(float(m["finite_difference_agreement"]))
            if m.get("mode") == str(GradientMode.SMOOTHED_RESEARCH_PROJECTION):
                if m.get("backward_pass_failure_status"):
                    sm_fail += 1
                else:
                    sm_ok += 1

    mean_norm = float(np.mean(jac_norms)) if jac_norms else float("nan")
    mean_agree = float(np.mean(agrees)) if agrees else float("nan")
    mean_kkt_fd = float(np.mean(kkt_fd_agrees)) if kkt_fd_agrees else float("nan")
    exact_status_summary = ",".join(sorted(set(exact_backend_statuses))) if exact_backend_statuses else "n/a"
    smoothed_status_summary = ",".join(sorted(set(smoothed_backend_statuses))) if smoothed_backend_statuses else "n/a"

    template = ""
    if template_path is not None and template_path.is_file():
        template = template_path.read_text(encoding="utf-8").rstrip() + "\n\n"
    else:
        template = "# Safety-Gradient Observatory report\n\n"

    body = f"""## Machine-filled summary

- scenarios_observed: {n}
- mean_central_jacobian_frobenius_norm: {mean_norm:.6g}
- mean_central_vs_onesided_fd_agreement (relative fro): {mean_agree:.6g}
- active_set_changes_within_perturbation: {active_changes}
- backward_pass_failures: {failures}
- exact_backend_gradient status(es): {exact_status_summary}
- smoothed_backend_gradient status(es): {smoothed_status_summary}
- exact_research_kkt available/fail: {kkt_ok}/{kkt_fail}
- exact_research_kkt vs central FD mean relative fro: {mean_kkt_fd:.6g}
- smoothed_research_projection available/fail: {sm_ok}/{sm_fail}

## Stability notes

- Gradients are treated as ambiguous when FD agreement is NaN or active-set changes within the perturbation radius.
- exact_research_kkt is a fixed-active-set KKT adapter on the public QP — not native Moreau.
- smoothed_research_projection uses explicit epsilon quadratic-penalty smoothing — not smoothed_backend_gradient.
- Native exact uses CompiledSolver.backward; smoothed uses softplus inequality
  softening on the Moreau QP (experimental). Production differentiation_api
  identity flag is separate.

## Per-scenario (compact)

| scenario_id | jac_norm | fd_agreement | active_set_change | failure |
| --- | ---: | ---: | ---: | --- |
"""
    for row in rows:
        sid = row.get("scenario_id", "")
        central: dict[str, Any] = next(
            (m for m in (row.get("metrics") or []) if m.get("mode") == str(GradientMode.CENTRAL_FINITE_DIFFERENCE)),
            {},
        )
        body += (
            f"| {sid} | {float(central.get('jacobian_norm') or float('nan')):.6g} | "
            f"{central.get('finite_difference_agreement')} | "
            f"{central.get('active_set_change_within_perturbation')} | "
            f"{central.get('backward_pass_failure_status')} |\n"
        )
    return template + body

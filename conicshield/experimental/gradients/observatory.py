"""Current Moreau Gradient Observatory (R11).

Forward-gated, independently labeled adapters. Does not claim production
``BackendCapabilities.differentiation_api``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.experimental.gradients.active_set_protocol import (
    probe_active_set_transition_all_coords,
    transition_aware_jacobians,
)
from conicshield.experimental.gradients.adapters import (
    DIFFERENTIATION_TARGET_CATALOG,
    IMPLEMENTED_DIFFERENTIATION_TARGETS,
    AdapterId,
    list_implemented_adapters,
    run_central_fd,
    run_jax_autodiff,
    run_native_smoothed,
    run_numpy_compiled_backward,
    run_one_sided_fd,
    run_pytorch_autograd,
    run_research_kkt,
)
from conicshield.experimental.gradients.exact_backend import exact_backend_gradient
from conicshield.experimental.gradients.finite_difference import fd_agreement_metric
from conicshield.experimental.gradients.forward_gate import (
    DEFAULT_RESIDUAL_TOLERANCE,
    VerifiedForward,
    verify_forward_projection,
)
from conicshield.experimental.gradients.metrics import SensitivityMetrics, metrics_from_jacobian
from conicshield.experimental.gradients.modes import GradientMode
from conicshield.experimental.gradients.smoothed_backend import smoothed_backend_gradient
from conicshield.experimental.gradients.smoothed_study import run_smoothed_study
from conicshield.experimental.gradients.step_size_study import run_step_size_study
from conicshield.experimental.solver_assurance.backends import create_research_projector
from conicshield.specs.schema import SafetySpec

# Back-compat alias: historical name listed aspirational targets. Prefer
# IMPLEMENTED_DIFFERENTIATION_TARGETS for honesty about live paths.
DIFFERENTIATION_TARGETS: tuple[str, ...] = IMPLEMENTED_DIFFERENTIATION_TARGETS


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
    verified_forward: dict[str, Any] = field(default_factory=dict)
    adapters: dict[str, Any] = field(default_factory=dict)
    active_set_transition: dict[str, Any] = field(default_factory=dict)
    step_size_study: dict[str, Any] = field(default_factory=dict)
    smoothed_study: dict[str, Any] = field(default_factory=dict)
    gradient_unavailable: bool = False

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
            "differentiation_targets": list(IMPLEMENTED_DIFFERENTIATION_TARGETS),
            "differentiation_target_catalog": list(DIFFERENTIATION_TARGET_CATALOG),
            "implemented_adapters": list_implemented_adapters(),
            "verified_forward": dict(self.verified_forward),
            "adapters": dict(self.adapters),
            "active_set_transition": dict(self.active_set_transition),
            "step_size_study": dict(self.step_size_study),
            "smoothed_study": dict(self.smoothed_study),
            "gradient_unavailable": self.gradient_unavailable,
            "claims_production_differentiation_api": False,
            "mode_separation_note": (
                "Gradient modes are recorded distinctly. "
                "exact_backend_gradient / numpy_compiled_backward uses Moreau "
                "CompiledSolver.backward; smoothed_backend_gradient uses softplus "
                "inequality softening on the Moreau shield QP (experimental). "
                "pytorch_autograd / jax_autodiff are framework adapters. "
                "exact_research_kkt is an analytical comparator only. "
                "Production BackendCapabilities.differentiation_api remains a separate "
                "identity-symbol flag and is never claimed here. "
                "Unverified forward → all gradients unavailable."
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
    residual_tolerance: float = DEFAULT_RESIDUAL_TOLERANCE,
    run_step_size: bool = False,
    run_smoothed: bool = False,
    include_torch: bool = True,
    include_jax: bool = True,
) -> ObservatoryReport:
    """Forward-gated observatory for corrected action w.r.t. proposed action."""

    def _project(p: np.ndarray) -> Any:
        projector = create_research_projector(backend_id=backend_id, spec=spec)
        return projector.project(
            p,
            previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
        )

    def forward_map(p: np.ndarray) -> np.ndarray:
        return np.asarray(_project(p).corrected_action, dtype=np.float64)

    def active_set_fn(p: np.ndarray) -> tuple[str, ...]:
        return tuple(_project(p).active_constraints)

    def residual_fn(p: np.ndarray) -> tuple[float, float]:
        r = _project(p)
        return float(r.equality_residual or 0.0), float(r.inequality_residual or 0.0)

    x0 = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
    base_proj = _project(x0)
    verified = verify_forward_projection(
        primary=base_proj,
        spec=spec,
        previous_action=previous_action,
        reference_action=reference_action,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        residual_tolerance=residual_tolerance,
        require_feasible=True,
    )

    if not verified.verified:
        # Fail closed: no gradient artifacts without verified forward.
        return ObservatoryReport(
            scenario_id=scenario_id,
            metrics=[],
            exact_backend={"status": "unavailable", "reason": "unverified_forward"},
            smoothed_backend={"status": "unavailable", "reason": "unverified_forward"},
            exact_research_kkt={},
            active_set_at_base=tuple(base_proj.active_constraints or ()),
            corpus_version=corpus_version,
            verified_forward=verified.as_dict(),
            adapters={},
            gradient_unavailable=True,
            notes=f"Gradient unavailable: {verified.reason}",
        )

    transition = probe_active_set_transition_all_coords(x=x0, epsilon=h, active_set_fn=active_set_fn)
    transition_pack = transition_aware_jacobians(
        forward_map, x0, h=h, parameter_name="proposed_action", active_set_fn=active_set_fn
    )

    adapters: dict[str, Any] = {}
    metrics: list[SensitivityMetrics] = []

    central = run_central_fd(
        forward=verified, f=forward_map, h=h, active_set_fn=active_set_fn, residual_fn=residual_fn
    )
    onesided = run_one_sided_fd(
        forward=verified, f=forward_map, h=h, active_set_fn=active_set_fn, residual_fn=residual_fn
    )
    adapters[str(AdapterId.CENTRAL_FD)] = central.as_dict()
    adapters[str(AdapterId.ONE_SIDED_FD)] = onesided.as_dict()

    # Additional implemented differentiation targets (honest FD paths).
    from conicshield.experimental.gradients.adapters import (
        differentiate_target_central_fd,
        list_implemented_targets,
    )

    target_rows: dict[str, Any] = {}
    for tgt in ("previous_action", "reference_action", "policy_weight", "reference_weight", "box_bounds"):
        tgt_res = differentiate_target_central_fd(
            forward=verified,
            spec=spec,
            target=tgt,
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            h=h,
            backend_id=backend_id,
        )
        target_rows[tgt] = tgt_res.as_dict()
    adapters["differentiation_targets"] = {
        "registry": list_implemented_targets(),
        "results": target_rows,
    }

    agree = None
    if central.jacobian is not None and onesided.jacobian is not None:
        agree = fd_agreement_metric(central.jacobian, onesided.jacobian)

    prefer_one_sided = bool(transition.prefer_one_sided_derivatives)
    if central.available and central.jacobian is not None:
        metrics.append(
            metrics_from_jacobian(
                parameter_name="proposed_action",
                mode=GradientMode.CENTRAL_FINITE_DIFFERENCE,
                jacobian=central.jacobian,
                perturbation_radius=h,
                finite_difference_agreement=agree,
                active_set_identity=verified.active_set,
                active_set_change_within_perturbation=prefer_one_sided,
                primal_residual_before=float(abs(verified.equality_residual or 0.0) + abs(verified.inequality_residual or 0.0)),
                backward_pass_runtime_sec=central.runtime_sec,
                backward_pass_failure_status=None if central.available else central.reason,
                exact_versus_smoothed_agreement=None,
            )
        )
    if onesided.available and onesided.jacobian is not None:
        metrics.append(
            metrics_from_jacobian(
                parameter_name="proposed_action",
                mode=GradientMode.ONE_SIDED_FINITE_DIFFERENCE,
                jacobian=onesided.jacobian,
                perturbation_radius=h,
                finite_difference_agreement=agree,
                active_set_identity=verified.active_set,
                active_set_change_within_perturbation=prefer_one_sided,
                backward_pass_runtime_sec=onesided.runtime_sec,
                backward_pass_failure_status=None if onesided.available else onesided.reason,
            )
        )

    numpy_ex = run_numpy_compiled_backward(
        forward=verified,
        spec=spec,
        previous_action=previous_action,
        reference_action=reference_action,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        compare_central_fd=False,
    )
    adapters[str(AdapterId.NUMPY_COMPILED_BACKWARD)] = numpy_ex.as_dict()

    native_sm = run_native_smoothed(
        forward=verified,
        spec=spec,
        previous_action=previous_action,
        reference_action=reference_action,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        smoothing_parameter=smoothing_epsilon,
        compare_central_fd=False,
    )
    adapters[str(AdapterId.NATIVE_SMOOTHED)] = native_sm.as_dict()

    if include_torch:
        torch_ad = run_pytorch_autograd(
            forward=verified,
            spec=spec,
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            smoothing_parameter=smoothing_epsilon,
        )
        adapters[str(AdapterId.PYTORCH_AUTOGRAD)] = torch_ad.as_dict()
        if torch_ad.available and torch_ad.jacobian is not None:
            metrics.append(
                metrics_from_jacobian(
                    parameter_name="proposed_action",
                    mode=GradientMode.PYTORCH_AUTOGRAD,
                    jacobian=torch_ad.jacobian,
                    perturbation_radius=float(smoothing_epsilon),
                    active_set_identity=verified.active_set,
                    backward_pass_runtime_sec=torch_ad.runtime_sec,
                )
            )

    if include_jax:
        jax_ad = run_jax_autodiff(
            forward=verified,
            spec=spec,
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            smoothing_parameter=smoothing_epsilon,
        )
        adapters[str(AdapterId.JAX_AUTODIFF)] = jax_ad.as_dict()
        if jax_ad.available and jax_ad.jacobian is not None:
            metrics.append(
                metrics_from_jacobian(
                    parameter_name="proposed_action",
                    mode=GradientMode.JAX_AUTODIFF,
                    jacobian=jax_ad.jacobian,
                    perturbation_radius=float(smoothing_epsilon),
                    active_set_identity=verified.active_set,
                    backward_pass_runtime_sec=jax_ad.runtime_sec,
                )
            )

    kkt_dict: dict[str, Any] = {}
    if include_research_gradients:
        kkt_ad = run_research_kkt(
            forward=verified,
            spec=spec,
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            backend_id=backend_id,
        )
        adapters[str(AdapterId.RESEARCH_KKT)] = kkt_ad.as_dict()
        kkt_dict = kkt_ad.extras.get("kkt") or kkt_ad.as_dict()
        if kkt_ad.available and kkt_ad.jacobian is not None:
            metrics.append(
                metrics_from_jacobian(
                    parameter_name="proposed_action",
                    mode=GradientMode.EXACT_RESEARCH_KKT,
                    jacobian=kkt_ad.jacobian,
                    perturbation_radius=0.0,
                    finite_difference_agreement=None,
                    active_set_identity=verified.active_set,
                    active_set_change_within_perturbation=prefer_one_sided,
                    backward_pass_runtime_sec=kkt_ad.runtime_sec,
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
                    active_set_identity=verified.active_set,
                    active_set_change_within_perturbation=prefer_one_sided,
                    backward_pass_runtime_sec=kkt_ad.runtime_sec,
                    backward_pass_failure_status=kkt_ad.reason,
                )
            )

    step_report: dict[str, Any] = {}
    if run_step_size:
        step_report = run_step_size_study(
            forward_map, x0, parameter_name="proposed_action", active_set_fn=active_set_fn
        ).as_dict()

    smoothed_report: dict[str, Any] = {}
    if run_smoothed:
        smoothed_report = run_smoothed_study(
            spec=spec,
            proposed_action=x0,
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            backend_id=backend_id,
            scenario_id=scenario_id,
            residual_tolerance=residual_tolerance,
            fd_h=h,
        ).as_dict()

    # Keep legacy exact/smoothed fields for existing tests / wave scripts.
    exact_backend = exact_backend_gradient(
        spec=spec,
        proposed_action=x0,
        previous_action=previous_action,
        reference_action=reference_action,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        compare_central_fd=False,
    ).as_dict()
    exact_backend["forward_solution_digest"] = verified.forward_solution_digest
    exact_backend["problem_digest"] = verified.problem_digest

    smoothed_backend = smoothed_backend_gradient(
        spec=spec,
        proposed_action=x0,
        previous_action=previous_action,
        reference_action=reference_action,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        smoothing_parameter=smoothing_epsilon,
        compare_central_fd=False,
        compare_exact_backend=False,
    ).as_dict()
    smoothed_backend["forward_solution_digest"] = verified.forward_solution_digest
    smoothed_backend["problem_digest"] = verified.problem_digest

    return ObservatoryReport(
        scenario_id=scenario_id,
        metrics=metrics,
        exact_backend=exact_backend,
        smoothed_backend=smoothed_backend,
        exact_research_kkt=kkt_dict,
        smoothed_research_projection={},
        active_set_at_base=verified.active_set,
        corpus_version=corpus_version,
        verified_forward=verified.as_dict(),
        adapters=adapters,
        active_set_transition={**transition.as_dict(), **{"transition_aware": transition_pack}},
        step_size_study=step_report,
        smoothed_study=smoothed_report,
        gradient_unavailable=False,
        notes=(
            "R11 forward-gated observatory. Gradients bind verified "
            f"forward_solution_digest={verified.forward_solution_digest[:16]}…. "
            "At active-set transitions prefer one-sided derivatives; central FD "
            "is not treated as a unique Jacobian. "
            "Production differentiation_api is not claimed."
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
    gated = 0
    exact_backend_statuses: list[str] = []
    smoothed_backend_statuses: list[str] = []
    for row in rows:
        if row.get("gradient_unavailable"):
            gated += 1
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

    mean_norm = float(np.mean(jac_norms)) if jac_norms else float("nan")
    mean_agree = float(np.mean(agrees)) if agrees else float("nan")
    exact_status_summary = ",".join(sorted(set(exact_backend_statuses))) if exact_backend_statuses else "n/a"
    smoothed_status_summary = ",".join(sorted(set(smoothed_backend_statuses))) if smoothed_backend_statuses else "n/a"

    if template_path is not None and template_path.is_file():
        template = template_path.read_text(encoding="utf-8").rstrip() + "\n\n"
    else:
        template = "# Safety-Gradient Observatory report\n\n"

    body = f"""## Machine-filled summary

- scenarios_observed: {n}
- forward_gate_blocked: {gated}
- mean_central_jacobian_frobenius_norm: {mean_norm:.6g}
- mean_central_vs_onesided_fd_agreement (relative fro): {mean_agree:.6g}
- active_set_changes_within_perturbation: {active_changes}
- backward_pass_failures: {failures}
- exact_backend_gradient status(es): {exact_status_summary}
- smoothed_backend_gradient status(es): {smoothed_status_summary}
- exact_research_kkt available/fail: {kkt_ok}/{kkt_fail}
- implemented_targets: {", ".join(IMPLEMENTED_DIFFERENTIATION_TARGETS)}
- claims_production_differentiation_api: false

## Stability notes

- Gradients require verified forward (canonical status, residuals, problem_digest, finite values).
- Active-set transitions (base/+ε/−ε) classify stable|one_sided|two_sided|ambiguous; prefer one-sided derivatives at transitions.
- exact_research_kkt is an analytical comparator only — not native Moreau.
- Production differentiation_api identity flag is separate and not claimed.

## Per-scenario (compact)

| scenario_id | jac_norm | fd_agreement | active_set_change | gated |
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
            f"{row.get('gradient_unavailable')} |\n"
        )
    return template + body


# Re-export for type checkers / callers.
__all__ = [
    "DIFFERENTIATION_TARGETS",
    "IMPLEMENTED_DIFFERENTIATION_TARGETS",
    "ObservatoryReport",
    "VerifiedForward",
    "observe_proposed_action_fd",
    "render_observatory_report_markdown",
]

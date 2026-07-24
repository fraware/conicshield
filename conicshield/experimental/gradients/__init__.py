"""Exports for Safety-Gradient Observatory (Track 2 / R11)."""

from __future__ import annotations

from typing import Any

from conicshield.experimental.gradients.agreement_study import (
    render_agreement_report_markdown,
    run_agreement_study,
)
from conicshield.experimental.gradients.capability import CapabilityStatus
from conicshield.experimental.gradients.dual_pressure import (
    DualPressureCorrelationStudy,
    correlate_dual_pressure,
    normalize_dual_pressure,
)
from conicshield.experimental.gradients.exact_backend import exact_backend_gradient
from conicshield.experimental.gradients.finite_difference import (
    central_finite_difference_jacobian,
    directional_derivative,
    fd_agreement_metric,
    one_sided_finite_difference_jacobian,
)
from conicshield.experimental.gradients.kkt_research import exact_research_kkt_jacobian
from conicshield.experimental.gradients.modes import GradientMode
from conicshield.experimental.gradients.observatory import (
    DIFFERENTIATION_TARGETS,
    observe_proposed_action_fd,
    render_observatory_report_markdown,
)
from conicshield.experimental.gradients.smoothed_backend import smoothed_backend_gradient
from conicshield.experimental.gradients.smoothed_research import smoothed_research_projection_jacobian

__all__ = [
    "ActiveSetTransitionClass",
    "AdapterId",
    "CapabilityStatus",
    "DIFFERENTIATION_TARGET_CATALOG",
    "DIFFERENTIATION_TARGETS",
    "DualPressureCorrelationStudy",
    "GradientMode",
    "IMPLEMENTED_DIFFERENTIATION_TARGETS",
    "VerifiedForward",
    "central_finite_difference_jacobian",
    "classify_active_set_transition",
    "correlate_dual_pressure",
    "directional_derivative",
    "exact_backend_gradient",
    "exact_research_kkt_jacobian",
    "fd_agreement_metric",
    "list_implemented_adapters",
    "normalize_dual_pressure",
    "observe_proposed_action_fd",
    "one_sided_finite_difference_jacobian",
    "probe_active_set_transition",
    "render_agreement_report_markdown",
    "render_observatory_report_markdown",
    "run_agreement_study",
    "run_smoothed_study",
    "run_step_size_study",
    "smoothed_backend_gradient",
    "smoothed_research_projection_jacobian",
    "verify_forward_projection",
]

# R11 surfaces that import assurance must stay lazy to avoid
# adapters → gradients → assurance → solver_assurance cycles.
_LAZY = {
    "ActiveSetTransitionClass": ("conicshield.experimental.gradients.active_set_protocol", "ActiveSetTransitionClass"),
    "AdapterId": ("conicshield.experimental.gradients.adapters", "AdapterId"),
    "DIFFERENTIATION_TARGET_CATALOG": (
        "conicshield.experimental.gradients.adapters",
        "DIFFERENTIATION_TARGET_CATALOG",
    ),
    "IMPLEMENTED_DIFFERENTIATION_TARGETS": (
        "conicshield.experimental.gradients.adapters",
        "IMPLEMENTED_DIFFERENTIATION_TARGETS",
    ),
    "VerifiedForward": ("conicshield.experimental.gradients.forward_gate", "VerifiedForward"),
    "classify_active_set_transition": (
        "conicshield.experimental.gradients.active_set_protocol",
        "classify_active_set_transition",
    ),
    "list_implemented_adapters": ("conicshield.experimental.gradients.adapters", "list_implemented_adapters"),
    "probe_active_set_transition": (
        "conicshield.experimental.gradients.active_set_protocol",
        "probe_active_set_transition",
    ),
    "run_smoothed_study": ("conicshield.experimental.gradients.smoothed_study", "run_smoothed_study"),
    "run_step_size_study": ("conicshield.experimental.gradients.step_size_study", "run_step_size_study"),
    "verify_forward_projection": ("conicshield.experimental.gradients.forward_gate", "verify_forward_projection"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        import importlib

        mod_name, attr = _LAZY[name]
        return getattr(importlib.import_module(mod_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

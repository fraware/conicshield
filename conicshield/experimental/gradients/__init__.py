"""Safety-Gradient Observatory (Track 2 R2)."""

from __future__ import annotations

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
    observe_proposed_action_fd,
    render_observatory_report_markdown,
)
from conicshield.experimental.gradients.smoothed_backend import smoothed_backend_gradient
from conicshield.experimental.gradients.smoothed_research import smoothed_research_projection_jacobian

__all__ = [
    "CapabilityStatus",
    "DualPressureCorrelationStudy",
    "GradientMode",
    "central_finite_difference_jacobian",
    "correlate_dual_pressure",
    "directional_derivative",
    "exact_backend_gradient",
    "exact_research_kkt_jacobian",
    "fd_agreement_metric",
    "normalize_dual_pressure",
    "observe_proposed_action_fd",
    "one_sided_finite_difference_jacobian",
    "render_agreement_report_markdown",
    "render_observatory_report_markdown",
    "run_agreement_study",
    "smoothed_backend_gradient",
    "smoothed_research_projection_jacobian",
]

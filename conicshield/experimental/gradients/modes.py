"""Gradient mode identifiers — never combine into an unlabeled gradient."""

from __future__ import annotations

from enum import StrEnum


class GradientMode(StrEnum):
    # Native / vendor paths — experimental Moreau backends (not production claims).
    EXACT_BACKEND_GRADIENT = "exact_backend_gradient"
    SMOOTHED_BACKEND_GRADIENT = "smoothed_backend_gradient"
    # Framework autodiff adapters (research-labeled; not production differentiation_api).
    PYTORCH_AUTOGRAD = "pytorch_autograd"
    JAX_AUTODIFF = "jax_autodiff"
    # Research adapters — NEVER alias to the native mode names above.
    EXACT_RESEARCH_KKT = "exact_research_kkt"
    SMOOTHED_RESEARCH_PROJECTION = "smoothed_research_projection"
    # Finite-difference baselines (always labeled distinctly).
    CENTRAL_FINITE_DIFFERENCE = "central_finite_difference"
    ONE_SIDED_FINITE_DIFFERENCE = "one_sided_finite_difference"

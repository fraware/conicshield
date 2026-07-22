"""Backend adapters and canonical status normalization."""

from conicshield.backends.status import (
    CanonicalSolverStatus,
    normalize_cvxpy_status,
    normalize_moreau_status,
    normalize_solver_status,
)

__all__ = [
    "CanonicalSolverStatus",
    "normalize_cvxpy_status",
    "normalize_moreau_status",
    "normalize_solver_status",
]

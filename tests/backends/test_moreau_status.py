"""Moreau SolverStatus integer / name adapters (fail-closed for unknowns)."""

from __future__ import annotations

import pytest

from conicshield.backends.status import CanonicalSolverStatus, normalize_moreau_status


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (1, CanonicalSolverStatus.OPTIMAL),
        ("1", CanonicalSolverStatus.OPTIMAL),
        (4, CanonicalSolverStatus.OPTIMAL_INACCURATE),
        ("4", CanonicalSolverStatus.OPTIMAL_INACCURATE),
        (2, CanonicalSolverStatus.INFEASIBLE),
        (3, CanonicalSolverStatus.UNBOUNDED),
        (7, CanonicalSolverStatus.ITERATION_LIMIT),
        (8, CanonicalSolverStatus.TIME_LIMIT),
        (9, CanonicalSolverStatus.NUMERICAL_ERROR),
        (0, CanonicalSolverStatus.UNKNOWN),
        (99, CanonicalSolverStatus.UNKNOWN),
        ("Solved", CanonicalSolverStatus.OPTIMAL),
        ("AlmostSolved", CanonicalSolverStatus.OPTIMAL_INACCURATE),
        ("MaxIterations", CanonicalSolverStatus.ITERATION_LIMIT),
        ("SolverStatus.Solved", CanonicalSolverStatus.OPTIMAL),
        (None, CanonicalSolverStatus.UNKNOWN),
        ("solved", CanonicalSolverStatus.OPTIMAL),
    ],
)
def test_normalize_moreau_status_codes(raw: object, expected: CanonicalSolverStatus) -> None:
    assert normalize_moreau_status(raw) is expected


def test_normalize_moreau_status_rejects_bool() -> None:
    # bool is a subclass of int; must not treat True as Solved(1).
    assert normalize_moreau_status(True) is CanonicalSolverStatus.UNKNOWN
    assert normalize_moreau_status(False) is CanonicalSolverStatus.UNKNOWN

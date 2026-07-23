"""Canonical solver status enum and backend-specific adapters.

Unknown raw statuses map to ``UNKNOWN`` — never to a success class.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class CanonicalSolverStatus(StrEnum):
    """Backend-independent solver termination status."""

    OPTIMAL = "optimal"
    OPTIMAL_INACCURATE = "optimal_inaccurate"
    INFEASIBLE = "infeasible"
    UNBOUNDED = "unbounded"
    ITERATION_LIMIT = "iteration_limit"
    TIME_LIMIT = "time_limit"
    NUMERICAL_ERROR = "numerical_error"
    BACKEND_ERROR = "backend_error"
    UNKNOWN = "unknown"


def _as_token(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, CanonicalSolverStatus):
        return raw.value
    text = str(raw).strip()
    if not text:
        return ""
    # Normalize separators and case for matching.
    return text.lower().replace("-", "_").replace(" ", "_")


def normalize_solver_status(raw: Any, *, backend: str | None = None) -> CanonicalSolverStatus:
    """Map an arbitrary backend status token to ``CanonicalSolverStatus``.

    Explicit mappings only. Anything unrecognized becomes ``UNKNOWN``.
    """
    del backend  # reserved for future backend-scoped overrides
    token = _as_token(raw)
    if not token:
        return CanonicalSolverStatus.UNKNOWN

    # Exact / alias tables (success first, then terminal failures).
    exact: dict[str, CanonicalSolverStatus] = {
        "optimal": CanonicalSolverStatus.OPTIMAL,
        "solved": CanonicalSolverStatus.OPTIMAL,
        "optimal_accurate": CanonicalSolverStatus.OPTIMAL,
        "optimal_inaccurate": CanonicalSolverStatus.OPTIMAL_INACCURATE,
        "user_limit_inaccurate": CanonicalSolverStatus.OPTIMAL_INACCURATE,
        "inaccurate": CanonicalSolverStatus.OPTIMAL_INACCURATE,
        "infeasible": CanonicalSolverStatus.INFEASIBLE,
        "infeasible_inaccurate": CanonicalSolverStatus.INFEASIBLE,
        "unbounded": CanonicalSolverStatus.UNBOUNDED,
        "unbounded_inaccurate": CanonicalSolverStatus.UNBOUNDED,
        "iteration_limit": CanonicalSolverStatus.ITERATION_LIMIT,
        "max_iters_reached": CanonicalSolverStatus.ITERATION_LIMIT,
        "max_iter": CanonicalSolverStatus.ITERATION_LIMIT,
        "max_iters": CanonicalSolverStatus.ITERATION_LIMIT,
        "time_limit": CanonicalSolverStatus.TIME_LIMIT,
        "timeout": CanonicalSolverStatus.TIME_LIMIT,
        "numerical_error": CanonicalSolverStatus.NUMERICAL_ERROR,
        "numerical_failure": CanonicalSolverStatus.NUMERICAL_ERROR,
        "num_error": CanonicalSolverStatus.NUMERICAL_ERROR,
        "solver_error": CanonicalSolverStatus.BACKEND_ERROR,
        "backend_error": CanonicalSolverStatus.BACKEND_ERROR,
        "error": CanonicalSolverStatus.BACKEND_ERROR,
        "unknown": CanonicalSolverStatus.UNKNOWN,
    }
    if token in exact:
        return exact[token]

    # Substring heuristics for vendor strings; still fail-closed for unknowns.
    if "infeas" in token:
        return CanonicalSolverStatus.INFEASIBLE
    if "unbound" in token:
        return CanonicalSolverStatus.UNBOUNDED
    if "inaccurate" in token and "optimal" in token:
        return CanonicalSolverStatus.OPTIMAL_INACCURATE
    if token == "optimal" or token.endswith("_optimal") or token.startswith("optimal_"):
        if "inaccurate" in token:
            return CanonicalSolverStatus.OPTIMAL_INACCURATE
        return CanonicalSolverStatus.OPTIMAL
    if "iter" in token and "limit" in token:
        return CanonicalSolverStatus.ITERATION_LIMIT
    if "time" in token and ("limit" in token or "out" in token):
        return CanonicalSolverStatus.TIME_LIMIT
    if "numeric" in token or "nan" in token:
        return CanonicalSolverStatus.NUMERICAL_ERROR
    if "error" in token or "fail" in token:
        return CanonicalSolverStatus.BACKEND_ERROR

    return CanonicalSolverStatus.UNKNOWN


def normalize_cvxpy_status(raw: Any) -> CanonicalSolverStatus:
    """Adapter for ``cvxpy.Problem.status`` strings."""
    token = _as_token(raw)
    # CVXPY uses "optimal_inaccurate", "user_limit", etc.
    if token == "user_limit":
        # Ambiguous: treat as iteration/time budget exhaustion, not success.
        return CanonicalSolverStatus.ITERATION_LIMIT
    return normalize_solver_status(raw, backend="cvxpy")


# Moreau ``SolverStatus`` integer codes (moreau>=0.3). Keep explicit — never
# invent success from unrecognized integers.
_MOREAU_INT_STATUS: dict[int, CanonicalSolverStatus] = {
    0: CanonicalSolverStatus.UNKNOWN,  # Unsolved
    1: CanonicalSolverStatus.OPTIMAL,  # Solved
    2: CanonicalSolverStatus.INFEASIBLE,  # PrimalInfeasible
    3: CanonicalSolverStatus.UNBOUNDED,  # DualInfeasible (primal unbounded)
    4: CanonicalSolverStatus.OPTIMAL_INACCURATE,  # AlmostSolved
    5: CanonicalSolverStatus.INFEASIBLE,  # AlmostPrimalInfeasible
    6: CanonicalSolverStatus.UNBOUNDED,  # AlmostDualInfeasible
    7: CanonicalSolverStatus.ITERATION_LIMIT,  # MaxIterations
    8: CanonicalSolverStatus.TIME_LIMIT,  # MaxTime
    9: CanonicalSolverStatus.NUMERICAL_ERROR,  # NumericalError
    10: CanonicalSolverStatus.NUMERICAL_ERROR,  # InsufficientProgress
    11: CanonicalSolverStatus.BACKEND_ERROR,  # CallbackTerminated
}

_MOREAU_NAME_STATUS: dict[str, CanonicalSolverStatus] = {
    "unsolved": CanonicalSolverStatus.UNKNOWN,
    "solved": CanonicalSolverStatus.OPTIMAL,
    "primalinfeasible": CanonicalSolverStatus.INFEASIBLE,
    "dualinfeasible": CanonicalSolverStatus.UNBOUNDED,
    "almostsolved": CanonicalSolverStatus.OPTIMAL_INACCURATE,
    "almostprimalinfeasible": CanonicalSolverStatus.INFEASIBLE,
    "almostdualinfeasible": CanonicalSolverStatus.UNBOUNDED,
    "maxiterations": CanonicalSolverStatus.ITERATION_LIMIT,
    "maxtime": CanonicalSolverStatus.TIME_LIMIT,
    "numericalerror": CanonicalSolverStatus.NUMERICAL_ERROR,
    "insufficientprogress": CanonicalSolverStatus.NUMERICAL_ERROR,
    "callbackterminated": CanonicalSolverStatus.BACKEND_ERROR,
}


def normalize_moreau_status(raw: Any) -> CanonicalSolverStatus:
    """Adapter for Moreau ``SolverStatus`` ints, enum members, and name tokens.

    Telemetry often stringifies integer codes (``\"1\"`` for Solved). Map those
    explicitly; unrecognized values remain ``UNKNOWN`` (fail-closed).
    """
    if raw is None:
        return CanonicalSolverStatus.UNKNOWN

    # Enum member (moreau.SolverStatus.Solved, etc.).
    name = getattr(raw, "name", None)
    if isinstance(name, str) and name:
        named = _MOREAU_NAME_STATUS.get(_as_token(name).replace("_", ""))
        if named is not None:
            return named
        # Fall through to value when name is unfamiliar.
    value = getattr(raw, "value", None)
    if isinstance(value, int) and not isinstance(raw, bool):
        mapped = _MOREAU_INT_STATUS.get(value)
        if mapped is not None:
            return mapped

    if isinstance(raw, bool):
        return CanonicalSolverStatus.UNKNOWN
    if isinstance(raw, int):
        mapped = _MOREAU_INT_STATUS.get(raw)
        return mapped if mapped is not None else CanonicalSolverStatus.UNKNOWN

    token = _as_token(raw)
    if token.isdigit() or (token.startswith("-") and token[1:].isdigit()):
        mapped = _MOREAU_INT_STATUS.get(int(token))
        return mapped if mapped is not None else CanonicalSolverStatus.UNKNOWN

    compact = token.replace("_", "")
    if compact in _MOREAU_NAME_STATUS:
        return _MOREAU_NAME_STATUS[compact]

    # e.g. "SolverStatus.Solved"
    if "." in token:
        tail = token.rsplit(".", 1)[-1]
        compact_tail = tail.replace("_", "")
        if compact_tail in _MOREAU_NAME_STATUS:
            return _MOREAU_NAME_STATUS[compact_tail]

    return normalize_solver_status(raw, backend="moreau")

from __future__ import annotations

import importlib
from types import ModuleType

from conicshield._optional import OptionalDependencyError

SOLVER_INSTALL_HINT = (
    'Install a profile from packaging/install_matrix.json, for example: '
    'pip install -e ".[solver-public]" -c packaging/constraints/solver-public.txt '
    '(credential-free), or pip install -e ".[solver-moreau-cpu]" '
    '--extra-index-url "<vendor-index>" for Linux/WSL Moreau. '
    "Place your Moreau license in ~/.moreau/key (or set MOREAU_LICENSE_KEY). "
    "Do not assume default-index pip install moreau is the governed package. "
    "See docs/MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md and "
    "https://docs.moreau.so/installation.html"
)


class MissingSolverExtraError(OptionalDependencyError):
    """Raised when an optional component (cvxpy, moreau, …) is missing for a code path."""

    def __init__(
        self,
        *,
        distribution_name: str,
        feature: str,
        install_hint: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        self.distribution_name = distribution_name
        self.feature = feature
        hint = install_hint or SOLVER_INSTALL_HINT
        msg = f"Optional dependency '{distribution_name}' is required for {feature}. {hint}"
        super().__init__(msg)
        if cause is not None:
            self.__cause__ = cause


def require_solver_module(distribution_name: str, feature: str) -> ModuleType:
    try:
        return importlib.import_module(distribution_name)
    except ImportError as exc:
        raise MissingSolverExtraError(
            distribution_name=distribution_name,
            feature=feature,
            cause=exc,
        ) from exc

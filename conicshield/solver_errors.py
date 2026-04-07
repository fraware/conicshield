from __future__ import annotations

import importlib
from types import ModuleType

from conicshield._optional import OptionalDependencyError

SOLVER_INSTALL_HINT = (
    'Install solver extras, for example: pip install -e ".[solver,dev]" '
    '--extra-index-url "https://<GEMFURY_TOKEN>:@pypi.fury.io/optimalintellect/". '
    "Place your Moreau license in ~/.moreau/key (or set MOREAU_LICENSE_KEY). "
    "See https://docs.moreau.so/installation.html"
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

from __future__ import annotations

import importlib
from types import ModuleType


class OptionalDependencyError(ImportError):
    pass


def require_module(name: str, purpose: str) -> ModuleType:
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        raise OptionalDependencyError(
            f"Optional dependency '{name}' is required for {purpose}. "
            f"Install the solver extras, for example: pip install -e '.[solver]'."
        ) from exc

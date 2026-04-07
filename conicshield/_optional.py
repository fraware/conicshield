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
            "Install solver extras (see README / MAINTAINER_RUNBOOK), e.g. "
            "pip install -e '.[solver,dev]' with the GemFury index and a Moreau license."
        ) from exc

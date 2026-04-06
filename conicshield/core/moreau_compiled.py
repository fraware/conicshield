from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from conicshield._optional import OptionalDependencyError, require_module
from conicshield.core.result import ProjectionResult
from conicshield.specs.schema import SafetySpec


@dataclass(slots=True)
class NativeMoreauCompiledOptions:
    device: str = "auto"
    auto_tune: bool = False
    enable_grad: bool = False
    max_iter: int = 200
    time_limit: float = float("inf")
    verbose: bool = False
    active_tol: float = 1e-6
    persist_warm_start: bool = True
    policy_weight: float = 1.0
    reference_weight: float = 0.0


class NativeMoreauCompiledProjector:
    """Native Moreau compiled path.

    The implementation is intentionally lazy-imported so the governance stack
    remains usable without solver dependencies.
    """

    def __init__(
        self,
        *,
        spec: SafetySpec,
        options: NativeMoreauCompiledOptions | None = None,
    ) -> None:
        self.spec = spec
        self.options = options or NativeMoreauCompiledOptions()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        require_module("moreau", "native Moreau compiled projector")
        raise OptionalDependencyError(
            "The native Moreau compiled projector is provided as an integration seam. "
            "Complete the structure-specific compilation for your exact spec family before use."
        )

    def project(
        self,
        proposed_action: np.ndarray,
        previous_action: np.ndarray | None = None,
        *,
        reference_action: np.ndarray | None = None,
        policy_weight: float = 1.0,
        reference_weight: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> ProjectionResult:
        self._ensure_initialized()
        raise RuntimeError("Unreachable")

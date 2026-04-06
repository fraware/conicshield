from __future__ import annotations

from enum import Enum

from conicshield.core.interfaces import ProjectorProtocol
from conicshield.core.moreau_compiled import (
    NativeMoreauCompiledOptions,
    NativeMoreauCompiledProjector,
)
from conicshield.specs.compiler import CVXPYMoreauProjector, SolverOptions
from conicshield.specs.schema import SafetySpec


class Backend(str, Enum):
    CVXPY_MOREAU = "cvxpy_moreau"
    NATIVE_MOREAU = "native_moreau"


def create_projector(
    *,
    spec: SafetySpec,
    backend: Backend = Backend.CVXPY_MOREAU,
    cvxpy_options: SolverOptions | None = None,
    native_options: NativeMoreauCompiledOptions | None = None,
) -> ProjectorProtocol:
    if backend == Backend.CVXPY_MOREAU:
        return CVXPYMoreauProjector(spec=spec, options=cvxpy_options)
    if backend == Backend.NATIVE_MOREAU:
        return NativeMoreauCompiledProjector(spec=spec, options=native_options)
    raise ValueError(f"Unsupported backend: {backend}")

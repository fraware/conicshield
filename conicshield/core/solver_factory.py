from __future__ import annotations

from enum import StrEnum

from conicshield.core.interfaces import ProjectorProtocol
from conicshield.core.moreau_batched import NativeMoreauCompiledBatchProjector
from conicshield.core.moreau_compiled import (
    NativeMoreauCompiledOptions,
    NativeMoreauCompiledProjector,
)
from conicshield.specs.compiler import CVXPYMoreauProjector, SolverOptions
from conicshield.specs.schema import SafetySpec


class Backend(StrEnum):
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


def create_batch_projector(
    *,
    spec: SafetySpec,
    backend: Backend = Backend.NATIVE_MOREAU,
    native_options: NativeMoreauCompiledOptions | None = None,
) -> NativeMoreauCompiledBatchProjector:
    """Return the batched native projector (one ``CompiledSolver.solve(qs, bs)`` per ``project_batch`` call).

    CVXPY reference batching is not exposed here; use ``create_projector`` for the reference path.
    """
    if backend != Backend.NATIVE_MOREAU:
        raise ValueError(
            f"Batched compiled projection is only implemented for {Backend.NATIVE_MOREAU!s}, got {backend!s}"
        )
    return NativeMoreauCompiledBatchProjector(spec=spec, options=native_options)

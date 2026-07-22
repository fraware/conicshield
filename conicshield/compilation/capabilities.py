"""Compilation / solver capability flags (default off until gates pass)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompilationCapabilities:
    """Optional solver features gated until parity and benchmark gates pass.

    These flags exist so callers can probe and tests can assert defaults stay
    off. Enabling them without passing gates is unsupported.
    """

    #: Direct-variable cone encodings (investigation only; not production default).
    enable_direct_variable_cones: bool = False
    #: CPU algorithm selection / auto-tune beyond Moreau Settings.auto_tune.
    enable_cpu_algorithm_autotune: bool = False


DEFAULT_COMPILATION_CAPABILITIES = CompilationCapabilities()


def resolve_capabilities(
    overrides: CompilationCapabilities | None = None,
) -> CompilationCapabilities:
    """Return effective capabilities (defaults all off when ``overrides`` is None)."""
    return overrides if overrides is not None else DEFAULT_COMPILATION_CAPABILITIES

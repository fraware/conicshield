"""Typed specification and objective-weight errors for Track-1 S1."""

from __future__ import annotations


class SpecificationError(ValueError):
    """Base class for invalid or contradictory safety specifications."""


class DimensionMismatchError(SpecificationError):
    """A constraint vector length does not match ``SafetySpec.action_dim``."""


class DuplicateConstraintError(SpecificationError):
    """Multiple singleton constraints of the same kind were declared."""


class ContradictoryConstraintError(SpecificationError):
    """Declared constraints are mutually infeasible under detectable static rules."""


class NoAdmissibleActionError(SpecificationError):
    """No action is admissible and the configured fail-safe policy rejects the case."""


class MissingFailSafePolicyError(SpecificationError):
    """No action is admissible and the caller did not select an explicit fail-safe policy."""


class InvalidObjectiveWeightError(SpecificationError):
    """Objective weights violate finite / nonnegativity / positive-sum requirements."""

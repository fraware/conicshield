"""Safety specification schema with strict dimension, duplicate, and contradiction checks.

``BoxConstraint`` semantics
---------------------------
For each action index ``i`` with declared finite bounds:

* lower bound: ``x_i >= lower_i``
* upper bound: ``x_i <= upper_i``

Bounds must be finite (no ``±inf`` / NaN). Absence of a ``BoxConstraint`` in a
shield QP is interpreted by the canonical IR as the unit box ``[0, 1]^n``
(probability-simplex family default). When a ``BoxConstraint`` is present, both
CVXPY and native compilers must encode exactly those declared bounds — never a
stronger implicit nonnegativity.
"""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from conicshield.specs.errors import (
    ContradictoryConstraintError,
    DimensionMismatchError,
    DuplicateConstraintError,
    MissingFailSafePolicyError,
    NoAdmissibleActionError,
)


class ConstraintKind(StrEnum):
    BOX = "box"
    RATE = "rate"
    PROGRESS = "progress"
    CLEARANCE = "clearance"
    TURN_FEASIBILITY = "turn_feasibility"
    SIMPLEX = "simplex"


class FailSafePolicy(StrEnum):
    """Caller-selected fail-safe when the admissible set is empty or release fails.

    * ``REJECT`` — fail closed (construction-time for empty admissible sets;
      runtime release pipeline raises rather than synthesizing an action).
    * ``UNIFORM_ADMISSIBLE`` — synthesize a uniform-mass action on allowed
      coordinates (still must pass residual verification before release).
    * ``CLAMPED_PROPOSED`` — clamp/repair the proposed action onto the
      admissible set (still must pass residual verification before release).
    """

    REJECT = "reject"
    UNIFORM_ADMISSIBLE = "uniform_admissible"
    CLAMPED_PROPOSED = "clamped_proposed"


# Singleton constraint kinds: at most one of each may appear in a SafetySpec.
_SINGLETON_KINDS = frozenset(
    {
        ConstraintKind.BOX,
        ConstraintKind.RATE,
        ConstraintKind.SIMPLEX,
        ConstraintKind.TURN_FEASIBILITY,
        ConstraintKind.PROGRESS,
        ConstraintKind.CLEARANCE,
    }
)


def _require_finite(values: list[float], *, label: str) -> None:
    for i, v in enumerate(values):
        if not math.isfinite(v):
            raise ValueError(f"{label}[{i}] must be finite (got {v!r})")


class BoxConstraint(BaseModel):
    """Axis-aligned box: ``lower_i <= x_i <= upper_i`` for each coordinate."""

    kind: Literal[ConstraintKind.BOX] = ConstraintKind.BOX
    lower: list[float]
    upper: list[float]

    @field_validator("lower")
    @classmethod
    def validate_lower_finite(cls, lower: list[float]) -> list[float]:
        _require_finite(lower, label="lower")
        return lower

    @field_validator("upper")
    @classmethod
    def validate_bounds(cls, upper: list[float], info: ValidationInfo) -> list[float]:
        _require_finite(upper, label="upper")
        lower = info.data.get("lower")
        if lower is None:
            return upper
        if len(lower) != len(upper):
            raise ValueError("lower and upper must have identical length")
        for lo, hi in zip(lower, upper, strict=True):
            if lo > hi:
                raise ValueError("each lower bound must be <= upper bound")
        return upper


class RateConstraint(BaseModel):
    kind: Literal[ConstraintKind.RATE] = ConstraintKind.RATE
    max_delta: list[float]

    @field_validator("max_delta")
    @classmethod
    def validate_nonnegative_finite_or_inf(cls, max_delta: list[float]) -> list[float]:
        for i, x in enumerate(max_delta):
            if math.isnan(x) or x < 0.0:
                raise ValueError(f"max_delta[{i}] must be nonnegative and non-NaN (got {x!r})")
            # +inf is allowed ("no rate limit" on that coordinate).
            if math.isinf(x) and x < 0.0:
                raise ValueError(f"max_delta[{i}] must not be -inf")
        return max_delta


class ProgressConstraint(BaseModel):
    kind: Literal[ConstraintKind.PROGRESS] = ConstraintKind.PROGRESS
    min_progress: float = Field(ge=0.0)


class ClearanceConstraint(BaseModel):
    kind: Literal[ConstraintKind.CLEARANCE] = ConstraintKind.CLEARANCE
    min_clearance: float = Field(gt=0.0)


class TurnFeasibilityConstraint(BaseModel):
    """Admissible action indices. Empty list is allowed only with an explicit fail-safe."""

    kind: Literal[ConstraintKind.TURN_FEASIBILITY] = ConstraintKind.TURN_FEASIBILITY
    allowed_actions: list[int]

    @field_validator("allowed_actions")
    @classmethod
    def validate_actions(cls, actions: list[int]) -> list[int]:
        if len(set(actions)) != len(actions):
            raise ValueError("allowed_actions must not contain duplicates")
        if any(a < 0 for a in actions):
            raise ValueError("actions must be nonnegative integers")
        return actions


class SimplexConstraint(BaseModel):
    kind: Literal[ConstraintKind.SIMPLEX] = ConstraintKind.SIMPLEX
    total: float = Field(default=1.0, gt=0.0)


Constraint = (
    BoxConstraint
    | RateConstraint
    | ProgressConstraint
    | ClearanceConstraint
    | TurnFeasibilityConstraint
    | SimplexConstraint
)


class SafetySpec(BaseModel):
    spec_id: str
    version: str = "0.1.0"
    action_dim: int = Field(gt=0)
    slack_weight: float = Field(default=10.0, gt=0.0)
    constraints: list[Constraint]
    fail_safe_policy: FailSafePolicy | None = None

    @field_validator("constraints")
    @classmethod
    def validate_non_empty(cls, constraints: list[Constraint]) -> list[Constraint]:
        if not constraints:
            raise ValueError("at least one constraint is required")
        return constraints

    @model_validator(mode="after")
    def validate_model_consistency(self) -> Self:
        n = self.action_dim
        seen: dict[ConstraintKind, Constraint] = {}
        simplex: SimplexConstraint | None = None
        box: BoxConstraint | None = None
        turn: TurnFeasibilityConstraint | None = None
        rate: RateConstraint | None = None

        for c in self.constraints:
            kind = c.kind if isinstance(c.kind, ConstraintKind) else ConstraintKind(str(c.kind))
            if kind in _SINGLETON_KINDS:
                if kind in seen:
                    raise DuplicateConstraintError(
                        f"duplicate {kind.value} constraint is not allowed; "
                        "declare at most one singleton constraint of each kind"
                    )
                seen[kind] = c

            if isinstance(c, BoxConstraint):
                if len(c.lower) != n or len(c.upper) != n:
                    raise DimensionMismatchError(
                        f"BoxConstraint lengths (lower={len(c.lower)}, upper={len(c.upper)}) must equal action_dim={n}"
                    )
                box = c
            elif isinstance(c, RateConstraint):
                if len(c.max_delta) != n:
                    raise DimensionMismatchError(
                        f"RateConstraint.max_delta length {len(c.max_delta)} must equal action_dim={n}"
                    )
                rate = c
            elif isinstance(c, SimplexConstraint):
                simplex = c
            elif isinstance(c, TurnFeasibilityConstraint):
                for idx in c.allowed_actions:
                    if idx >= n:
                        raise DimensionMismatchError(f"allowed_actions index {idx} is out of range for action_dim={n}")
                turn = c

        # Empty admissible set requires an explicit fail-safe; REJECT fails closed.
        # Checked before simplex/box sum rules so the fail-safe requirement is visible.
        if turn is not None and not turn.allowed_actions:
            self._enforce_empty_admissible_fail_safe()

        # Detectable contradictions involving simplex + box (+ optional turn mask).
        if simplex is not None and box is not None:
            if turn is not None and turn.allowed_actions:
                mask = [False] * n
                for idx in turn.allowed_actions:
                    mask[idx] = True
            elif turn is not None and not turn.allowed_actions:
                mask = [False] * n
            else:
                mask = [True] * n

            sum_lower = 0.0
            sum_upper = 0.0
            for i in range(n):
                if not mask[i]:
                    # Prohibited actions must be exactly zero; treat as fixed at 0.
                    if box.lower[i] > 0.0 or box.upper[i] < 0.0:
                        raise ContradictoryConstraintError(
                            f"prohibited action {i} has box bounds that exclude 0 "
                            f"(lower={box.lower[i]}, upper={box.upper[i]})"
                        )
                    continue
                sum_lower += box.lower[i]
                sum_upper += box.upper[i]

            total = float(simplex.total)
            if sum_lower > total + 1e-12:
                raise ContradictoryConstraintError(
                    f"sum of lower bounds on admissible actions ({sum_lower}) exceeds simplex total ({total})"
                )
            if sum_upper < total - 1e-12:
                raise ContradictoryConstraintError(
                    f"sum of upper bounds on admissible actions ({sum_upper}) is below simplex total ({total})"
                )

        # Rate is retained for IR; no static contradiction beyond dimension checks.
        _ = rate
        return self

    def _enforce_empty_admissible_fail_safe(self) -> None:
        if self.fail_safe_policy is None:
            raise MissingFailSafePolicyError(
                "no action is admissible (empty TurnFeasibilityConstraint.allowed_actions); "
                "set SafetySpec.fail_safe_policy explicitly "
                f"(e.g. FailSafePolicy.{FailSafePolicy.REJECT.name})"
            )
        # Empty admissible set cannot be recovered by any fail-safe synthesizer.
        raise NoAdmissibleActionError(
            "no action is admissible; fail-safe policies cannot synthesize an "
            f"action from an empty allowed set (policy={self.fail_safe_policy!r})"
        )

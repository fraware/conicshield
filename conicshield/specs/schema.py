from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class ConstraintKind(str, Enum):
    BOX = "box"
    RATE = "rate"
    PROGRESS = "progress"
    CLEARANCE = "clearance"
    TURN_FEASIBILITY = "turn_feasibility"
    SIMPLEX = "simplex"


class BoxConstraint(BaseModel):
    kind: Literal[ConstraintKind.BOX] = ConstraintKind.BOX
    lower: list[float]
    upper: list[float]

    @field_validator("upper")
    @classmethod
    def validate_bounds(cls, upper: list[float], info: ValidationInfo) -> list[float]:
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
    def validate_positive(cls, max_delta: list[float]) -> list[float]:
        if any(x < 0 for x in max_delta):
            raise ValueError("max_delta must be elementwise nonnegative")
        return max_delta


class ProgressConstraint(BaseModel):
    kind: Literal[ConstraintKind.PROGRESS] = ConstraintKind.PROGRESS
    min_progress: float = Field(ge=0.0)


class ClearanceConstraint(BaseModel):
    kind: Literal[ConstraintKind.CLEARANCE] = ConstraintKind.CLEARANCE
    min_clearance: float = Field(gt=0.0)


class TurnFeasibilityConstraint(BaseModel):
    kind: Literal[ConstraintKind.TURN_FEASIBILITY] = ConstraintKind.TURN_FEASIBILITY
    allowed_actions: list[int]

    @field_validator("allowed_actions")
    @classmethod
    def validate_actions(cls, actions: list[int]) -> list[int]:
        if not actions:
            raise ValueError("allowed_actions must be non-empty")
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

    @field_validator("constraints")
    @classmethod
    def validate_non_empty(cls, constraints: list[Constraint]) -> list[Constraint]:
        if not constraints:
            raise ValueError("at least one constraint is required")
        return constraints

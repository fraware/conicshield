from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TransitionCandidateModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    destination_address: str
    destination_coords: tuple[float, float]
    first_instruction: str
    action_class: str
    duration_sec: float | None = None
    distance_m: float | None = None


class ShieldContextModel(BaseModel):
    """Pydantic mirror of the minimum contract in docs/INTER_SIM_RL_INTEGRATION.md."""

    model_config = ConfigDict(extra="allow")

    allowed_actions: list[str]
    blocked_actions: list[str]
    action_upper_bounds: dict[str, float]
    rule_choice: str
    previous_instruction: str | None
    hazard_score: float = Field(ge=0.0, le=1.0)
    current_heading_deg: float | None = None
    branch_bearings_deg: list[float] | None = None
    current_location: list[float] | None = None
    current_direction: list[float] | None = None
    current_address: str | None = None
    transition_candidates: list[TransitionCandidateModel] | None = None

    @classmethod
    def from_mapping(cls, context: dict[str, Any]) -> ShieldContextModel:
        raw = dict(context)
        caps = raw.get("action_upper_bounds")
        if isinstance(caps, dict):
            raw["action_upper_bounds"] = {str(k): float(v) for k, v in caps.items()}
        else:
            raw["action_upper_bounds"] = {}
        tc = raw.get("transition_candidates")
        if isinstance(tc, list):
            normalized: list[dict[str, Any]] = []
            for item in tc:
                if not isinstance(item, dict):
                    continue
                row = dict(item)
                dc = row.get("destination_coords")
                if isinstance(dc, list | tuple) and len(dc) >= 2:
                    row["destination_coords"] = (float(dc[0]), float(dc[1]))
                normalized.append(row)
            raw["transition_candidates"] = normalized
        return cls.model_validate(raw)

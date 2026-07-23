"""State-level safety response map export from frontier sweeps (R3 deliverable depth)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.experimental.frontiers.sweeps import (
    BATCH_EMULATION_SEQUENTIAL,
    PUBLICATION_GRADE_WATERMARK,
    FrontierPoint,
    ParetoFrontier,
    probe_track1_hetero_batch_attestation,
    run_frontier_sweep,
)
from conicshield.specs.schema import SafetySpec

RESPONSE_MAP_SCHEMA_ID = "research.safety_response_map.v0"

# R3 required output fields for a complete (still non-publication-grade) response map.
R3_REQUIRED_CELL_FIELDS: tuple[str, ...] = (
    "state_id",
    "parameters",
    "selected_action",
    "intervention_magnitude",
    "safety_margin",
    "feasibility_margin",
    "active_set",
    "regime_tag",
    "policy_fidelity",
    "numerical_confidence",
)

R3_REQUIRED_MAP_FIELDS: tuple[str, ...] = (
    "schema_id",
    "cells",
    "regime_counts",
    "batch_emulation",
    "publication_grade",
    "watermark",
    "r3_completeness",
)


def _regime_tag(point: FrontierPoint) -> str:
    """Tag frontier points into coarse response regimes."""

    if not np.isfinite(point.feasibility_margin) or point.feasibility_margin < 0.0:
        return "infeasible_or_negative_margin"
    if point.intervention_magnitude < 1e-8:
        return "no_intervention"
    if point.intervention_magnitude < 0.05:
        return "light_intervention"
    active_joined = " ".join(point.active_set).lower()
    if point.active_set and "rate" in active_joined:
        return "rate_limited_intervention"
    if "bound" in active_joined or "simplex" in active_joined:
        return "bound_active_intervention"
    if point.safety_margin < 0.05:
        return "near_safety_boundary"
    if point.numerical_confidence < 0.5:
        return "low_confidence_intervention"
    return "active_intervention"


@dataclass(slots=True)
class SafetyResponseCell:
    state_id: str
    parameters: dict[str, float]
    selected_action: list[float]
    intervention_magnitude: float
    safety_margin: float
    feasibility_margin: float
    active_set: tuple[str, ...]
    regime_tag: str
    policy_fidelity: float
    numerical_confidence: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "parameters": dict(self.parameters),
            "selected_action": list(self.selected_action),
            "intervention_magnitude": self.intervention_magnitude,
            "safety_margin": self.safety_margin,
            "feasibility_margin": self.feasibility_margin,
            "active_set": list(self.active_set),
            "regime_tag": self.regime_tag,
            "policy_fidelity": self.policy_fidelity,
            "numerical_confidence": self.numerical_confidence,
        }


@dataclass(slots=True)
class SafetyResponseMap:
    schema_id: str = RESPONSE_MAP_SCHEMA_ID
    cells: list[SafetyResponseCell] = field(default_factory=list)
    regime_counts: dict[str, int] = field(default_factory=dict)
    batch_emulation: str = BATCH_EMULATION_SEQUENTIAL
    publication_grade: bool = False
    watermark: str = PUBLICATION_GRADE_WATERMARK
    r3_completeness: dict[str, bool] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "n_cells": len(self.cells),
            "cells": [c.as_dict() for c in self.cells],
            "regime_counts": dict(self.regime_counts),
            "batch_emulation": self.batch_emulation,
            "publication_grade": self.publication_grade,
            "watermark": self.watermark,
            "r3_completeness": dict(self.r3_completeness),
            "notes": list(self.notes),
        }


def assess_r3_completeness(response_map: SafetyResponseMap) -> dict[str, bool]:
    """Check map against R3 required outputs (still watermarked / non-publication)."""

    d = response_map.as_dict()
    cell_ok = True
    for cell in response_map.cells:
        cd = cell.as_dict()
        if any(f not in cd for f in R3_REQUIRED_CELL_FIELDS):
            cell_ok = False
            break
        if not cd.get("regime_tag"):
            cell_ok = False
            break
    return {
        "has_cells": len(response_map.cells) > 0,
        "has_regime_counts": bool(response_map.regime_counts),
        "has_batch_emulation_watermark": response_map.batch_emulation == BATCH_EMULATION_SEQUENTIAL,
        "publication_grade_false": response_map.publication_grade is False,
        "watermark_present": bool(response_map.watermark),
        "required_map_fields": all(f in d for f in R3_REQUIRED_MAP_FIELDS if f != "r3_completeness"),
        "required_cell_fields": cell_ok,
        "regime_tags_nonempty": all(bool(c.regime_tag) for c in response_map.cells),
    }


def export_safety_response_map(
    frontier: ParetoFrontier | None = None,
    *,
    spec: SafetySpec | None = None,
    proposed_action: np.ndarray | None = None,
    previous_action: np.ndarray | None = None,
    reference_action: np.ndarray | None = None,
    grid: dict[str, list[float]] | None = None,
    backend_id: str = "cvxpy_clarabel",
) -> SafetyResponseMap:
    """Export state-level safety response map with regime tags from a frontier."""

    att = probe_track1_hetero_batch_attestation()
    if frontier is None:
        if spec is None or proposed_action is None or previous_action is None or reference_action is None:
            raise ValueError("spec and actions required when frontier is not provided")
        frontier = run_frontier_sweep(
            spec=spec,
            proposed_action=proposed_action,
            previous_action=previous_action,
            reference_action=reference_action,
            grid=grid
            or {
                "policy_weight": [1.0, 2.0],
                "reference_weight": [0.0, 0.5],
                "rate_limit": [0.5, 1.0],
                "hazard_multiplier": [1.0],
                "geometry_prior_weight": [0.0],
                "bound_margins": [0.0],
                "robustness_margins": [0.0],
                "fallback_thresholds": [0.5],
            },
            backend_id=backend_id,
        )

    cells: list[SafetyResponseCell] = []
    counts: dict[str, int] = {}
    for i, p in enumerate(frontier.points):
        tag = _regime_tag(p)
        counts[tag] = counts.get(tag, 0) + 1
        cells.append(
            SafetyResponseCell(
                state_id=f"frontier_{i:04d}",
                parameters=dict(p.parameters),
                selected_action=list(p.selected_action),
                intervention_magnitude=float(p.intervention_magnitude),
                safety_margin=float(p.safety_margin),
                feasibility_margin=float(p.feasibility_margin),
                active_set=tuple(p.active_set),
                regime_tag=tag,
                policy_fidelity=float(p.policy_fidelity),
                numerical_confidence=float(p.numerical_confidence),
            )
        )

    response = SafetyResponseMap(
        cells=cells,
        regime_counts=counts,
        batch_emulation=att.batch_emulation,
        publication_grade=False,
        watermark=PUBLICATION_GRADE_WATERMARK,
        notes=[
            "State-level map derived from sequential research frontier sweeps.",
            "Not publication-grade until Track 1 S4 hetero-batch attestation is positive.",
            f"attestation_note={att.attestation_note}",
        ],
    )
    response.r3_completeness = assess_r3_completeness(response)
    if not all(response.r3_completeness.values()):
        response.notes.append(f"r3_completeness gaps: {[k for k, v in response.r3_completeness.items() if not v]}")
    return response


def write_safety_response_map(path: Path, response_map: SafetyResponseMap) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(response_map.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path

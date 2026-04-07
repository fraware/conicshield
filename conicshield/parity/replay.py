from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(slots=True)
class ParityStepResult:
    episode_id: str
    step: int
    reference_action: str
    candidate_action: str
    action_match: bool
    proposed_linf: float
    corrected_linf: float
    corrected_l2: float
    objective_abs_diff: float | None
    intervention_norm_abs_diff: float | None
    active_constraints_match: bool
    solver_status_reference: str | None
    solver_status_candidate: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "step": self.step,
            "reference_action": self.reference_action,
            "candidate_action": self.candidate_action,
            "action_match": self.action_match,
            "proposed_linf": self.proposed_linf,
            "corrected_linf": self.corrected_linf,
            "corrected_l2": self.corrected_l2,
            "objective_abs_diff": self.objective_abs_diff,
            "intervention_norm_abs_diff": self.intervention_norm_abs_diff,
            "active_constraints_match": self.active_constraints_match,
            "solver_status_reference": self.solver_status_reference,
            "solver_status_candidate": self.solver_status_candidate,
        }


@dataclass(slots=True)
class ParitySummary:
    total_steps: int
    action_match_rate: float
    max_corrected_linf: float
    p95_corrected_linf: float
    max_corrected_l2: float
    p95_corrected_l2: float
    active_constraints_match_rate: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_steps": self.total_steps,
            "action_match_rate": self.action_match_rate,
            "max_corrected_linf": self.max_corrected_linf,
            "p95_corrected_linf": self.p95_corrected_linf,
            "max_corrected_l2": self.max_corrected_l2,
            "p95_corrected_l2": self.p95_corrected_l2,
            "active_constraints_match_rate": self.active_constraints_match_rate,
        }


def _iter_jsonl(path: str | Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _safe_percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    return float(np.percentile(np.asarray(values, dtype=float), q))


def compare_against_reference(
    *, episodes_jsonl: str | Path, candidate_shield: Any, reference_arm_label: str = "shielded-rules-plus-geometry"
) -> tuple[list[ParityStepResult], ParitySummary]:
    records = _iter_jsonl(episodes_jsonl)
    step_results: list[ParityStepResult] = []

    for ep in records:
        if ep["arm_label"] != reference_arm_label:
            continue

        candidate_shield.reset_episode()
        current_episode_id = ep["episode_id"]

        for step in ep["steps"]:
            meta = dict(step.get("metadata", {}))
            ctx = meta.get("shield_context_snapshot")
            if ctx is None:
                raise ValueError("episodes.jsonl does not contain metadata.shield_context_snapshot")

            raw_q_values = step.get("raw_q_values")
            if raw_q_values is None:
                raise ValueError("episodes.jsonl does not contain raw_q_values")

            action_space = meta.get("canonical_action_space")
            if action_space is None:
                raise ValueError("episodes.jsonl does not contain metadata.canonical_action_space")

            decision = candidate_shield.choose_action(
                q_values=np.asarray(raw_q_values, dtype=float),
                action_space=list(action_space),
                context=ctx,
            )

            ref_proposed = np.asarray(step.get("proposed_distribution"), dtype=float)
            ref_corrected = np.asarray(step.get("corrected_distribution"), dtype=float)
            cand_proposed = np.asarray(decision.proposed_distribution, dtype=float)
            cand_corrected = np.asarray(decision.corrected_distribution, dtype=float)

            obj_ref = step.get("objective_value")
            obj_cand = decision.projection.objective_value
            intervention_ref = step.get("intervention_norm")
            intervention_cand = decision.projection.intervention_norm

            step_results.append(
                ParityStepResult(
                    episode_id=current_episode_id,
                    step=int(step["step"]),
                    reference_action=str(step["chosen_action"]),
                    candidate_action=str(decision.action_name),
                    action_match=(str(step["chosen_action"]) == str(decision.action_name)),
                    proposed_linf=float(np.max(np.abs(ref_proposed - cand_proposed))),
                    corrected_linf=float(np.max(np.abs(ref_corrected - cand_corrected))),
                    corrected_l2=float(np.linalg.norm(ref_corrected - cand_corrected)),
                    objective_abs_diff=(
                        abs(float(obj_ref) - float(obj_cand)) if obj_ref is not None and obj_cand is not None else None
                    ),
                    intervention_norm_abs_diff=(
                        abs(float(intervention_ref) - float(intervention_cand))
                        if intervention_ref is not None and intervention_cand is not None
                        else None
                    ),
                    active_constraints_match=(
                        sorted(step.get("active_constraints", [])) == sorted(decision.projection.active_constraints)
                    ),
                    solver_status_reference=step.get("solver_status"),
                    solver_status_candidate=decision.projection.solver_status,
                )
            )

    if not step_results:
        raise ValueError("No reference-arm records found in episodes.jsonl")

    corrected_linf = [r.corrected_linf for r in step_results]
    corrected_l2 = [r.corrected_l2 for r in step_results]
    summary = ParitySummary(
        total_steps=len(step_results),
        action_match_rate=sum(int(r.action_match) for r in step_results) / len(step_results),
        max_corrected_linf=max(corrected_linf),
        p95_corrected_linf=_safe_percentile(corrected_linf, 95),
        max_corrected_l2=max(corrected_l2),
        p95_corrected_l2=_safe_percentile(corrected_l2, 95),
        active_constraints_match_rate=(sum(int(r.active_constraints_match) for r in step_results) / len(step_results)),
    )
    return step_results, summary

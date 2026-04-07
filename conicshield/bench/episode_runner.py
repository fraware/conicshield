from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import numpy as np

from conicshield.adapters.inter_sim_rl.policy import InterSimKerasDQNPolicy
from conicshield.adapters.inter_sim_rl.shield import InterSimConicShield


@dataclass(slots=True)
class StepRecord:
    step: int
    current_address: str
    current_location: tuple[float, float] | None
    previous_instruction: str | None
    available_actions: list[str]
    chosen_action: str
    reward: float

    intervened: bool = False
    intervention_norm: float | None = None
    objective_value: float | None = None
    raw_q_values: list[float] | None = None
    proposed_distribution: list[float] | None = None
    corrected_distribution: list[float] | None = None
    active_constraints: list[str] = field(default_factory=list)

    matched_action: bool = False
    fallback_used: bool = False
    selected_action_class: str | None = None
    selected_destination_address: str | None = None
    selected_duration_sec: float | None = None
    selected_distance_m: float | None = None

    solver_status: str | None = None
    iterations: int | None = None
    solve_time_sec: float | None = None
    setup_time_sec: float | None = None
    construction_time_sec: float | None = None
    device: str | None = None
    warm_started: bool | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "current_address": self.current_address,
            "current_location": list(self.current_location) if self.current_location is not None else None,
            "previous_instruction": self.previous_instruction,
            "available_actions": list(self.available_actions),
            "chosen_action": self.chosen_action,
            "reward": float(self.reward),
            "intervened": bool(self.intervened),
            "intervention_norm": self.intervention_norm,
            "objective_value": self.objective_value,
            "raw_q_values": self.raw_q_values,
            "proposed_distribution": self.proposed_distribution,
            "corrected_distribution": self.corrected_distribution,
            "active_constraints": list(self.active_constraints),
            "matched_action": bool(self.matched_action),
            "fallback_used": bool(self.fallback_used),
            "selected_action_class": self.selected_action_class,
            "selected_destination_address": self.selected_destination_address,
            "selected_duration_sec": self.selected_duration_sec,
            "selected_distance_m": self.selected_distance_m,
            "solver_status": self.solver_status,
            "iterations": self.iterations,
            "solve_time_sec": self.solve_time_sec,
            "setup_time_sec": self.setup_time_sec,
            "construction_time_sec": self.construction_time_sec,
            "device": self.device,
            "warm_started": self.warm_started,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class EpisodeRecord:
    episode_id: str
    arm_label: str
    backend: str
    root_address: str
    rule_choice: str
    bank_id: str
    policy_id: str
    policy_checkpoint: str | None
    seed: int | None

    started_at_utc: str
    finished_at_utc: str | None = None

    num_steps: int = 0
    total_reward: float = 0.0
    num_interventions: int = 0
    rule_violations: int = 0
    matched_action_steps: int = 0
    fallback_steps: int = 0
    terminated_reason: str | None = None

    steps: list[StepRecord] = field(default_factory=list)

    def finalize(self) -> None:
        self.num_steps = len(self.steps)
        self.total_reward = float(sum(float(s.reward) for s in self.steps))
        self.num_interventions = sum(int(s.intervened) for s in self.steps)
        self.rule_violations = self._count_rule_violations()
        self.matched_action_steps = sum(int(s.matched_action) for s in self.steps)
        self.fallback_steps = sum(int(s.fallback_used) for s in self.steps)
        self.finished_at_utc = datetime.now(UTC).isoformat()

    def _count_rule_violations(self) -> int:
        violations = 0
        for s in self.steps:
            prev = s.previous_instruction
            if prev is None:
                continue

            prev_l = prev.lower()
            if self.rule_choice == "right":
                if "right" in prev_l and s.chosen_action != "turn_right":
                    violations += 1
            elif self.rule_choice == "left":
                if "left" in prev_l and s.chosen_action != "turn_left":
                    violations += 1
            elif self.rule_choice == "alternate" and (
                "left" in prev_l
                and s.chosen_action != "turn_right"
                or "right" in prev_l
                and s.chosen_action != "turn_left"
            ):
                violations += 1
        return violations

    def as_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "arm_label": self.arm_label,
            "backend": self.backend,
            "root_address": self.root_address,
            "rule_choice": self.rule_choice,
            "bank_id": self.bank_id,
            "policy_id": self.policy_id,
            "policy_checkpoint": self.policy_checkpoint,
            "seed": self.seed,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
            "num_steps": self.num_steps,
            "total_reward": self.total_reward,
            "num_interventions": self.num_interventions,
            "rule_violations": self.rule_violations,
            "matched_action_steps": self.matched_action_steps,
            "fallback_steps": self.fallback_steps,
            "terminated_reason": self.terminated_reason,
            "steps": [s.as_dict() for s in self.steps],
        }


class InterSimEpisodeRunner:
    def __init__(
        self,
        *,
        env_factory: Callable[[], Any],
        policy: InterSimKerasDQNPolicy,
        shield: InterSimConicShield | None = None,
        epsilon: float = 0.0,
        seed: int | None = None,
        arm_label: str,
        backend: str,
        bank_id: str,
        policy_id: str,
        policy_checkpoint: str | None = None,
    ) -> None:
        self.env_factory = env_factory
        self.policy = policy
        self.shield = shield
        self.epsilon = float(epsilon)
        self.seed = seed
        self.arm_label = arm_label
        self.backend = backend
        self.bank_id = bank_id
        self.policy_id = policy_id
        self.policy_checkpoint = policy_checkpoint
        self.rng = np.random.default_rng(seed)

    def run_episode(self, episode_id: str) -> EpisodeRecord:
        env = self.env_factory()
        if self.shield is not None:
            self.shield.reset_episode()

        root_address = getattr(env, "current_address", None) or getattr(env, "starting_address", "")
        episode = EpisodeRecord(
            episode_id=episode_id,
            arm_label=self.arm_label,
            backend=self.backend,
            root_address=str(root_address),
            rule_choice=str(getattr(env, "rule_choice", "unknown")),
            bank_id=self.bank_id,
            policy_id=self.policy_id,
            policy_checkpoint=self.policy_checkpoint,
            seed=self.seed,
            started_at_utc=datetime.now(UTC).isoformat(),
        )

        for step_idx in range(getattr(env, "max_intersections", 1000) + 5):
            state = env.get_observation()
            current_address = getattr(state, "current_address", "")
            current_location = getattr(state, "current_location", None)
            previous_instruction = getattr(state, "previous_instruction", None)

            env_context = env.get_shield_context() if hasattr(env, "get_shield_context") else {}
            available_actions = list(env_context.get("allowed_actions", getattr(env, "action_space", [])))

            q_values = self.policy.score_actions(state)

            if self.rng.random() < self.epsilon:
                chosen_action = str(self.rng.choice(getattr(env, "action_space", available_actions)))
                step_record = StepRecord(
                    step=step_idx,
                    current_address=str(current_address),
                    current_location=tuple(current_location) if current_location is not None else None,
                    previous_instruction=previous_instruction,
                    available_actions=available_actions,
                    chosen_action=chosen_action,
                    reward=0.0,
                    raw_q_values=np.asarray(q_values, dtype=float).tolist(),
                )
            else:
                if self.shield is None:
                    action_idx = int(np.argmax(q_values))
                    chosen_action = env.action_space[action_idx]
                    step_record = StepRecord(
                        step=step_idx,
                        current_address=str(current_address),
                        current_location=tuple(current_location) if current_location is not None else None,
                        previous_instruction=previous_instruction,
                        available_actions=available_actions,
                        chosen_action=chosen_action,
                        reward=0.0,
                        raw_q_values=np.asarray(q_values, dtype=float).tolist(),
                    )
                else:
                    shield_context_snapshot = dict(env_context)
                    raw_q_values_list = np.asarray(q_values, dtype=float).tolist()

                    decision = self.shield.choose_action(
                        q_values=q_values,
                        action_space=env.action_space,
                        context=env_context,
                    )
                    chosen_action = decision.action_name
                    step_record = StepRecord(
                        step=step_idx,
                        current_address=str(current_address),
                        current_location=tuple(current_location) if current_location is not None else None,
                        previous_instruction=previous_instruction,
                        available_actions=available_actions,
                        chosen_action=chosen_action,
                        reward=0.0,
                        intervened=bool(decision.projection.intervened),
                        intervention_norm=decision.projection.intervention_norm,
                        objective_value=decision.projection.objective_value,
                        raw_q_values=raw_q_values_list,
                        proposed_distribution=decision.proposed_distribution.tolist(),
                        corrected_distribution=decision.corrected_distribution.tolist(),
                        active_constraints=list(decision.projection.active_constraints),
                        solver_status=decision.projection.solver_status,
                        iterations=decision.projection.iterations,
                        solve_time_sec=decision.projection.solve_time_sec,
                        setup_time_sec=decision.projection.setup_time_sec,
                        construction_time_sec=decision.projection.construction_time_sec,
                        device=decision.projection.device,
                        warm_started=decision.projection.warm_started,
                        metadata={
                            **decision.projection.metadata,
                            "shield_context_snapshot": shield_context_snapshot,
                            "canonical_action_space": list(env.action_space),
                            "spec_id": decision.spec_id,
                            "cache_key": decision.cache_key,
                        },
                    )

            transition = env.step(chosen_action)
            if len(transition) == 3:
                _next_state, reward, done = transition
                info = {}
            elif len(transition) == 4:
                _next_state, reward, done, info = transition
            else:
                raise ValueError("Unsupported env.step(...) return format")

            info = dict(info or {})
            step_record.reward = float(reward)
            step_record.matched_action = bool(info.get("matched_action", False))
            step_record.fallback_used = bool(info.get("fallback_used", False))
            step_record.selected_action_class = info.get("selected_action_class")
            step_record.selected_destination_address = info.get("selected_destination_address")
            step_record.selected_duration_sec = info.get("selected_duration_sec")
            step_record.selected_distance_m = info.get("selected_distance_m")
            step_record.metadata.update(info)

            episode.steps.append(step_record)

            if done:
                episode.terminated_reason = (
                    "out_of_bank"
                    if info.get("out_of_bank")
                    else "no_candidates"
                    if info.get("candidate_count", 1) == 0
                    else "max_intersections"
                )
                break

        episode.finalize()
        return episode

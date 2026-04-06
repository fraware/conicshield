from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from typing import Any


def canonical_json(data: Any) -> str:
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def short_digest(data: Any, length: int = 16) -> str:
    payload = canonical_json(data).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:length]


@dataclass(slots=True)
class PolicySpec:
    policy_name: str
    input_dim: int
    action_dim: int = 4
    checkpoint: str | None = None
    epsilon: float = 0.0
    frozen_weights: bool = True

    def policy_id(self) -> str:
        payload = {
            "policy_name": self.policy_name,
            "input_dim": self.input_dim,
            "action_dim": self.action_dim,
            "checkpoint": self.checkpoint,
            "epsilon": self.epsilon,
            "frozen_weights": self.frozen_weights,
        }
        return f"policy_{short_digest(payload)}"

    def to_config(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id(),
            "checkpoint": self.checkpoint,
            "input_dim": self.input_dim,
            "action_dim": self.action_dim,
            "epsilon": self.epsilon,
            "frozen_weights": self.frozen_weights,
        }


@dataclass(slots=True)
class EnvironmentSpec:
    env_name: str = "inter-sim-rl"
    action_space: tuple[str, ...] = (
        "turn_left",
        "turn_right",
        "go_straight",
        "turn_back",
    )
    rule_choices: tuple[str, ...] = ("right", "left", "alternate")
    max_intersections: int = 20
    location_dim: int = 2
    direction_dim: int = 2
    nearby_places_feature_size: int = 20

    def to_config(self) -> dict[str, Any]:
        return {
            "env_name": self.env_name,
            "action_space": list(self.action_space),
            "rule_choices": list(self.rule_choices),
            "max_intersections": self.max_intersections,
            "state_contract": {
                "location_dim": self.location_dim,
                "direction_dim": self.direction_dim,
                "nearby_places_feature_size": self.nearby_places_feature_size,
            },
        }


@dataclass(slots=True)
class TransitionBankSpec:
    root_addresses: list[str]
    max_depth: int = 4
    max_nodes: int = 300
    radius: int = 500
    max_candidates_per_node: int = 12

    def bank_id(self) -> str:
        payload = {
            "root_addresses": self.root_addresses,
            "max_depth": self.max_depth,
            "max_nodes": self.max_nodes,
            "radius": self.radius,
            "max_candidates_per_node": self.max_candidates_per_node,
        }
        return f"bank_{short_digest(payload)}"

    def to_config(self) -> dict[str, Any]:
        return {
            "bank_id": self.bank_id(),
            "root_addresses": list(self.root_addresses),
            "max_depth": self.max_depth,
            "max_nodes": self.max_nodes,
            "radius": self.radius,
            "max_candidates_per_node": self.max_candidates_per_node,
        }


@dataclass(slots=True)
class SolverSpec:
    device: str | None = None
    max_iter: int | None = None
    time_limit_sec: float | None = None
    policy_weight: float | None = None
    reference_weight: float | None = None

    def to_config(self) -> dict[str, Any]:
        return {
            "device": self.device,
            "max_iter": self.max_iter,
            "time_limit_sec": self.time_limit_sec,
            "policy_weight": self.policy_weight,
            "reference_weight": self.reference_weight,
        }


@dataclass(slots=True)
class ArmSpec:
    label: str
    backend: str
    use_geometry_prior: bool | None = None
    warm_start: bool | None = None
    solver: SolverSpec = field(default_factory=SolverSpec)

    def to_config(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "backend": self.backend,
            "use_geometry_prior": self.use_geometry_prior,
            "warm_start": self.warm_start,
            "solver": self.solver.to_config(),
        }


@dataclass(slots=True)
class CommitSpec:
    conicshield_commit: str | None = None
    inter_sim_rl_commit: str | None = None

    def to_config(self) -> dict[str, Any]:
        return {
            "conicshield_commit": self.conicshield_commit,
            "inter_sim_rl_commit": self.inter_sim_rl_commit,
        }


@dataclass(slots=True)
class RunSpec:
    benchmark_name: str
    description: str | None
    policy: PolicySpec
    environment: EnvironmentSpec
    transition_bank: TransitionBankSpec
    arms: list[ArmSpec]
    seeds: list[int]
    commits: CommitSpec = field(default_factory=CommitSpec)
    created_at_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def run_id(self) -> str:
        payload = self.to_config()
        return f"run_{short_digest(payload)}"

    def to_config(self) -> dict[str, Any]:
        return {
            "benchmark_name": self.benchmark_name,
            "description": self.description,
            "created_at_utc": self.created_at_utc,
            "policy": self.policy.to_config(),
            "environment": self.environment.to_config(),
            "transition_bank": self.transition_bank.to_config(),
            "arms": [arm.to_config() for arm in self.arms],
            "seeds": list(self.seeds),
            "commits": self.commits.to_config(),
        }

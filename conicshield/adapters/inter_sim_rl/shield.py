from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np

from conicshield.adapters.inter_sim_rl.geometry_prior import (
    GeometryPriorConfig,
    infer_geometry_prior,
)
from conicshield.core.interfaces import ProjectorProtocol
from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.result import ProjectionResult
from conicshield.core.solver_factory import Backend, create_projector
from conicshield.specs.compiler import SolverOptions
from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)

CANONICAL_ACTION_SPACE: tuple[str, ...] = (
    "turn_left",
    "turn_right",
    "go_straight",
    "turn_back",
)
ACTION_TO_INDEX = {name: idx for idx, name in enumerate(CANONICAL_ACTION_SPACE)}


def stable_softmax(logits: np.ndarray) -> np.ndarray:
    logits = np.asarray(logits, dtype=float)
    if logits.ndim != 1:
        raise ValueError("q_values/logits must be a 1D vector")
    shifted = logits - np.max(logits)
    exps = np.exp(shifted)
    denom = float(np.sum(exps))
    if denom <= 0.0 or not np.isfinite(denom):
        raise ValueError("softmax denominator is invalid")
    return cast(np.ndarray, exps / denom)


@dataclass(slots=True)
class ShieldDecision:
    action_name: str
    action_index: int
    proposed_distribution: np.ndarray
    corrected_distribution: np.ndarray
    projection: ProjectionResult
    spec_id: str
    cache_key: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_name": self.action_name,
            "action_index": self.action_index,
            "proposed_distribution": self.proposed_distribution.tolist(),
            "corrected_distribution": self.corrected_distribution.tolist(),
            "projection": self.projection.as_dict(),
            "spec_id": self.spec_id,
            "cache_key": self.cache_key,
        }


ProjectorFactory = Callable[
    [SafetySpec, Backend, SolverOptions | None, NativeMoreauCompiledOptions | None], ProjectorProtocol
]


@dataclass(slots=True)
class InterSimConicShield:
    backend: Backend = Backend.CVXPY_MOREAU
    solver_options: SolverOptions | None = None
    native_options: NativeMoreauCompiledOptions | None = None
    base_max_probability_delta: float = 0.80
    spec_version: str = "0.2.0"
    use_geometry_prior: bool = True
    geometry_prior_config: GeometryPriorConfig = field(default_factory=GeometryPriorConfig)
    projector_factory: ProjectorFactory | None = None

    _previous_distribution: np.ndarray | None = field(default=None, init=False)
    _projector_cache: dict[str, ProjectorProtocol] = field(default_factory=dict, init=False)

    def reset_episode(self) -> None:
        self._previous_distribution = None

    def choose_action(
        self,
        *,
        q_values: np.ndarray,
        action_space: list[str] | tuple[str, ...],
        context: Mapping[str, Any],
    ) -> ShieldDecision:
        q_values = np.asarray(q_values, dtype=float)
        action_space = tuple(str(a) for a in action_space)

        if set(action_space) != set(CANONICAL_ACTION_SPACE):
            raise ValueError("action_space must contain exactly: " f"{list(CANONICAL_ACTION_SPACE)}")
        if q_values.shape != (len(action_space),):
            raise ValueError(
                f"q_values shape {q_values.shape} does not match " f"action_space length {len(action_space)}"
            )

        q_values_canonical = self._reorder_to_canonical(
            values=q_values,
            action_space=action_space,
        )
        proposed_distribution = stable_softmax(q_values_canonical)

        if self.use_geometry_prior:
            geometry_prior, geometry_weight = infer_geometry_prior(
                context=context,
                config=self.geometry_prior_config,
            )
        else:
            geometry_prior, geometry_weight = None, 0.0

        spec = self._build_spec_from_context(context)
        cache_key = self._spec_cache_key(spec)

        projector = self._projector_cache.get(cache_key)
        if projector is None:
            if self.projector_factory is not None:
                projector = self.projector_factory(
                    spec,
                    self.backend,
                    self.solver_options,
                    self.native_options,
                )
            else:
                projector = create_projector(
                    spec=spec,
                    backend=self.backend,
                    cvxpy_options=self.solver_options,
                    native_options=self.native_options,
                )
            self._projector_cache[cache_key] = projector

        result = projector.project(
            proposed_action=proposed_distribution,
            previous_action=self._previous_distribution,
            reference_action=geometry_prior,
            policy_weight=1.0,
            reference_weight=float(geometry_weight),
            metadata={
                "raw_q_values_canonical": q_values_canonical.tolist(),
                "context_rule_choice": context.get("rule_choice"),
                "context_previous_instruction": context.get("previous_instruction"),
                "context_hazard_score": context.get("hazard_score"),
                "context_allowed_actions": list(context.get("allowed_actions", [])),
                "context_blocked_actions": list(context.get("blocked_actions", [])),
                "geometry_prior": None if geometry_prior is None else geometry_prior.tolist(),
                "geometry_weight": float(geometry_weight),
            },
        )

        corrected_distribution = np.asarray(result.corrected_action, dtype=float)
        chosen_idx_canonical = int(np.argmax(corrected_distribution))
        chosen_action = CANONICAL_ACTION_SPACE[chosen_idx_canonical]

        self._previous_distribution = corrected_distribution.copy()

        return ShieldDecision(
            action_name=chosen_action,
            action_index=action_space.index(chosen_action),
            proposed_distribution=proposed_distribution,
            corrected_distribution=corrected_distribution,
            projection=result,
            spec_id=spec.spec_id,
            cache_key=cache_key,
        )

    def _build_spec_from_context(self, context: Mapping[str, Any]) -> SafetySpec:
        allowed_actions = self._normalize_actions(context.get("allowed_actions", CANONICAL_ACTION_SPACE))
        blocked_actions = self._normalize_actions(context.get("blocked_actions", []))

        allowed_set = set(allowed_actions) - set(blocked_actions)
        if not allowed_set:
            allowed_set = set(CANONICAL_ACTION_SPACE)

        upper_bounds = {a: 1.0 for a in CANONICAL_ACTION_SPACE}
        raw_caps = context.get("action_upper_bounds", {})
        if isinstance(raw_caps, Mapping):
            for action_name, value in raw_caps.items():
                action_name = str(action_name)
                if action_name in upper_bounds:
                    cap = float(value)
                    upper_bounds[action_name] = max(0.0, min(1.0, cap))

        for action_name in CANONICAL_ACTION_SPACE:
            if action_name not in allowed_set:
                upper_bounds[action_name] = 0.0

        hazard_score = context.get("hazard_score")
        rate = self._adaptive_probability_delta(
            self.base_max_probability_delta,
            hazard_score,
        )

        allowed_indices = [
            ACTION_TO_INDEX[action_name] for action_name in CANONICAL_ACTION_SPACE if upper_bounds[action_name] > 1e-12
        ]
        if not allowed_indices:
            allowed_indices = list(range(len(CANONICAL_ACTION_SPACE)))

        upper = [upper_bounds[a] for a in CANONICAL_ACTION_SPACE]
        lower = [0.0] * len(CANONICAL_ACTION_SPACE)

        return SafetySpec(
            spec_id="inter-sim-rl/shield-context-v0",
            version=self.spec_version,
            action_dim=len(CANONICAL_ACTION_SPACE),
            constraints=[
                SimplexConstraint(total=1.0),
                TurnFeasibilityConstraint(allowed_actions=allowed_indices),
                BoxConstraint(lower=lower, upper=upper),
                RateConstraint(max_delta=[rate] * len(CANONICAL_ACTION_SPACE)),
            ],
        )

    @staticmethod
    def _normalize_actions(actions: Any) -> list[str]:
        out: list[str] = []
        for action in actions:
            name = str(action)
            if name not in CANONICAL_ACTION_SPACE:
                raise ValueError(f"Unknown action name in context: {name}")
            out.append(name)
        return out

    @staticmethod
    def _adaptive_probability_delta(
        base_delta: float,
        hazard_score: Any,
    ) -> float:
        if hazard_score is None:
            return base_delta
        hz = max(0.0, min(1.0, float(hazard_score)))
        scale = 1.0 - 0.65 * hz
        return max(0.10, base_delta * scale)

    @staticmethod
    def _reorder_to_canonical(
        *,
        values: np.ndarray,
        action_space: tuple[str, ...],
    ) -> np.ndarray:
        out = np.zeros(len(CANONICAL_ACTION_SPACE), dtype=float)
        action_to_pos = {name: idx for idx, name in enumerate(action_space)}
        for idx, action_name in enumerate(CANONICAL_ACTION_SPACE):
            out[idx] = float(values[action_to_pos[action_name]])
        return out

    @staticmethod
    def _spec_cache_key(spec: SafetySpec) -> str:
        payload = json.dumps(
            spec.model_dump(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

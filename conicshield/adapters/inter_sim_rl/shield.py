from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, cast

import numpy as np

from conicshield.adapters.inter_sim_rl.geometry_prior import (
    GeometryPriorConfig,
    infer_geometry_prior,
)
from conicshield.compilation.bounded_cache import BoundedLRUCache
from conicshield.compilation.metrics import LifecycleMetrics
from conicshield.compilation.structural_keys import (
    numerical_signature,
    structural_fingerprint,
)
from conicshield.core.interfaces import ConcurrencyModel, ProjectorProtocol
from conicshield.core.moreau_batched import NativeMoreauCompiledBatchProjector
from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.result import ProjectionResult
from conicshield.core.solver_factory import Backend, create_batch_projector, create_projector
from conicshield.specs.compiler import SolverOptions
from conicshield.specs.errors import MissingFailSafePolicyError
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


def _call_reset_state(projector: object, *, scope_id: str | None = None) -> None:
    reset = getattr(projector, "reset_state", None)
    if callable(reset):
        reset(scope_id=scope_id)


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
class _CachedProjector:
    projector: ProjectorProtocol
    numerical_digest: str


@dataclass(slots=True)
class InterSimConicShield:
    """Inter-Sim RL shield with episode-isolated warm starts and structural LRU caching.

    Concurrency: default :attr:`ConcurrencyModel.INSTANCE_CONFINED` (one owner episode).
    Set ``concurrency_model=LOCK_PROTECTED`` to serialize ``choose_action`` /
    ``reset_episode`` for shared instances. Cached projectors are never shared across
    shield instances, so concurrent episodes with distinct shields cannot exchange
    warm starts.
    """

    backend: Backend = Backend.CVXPY_MOREAU
    solver_options: SolverOptions | None = None
    native_options: NativeMoreauCompiledOptions | None = None
    base_max_probability_delta: float = 0.80
    spec_version: str = "0.2.0"
    use_geometry_prior: bool = True
    geometry_prior_config: GeometryPriorConfig = field(default_factory=GeometryPriorConfig)
    projector_factory: ProjectorFactory | None = None
    projector_cache_max_size: int = 64
    concurrency_model: ConcurrencyModel = ConcurrencyModel.INSTANCE_CONFINED
    metrics: LifecycleMetrics | None = None

    _previous_distribution: np.ndarray | None = field(default=None, init=False)
    _metrics: LifecycleMetrics = field(init=False, repr=False)
    _projector_cache: BoundedLRUCache[str, _CachedProjector] = field(init=False, repr=False)
    _batch_projector_cache: BoundedLRUCache[str, NativeMoreauCompiledBatchProjector] = field(init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)
    _episode_scope_id: str = field(default="episode", init=False, repr=False)

    def __post_init__(self) -> None:
        self._metrics = self.metrics if self.metrics is not None else LifecycleMetrics()

        def _on_evict(_key: str, cached: _CachedProjector) -> None:
            _call_reset_state(cached.projector)

        def _on_batch_evict(_key: str, batch: NativeMoreauCompiledBatchProjector) -> None:
            batch.reset_state()

        self._projector_cache = BoundedLRUCache(
            max_size=int(self.projector_cache_max_size),
            metrics=self._metrics,
            on_evict=_on_evict,
        )
        self._batch_projector_cache = BoundedLRUCache(
            max_size=max(4, int(self.projector_cache_max_size) // 4),
            metrics=self._metrics,
            on_evict=_on_batch_evict,
        )

    @property
    def lifecycle_metrics(self) -> LifecycleMetrics:
        return self._metrics

    def reset_episode(self) -> None:
        """Clear previous action and all episode/projector warm-start state."""
        if self.concurrency_model is ConcurrencyModel.LOCK_PROTECTED:
            with self._lock:
                self._reset_episode_unlocked()
            return
        self._reset_episode_unlocked()

    def _reset_episode_unlocked(self) -> None:
        self._previous_distribution = None
        for cached in self._projector_cache.values():
            _call_reset_state(cached.projector, scope_id=self._episode_scope_id)
            # Also clear anonymous / full scope so sequential projectors drop ``_warm``.
            _call_reset_state(cached.projector)
        for batch in self._batch_projector_cache.values():
            batch.reset_state(scope_id=self._episode_scope_id)
            batch.reset_state()

    def choose_action(
        self,
        *,
        q_values: np.ndarray,
        action_space: list[str] | tuple[str, ...],
        context: Mapping[str, Any],
    ) -> ShieldDecision:
        if self.concurrency_model is ConcurrencyModel.LOCK_PROTECTED:
            with self._lock:
                return self._choose_action_unlocked(
                    q_values=q_values,
                    action_space=action_space,
                    context=context,
                )
        return self._choose_action_unlocked(
            q_values=q_values,
            action_space=action_space,
            context=context,
        )

    def _choose_action_unlocked(
        self,
        *,
        q_values: np.ndarray,
        action_space: list[str] | tuple[str, ...],
        context: Mapping[str, Any],
    ) -> ShieldDecision:
        q_values = np.asarray(q_values, dtype=float)
        action_space = tuple(str(a) for a in action_space)

        if set(action_space) != set(CANONICAL_ACTION_SPACE):
            raise ValueError(f"action_space must contain exactly: {list(CANONICAL_ACTION_SPACE)}")
        if q_values.shape != (len(action_space),):
            raise ValueError(f"q_values shape {q_values.shape} does not match action_space length {len(action_space)}")

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
        cache_key = self._structural_cache_key(spec)
        projector = self._get_or_create_projector(spec, cache_key)

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

    def project_softmax_batch(
        self,
        *,
        proposed_softmax_rows: np.ndarray,
        context: Mapping[str, Any],
        policy_weight: float = 1.0,
        trajectory_ids: list[str] | tuple[str, ...] | None = None,
    ) -> np.ndarray:
        """Project ``K`` simplex proposals in one native ``CompiledSolver`` batch call.

        Requires ``Backend.NATIVE_MOREAU``. Uses the same spec/geometry prior as
        :meth:`choose_action` and the current episode ``previous_action`` state.
        ``proposed_softmax_rows`` must have shape ``(K, len(CANONICAL_ACTION_SPACE))``.
        Returns corrected rows with the same shape.
        """
        if self.concurrency_model is ConcurrencyModel.LOCK_PROTECTED:
            with self._lock:
                return self._project_softmax_batch_unlocked(
                    proposed_softmax_rows=proposed_softmax_rows,
                    context=context,
                    policy_weight=policy_weight,
                    trajectory_ids=trajectory_ids,
                )
        return self._project_softmax_batch_unlocked(
            proposed_softmax_rows=proposed_softmax_rows,
            context=context,
            policy_weight=policy_weight,
            trajectory_ids=trajectory_ids,
        )

    def _project_softmax_batch_unlocked(
        self,
        *,
        proposed_softmax_rows: np.ndarray,
        context: Mapping[str, Any],
        policy_weight: float = 1.0,
        trajectory_ids: list[str] | tuple[str, ...] | None = None,
    ) -> np.ndarray:
        if self.backend != Backend.NATIVE_MOREAU:
            raise ValueError("project_softmax_batch requires Backend.NATIVE_MOREAU")
        pb = np.asarray(proposed_softmax_rows, dtype=np.float64)
        if pb.ndim != 2:
            raise ValueError(f"proposed_softmax_rows must be 2D, got shape {pb.shape}")
        if pb.shape[1] != len(CANONICAL_ACTION_SPACE):
            raise ValueError(
                f"proposed_softmax_rows second dim must be {len(CANONICAL_ACTION_SPACE)}, got {pb.shape[1]}"
            )
        if pb.shape[0] < 1:
            raise ValueError("batch size must be >= 1")

        if self.use_geometry_prior:
            geometry_prior, geometry_weight = infer_geometry_prior(
                context=context,
                config=self.geometry_prior_config,
            )
        else:
            geometry_prior, geometry_weight = None, 0.0

        spec = self._build_spec_from_context(context)
        cache_key = self._structural_cache_key(spec, batch=True)
        batch = self._get_or_create_batch_projector(spec, cache_key)
        ids = trajectory_ids
        if ids is None:
            # Bind anonymous batch warm starts to this shield episode so reset clears them.
            ids = tuple(f"{self._episode_scope_id}:row{i}" for i in range(pb.shape[0]))
        return batch.project_batch(
            pb,
            self._previous_distribution,
            reference_action=geometry_prior,
            policy_weight=float(policy_weight),
            reference_weight=float(geometry_weight),
            trajectory_ids=ids,
        ).corrected_actions

    def _get_or_create_projector(self, spec: SafetySpec, cache_key: str) -> ProjectorProtocol:
        num = numerical_signature(spec)
        cached = self._projector_cache.get(cache_key)
        if cached is not None:
            if cached.numerical_digest != num.digest:
                # Same CSR topology / constraint kinds; refresh parametric fills.
                if hasattr(cached.projector, "spec"):
                    cached.projector.spec = spec  # type: ignore[attr-defined]
                cached.numerical_digest = num.digest
            return cached.projector

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
        self._projector_cache.put(
            cache_key,
            _CachedProjector(projector=projector, numerical_digest=num.digest),
        )
        return projector

    def _get_or_create_batch_projector(
        self,
        spec: SafetySpec,
        cache_key: str,
    ) -> NativeMoreauCompiledBatchProjector:
        cached = self._batch_projector_cache.get(cache_key)
        if cached is not None:
            self._metrics.record_cache_hit()
            cached.bind_spec(spec)
            return cached
        self._metrics.record_cache_miss()
        batch = create_batch_projector(
            spec=spec,
            backend=Backend.NATIVE_MOREAU_BATCH,
            native_options=self.native_options,
            metrics=self._metrics,
        )
        self._batch_projector_cache.put(cache_key, batch)
        return batch

    def _structural_options(self, *, batch: bool = False) -> dict[str, Any]:
        opts: dict[str, Any] = {}
        if self.native_options is not None:
            opts["use_compiled_solver"] = bool(self.native_options.use_compiled_solver)
            opts["device"] = str(self.native_options.device)
            opts["auto_tune"] = bool(self.native_options.auto_tune)
            opts["enable_grad"] = bool(self.native_options.enable_grad)
        if batch:
            opts["batch_size"] = "dynamic"
        return opts

    def _structural_cache_key(self, spec: SafetySpec, *, batch: bool = False) -> str:
        fp = structural_fingerprint(
            spec,
            backend=str(self.backend),
            structural_options=self._structural_options(batch=batch),
        )
        return fp.digest

    def _build_spec_from_context(self, context: Mapping[str, Any]) -> SafetySpec:
        allowed_actions = self._normalize_actions(context.get("allowed_actions", CANONICAL_ACTION_SPACE))
        blocked_actions = self._normalize_actions(context.get("blocked_actions", []))

        allowed_set = set(allowed_actions) - set(blocked_actions)
        if not allowed_set:
            allowed_set = set(CANONICAL_ACTION_SPACE)

        upper_bounds = dict.fromkeys(CANONICAL_ACTION_SPACE, 1.0)
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
            raise MissingFailSafePolicyError(
                "no action is admissible in shield context; refusing silent "
                "'all actions allowed' recovery. Select an explicit fail-safe at the "
                "call site or ensure at least one action remains admissible."
            )

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

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator

from conicshield.adapters.inter_sim_rl.context_validate import validate_shield_context_dict
from conicshield.adapters.inter_sim_rl.policy import InterSimKerasDQNPolicy
from conicshield.adapters.inter_sim_rl.shield import InterSimConicShield
from conicshield.bench.episode_runner import InterSimEpisodeRunner
from conicshield.bench.passthrough_projector import PassthroughProjector
from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.solver_factory import Backend
from conicshield.specs.compiler import SolverOptions
from conicshield.specs.schema import SafetySpec


def _passthrough_factory(
    _spec: SafetySpec,
    _backend: Backend,
    _solver_options: SolverOptions | None,
    _native_options: NativeMoreauCompiledOptions | None,
):
    return PassthroughProjector()


def _intersim_root() -> Path | None:
    root = os.environ.get("INTERSIM_RL_ROOT", "").strip()
    if root and Path(root).is_dir():
        return Path(root).resolve()
    sub = Path(__file__).resolve().parents[1] / "third_party" / "inter-sim-rl" / "checkout"
    if sub.is_dir():
        return sub.resolve()
    return None


def _offline_fork_graph() -> dict[str, list[dict]]:
    return {
        "Root": [
            {
                "destination_address": "NodeA",
                "destination_coords": (1.0, 0.0),
                "first_instruction": "Turn right",
                "action_class": "turn_right",
                "duration_sec": 10.0,
                "distance_m": 100.0,
            },
            {
                "destination_address": "NodeB",
                "destination_coords": (0.0, 1.0),
                "first_instruction": "Turn left",
                "action_class": "turn_left",
                "duration_sec": 12.0,
                "distance_m": 120.0,
            },
        ],
        "NodeA": [
            {
                "destination_address": "NodeC",
                "destination_coords": (2.0, 0.0),
                "first_instruction": "Go straight",
                "action_class": "go_straight",
                "duration_sec": 5.0,
                "distance_m": 50.0,
            },
        ],
        "NodeB": [],
        "NodeC": [],
    }


pytestmark = pytest.mark.inter_sim_rl


@pytest.mark.skipif(_intersim_root() is None, reason="INTERSIM_RL_ROOT or third_party/inter-sim-rl/checkout missing")
def test_inter_sim_rl_upstream_layout_matches_expected_package() -> None:
    """Assert checkout looks like fraware/inter-sim-rl (package dir + pyproject) without importing TensorFlow."""
    root = _intersim_root()
    assert root is not None
    pkg = root / "inter_sim_rl"
    assert pkg.is_dir(), f"expected Python package at {pkg}"
    init_py = pkg / "__init__.py"
    assert init_py.is_file(), f"missing {init_py}"
    pyproject = root / "pyproject.toml"
    assert pyproject.is_file(), f"missing {pyproject}"


@pytest.mark.skipif(_intersim_root() is None, reason="INTERSIM_RL_ROOT or third_party/inter-sim-rl/checkout missing")
def test_action_conditioning_changes_transition_destination() -> None:
    """Two different actions from the same root must select different destinations when graph branches."""
    root = _intersim_root()
    assert root is not None
    sys.path.insert(0, str(root))
    try:
        from inter_sim_rl.rl_environment import RLEnvironment  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)

    graph = _offline_fork_graph()
    env_r = RLEnvironment(
        starting_address="Root",
        max_intersections=5,
        rule_choice="right",
        offline_transition_graph=graph,
        random_seed=0,
    )
    _s, _rw, _dw, info_r = env_r.step("turn_right")
    env_l = RLEnvironment(
        starting_address="Root",
        max_intersections=5,
        rule_choice="right",
        offline_transition_graph=graph,
        random_seed=0,
    )
    _s, _lw, _dl, info_l = env_l.step("turn_left")
    if "selected_destination_address" not in info_r or "selected_destination_address" not in info_l:
        pytest.skip("RLEnvironment.step missing M2 info keys; apply inter-sim-rl patch or use inter-sim-rl-ci")
    assert info_r["selected_destination_address"] != info_l["selected_destination_address"]


@pytest.mark.skipif(_intersim_root() is None, reason="INTERSIM_RL_ROOT or third_party/inter-sim-rl/checkout missing")
def test_upstream_get_shield_context_matches_conicshield_schema() -> None:
    root = _intersim_root()
    assert root is not None
    sys.path.insert(0, str(root))
    try:
        from inter_sim_rl.rl_environment import RLEnvironment  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)

    env = RLEnvironment(
        starting_address="Root",
        max_intersections=5,
        rule_choice="right",
        offline_transition_graph=_offline_fork_graph(),
        random_seed=0,
    )
    ctx = env.get_shield_context()
    validate_shield_context_dict(ctx)
    repo = Path(__file__).resolve().parents[1]
    schema_path = repo / "schemas" / "shield_context.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(ctx)


@pytest.mark.skipif(_intersim_root() is None, reason="INTERSIM_RL_ROOT or third_party/inter-sim-rl/checkout missing")
def test_episode_runner_with_upstream_env_and_passthrough_shield() -> None:
    root = _intersim_root()
    assert root is not None
    sys.path.insert(0, str(root))
    try:
        from inter_sim_rl.rl_environment import RLEnvironment  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)

    graph = _offline_fork_graph()

    def env_factory() -> RLEnvironment:
        return RLEnvironment(
            starting_address="Root",
            max_intersections=3,
            rule_choice="right",
            offline_transition_graph=graph,
            random_seed=42,
        )

    class _Model:
        q = np.array([0.1, 3.0, 0.0, -1.0], dtype=float)

        class _Inner:
            @staticmethod
            def predict(x: object, verbose: int = 0) -> np.ndarray:
                return np.array([_Model.q], dtype=float)

        model = _Inner()

    shield = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        use_geometry_prior=True,
        projector_factory=_passthrough_factory,
    )
    runner = InterSimEpisodeRunner(
        env_factory=env_factory,
        policy=InterSimKerasDQNPolicy(dqn_model=_Model()),
        shield=shield,
        epsilon=0.0,
        seed=1,
        arm_label="shielded-rules-plus-geometry",
        backend="cvxpy_moreau",
        bank_id="upstream_offline",
        policy_id="stub",
        policy_checkpoint=None,
    )
    ep = runner.run_episode("upstream-offline-001")
    assert ep.num_steps >= 1
    for s in ep.steps:
        assert np.all(np.isfinite(np.asarray(s.raw_q_values, dtype=float)))
        assert s.chosen_action in (
            "turn_left",
            "turn_right",
            "go_straight",
            "turn_back",
        )
        if s.corrected_distribution is not None:
            assert np.isfinite(np.sum(s.corrected_distribution))


@pytest.mark.skipif(_intersim_root() is None, reason="INTERSIM_RL_ROOT or third_party/inter-sim-rl/checkout missing")
def test_episode_runner_upstream_multi_step_stability() -> None:
    root = _intersim_root()
    assert root is not None
    sys.path.insert(0, str(root))
    try:
        from inter_sim_rl.rl_environment import RLEnvironment  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)

    graph = _offline_fork_graph()

    def env_factory() -> RLEnvironment:
        return RLEnvironment(
            starting_address="Root",
            max_intersections=12,
            rule_choice="right",
            offline_transition_graph=graph,
            random_seed=99,
        )

    class _Model:
        q = np.array([0.2, 2.5, 0.3, -0.5], dtype=float)

        class _Inner:
            @staticmethod
            def predict(x: object, verbose: int = 0) -> np.ndarray:
                return np.array([_Model.q], dtype=float)

        model = _Inner()

    shield = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        use_geometry_prior=True,
        projector_factory=_passthrough_factory,
    )
    runner = InterSimEpisodeRunner(
        env_factory=env_factory,
        policy=InterSimKerasDQNPolicy(dqn_model=_Model()),
        shield=shield,
        epsilon=0.0,
        seed=2,
        arm_label="shielded-rules-plus-geometry",
        backend="cvxpy_moreau",
        bank_id="upstream_offline",
        policy_id="stub",
        policy_checkpoint=None,
    )
    ep = runner.run_episode("upstream-offline-stability")
    assert ep.num_steps >= 1
    assert np.isfinite(ep.total_reward)
    for s in ep.steps:
        assert np.all(np.isfinite(np.asarray(s.raw_q_values, dtype=float)))
        if s.proposed_distribution is not None:
            assert np.isfinite(np.sum(s.proposed_distribution))
        if s.corrected_distribution is not None:
            assert np.isfinite(np.sum(s.corrected_distribution))

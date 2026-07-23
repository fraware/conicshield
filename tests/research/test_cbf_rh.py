"""Tests for experimental short-horizon RH CBF filter and stage-4 gate coupling."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from conicshield.experimental.domains.cbf_2d import (
    AgentState2D,
    CBF2DDomain,
    CircularObstacle,
)
from conicshield.experimental.domains.cbf_rh import (
    RH_EXPERIMENT_VERSION,
    RHConstraintMode,
    demo_rh_scenario,
    describe_rh_capability,
    run_receding_horizon_filter,
)
from conicshield.experimental.domains.stage4_gate import evaluate_stage4_gate
from conicshield.experimental.gradients.capability import CapabilityStatus


def test_stage4_gate_reports_experimental_rh(tmp_path: Path) -> None:
    ev = evaluate_stage4_gate(evidence_dir=tmp_path)
    d = ev.as_dict()
    assert d["experimental_rh_implemented"] is True
    assert d["rh_mpc_implemented"] is False
    assert d["stage4_status"] in {
        "experimental_rh_available",
        "blocked",
        "checklist_green_rh_not_implemented",
    }
    if d["all_required_passed"]:
        assert d["stage4_status"] == "experimental_rh_available"
        assert d["unblock_allowed"] is True
    assert d["experimental_rh"]["experiment_version"] == RH_EXPERIMENT_VERSION
    assert (tmp_path / "stage4_gate_evaluation.json").is_file()
    domain = CBF2DDomain()
    assert domain.stage4.status == "experimental_rh_available"
    assert domain.stage4.rh_mpc_full is False


def test_rh_runs_only_when_checklist_green() -> None:
    gate = evaluate_stage4_gate()
    agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]), "a0")
    obs = CircularObstacle(np.array([1.2, 0.0]), 0.5, "o0")
    if gate.unblock_allowed and gate.as_dict()["all_required_passed"]:
        result = run_receding_horizon_filter(
            agent,
            obs,
            horizon=3,
            require_stage4_checklist_green=True,
            gate_evaluation=gate,
        )
        assert result.ran is True
        assert result.capability_status == CapabilityStatus.AVAILABLE
        assert result.metrics is not None
        assert result.experimental is True
        assert result.production_claim is False
        assert "no_filter" in result.baseline_comparison
        assert "public_solver_single_step" in result.baseline_comparison
        assert result.reproducibility.get("horizon") == 3
    else:
        result = run_receding_horizon_filter(
            agent,
            obs,
            require_stage4_checklist_green=True,
            gate_evaluation=gate,
        )
        assert result.ran is False
        assert result.capability_status == CapabilityStatus.BLOCKED


def test_rh_fail_closed_when_gate_not_green() -> None:
    fake_gate = SimpleNamespace(
        as_dict=lambda: {
            "stage4_status": "blocked",
            "unblock_allowed": False,
            "all_required_passed": False,
            "passed_count": 0,
            "required_count": 6,
        }
    )
    agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]), "a0")
    obs = CircularObstacle(np.array([1.2, 0.0]), 0.5, "o0")
    result = run_receding_horizon_filter(
        agent,
        obs,
        require_stage4_checklist_green=True,
        gate_evaluation=fake_gate,
    )
    assert result.ran is False
    assert result.capability_status == CapabilityStatus.BLOCKED
    assert result.fail_closed_reason is not None
    assert "stage4_checklist_not_green" in result.fail_closed_reason


def test_rh_soc_robust_mode_and_negatives() -> None:
    fake_green = SimpleNamespace(
        as_dict=lambda: {
            "stage4_status": "experimental_rh_available",
            "unblock_allowed": True,
            "all_required_passed": True,
            "passed_count": 6,
            "required_count": 6,
        }
    )
    # Extremely tight u_max near obstacle → likely infeasible / negative retention
    agent = AgentState2D(np.array([0.55, 0.0]), np.array([1.0, 0.0]), "tight")
    obs = CircularObstacle(np.array([1.0, 0.0]), 0.5, "o0")
    result = run_receding_horizon_filter(
        agent,
        obs,
        horizon=3,
        u_max=0.05,
        constraint_mode=RHConstraintMode.SOC_ROBUST_STAGE3,
        epsilon=0.05,
        require_stage4_checklist_green=True,
        gate_evaluation=fake_green,
        compare_baselines=False,
    )
    assert result.ran is True
    assert result.metrics is not None
    # Negatives structure always present for retention
    assert "infeasible_steps" in result.negatives.as_dict()
    assert "active_set_chatter_steps" in result.negatives.as_dict()


def test_demo_rh_and_capability_descriptor() -> None:
    cap = describe_rh_capability()
    assert cap["implemented"] is True
    assert cap["rh_mpc_full"] is False
    assert cap["multi_robot"] is False
    # Bypass only for unit isolation of demo wiring when gate might be pending in odd envs
    result = demo_rh_scenario(require_gate=False)
    assert result.ran is True
    assert len(result.steps) >= 1


def test_rh_horizon_cap() -> None:
    fake_green = SimpleNamespace(
        as_dict=lambda: {
            "stage4_status": "experimental_rh_available",
            "unblock_allowed": True,
            "all_required_passed": True,
        }
    )
    agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]))
    obs = CircularObstacle(np.array([1.2, 0.0]), 0.5)
    try:
        run_receding_horizon_filter(
            agent,
            obs,
            horizon=99,
            gate_evaluation=fake_green,
            require_stage4_checklist_green=True,
            compare_baselines=False,
        )
        ok = False
    except ValueError:
        ok = True
    assert ok

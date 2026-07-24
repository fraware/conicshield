"""R11 Current Moreau Gradient Observatory tests."""

from __future__ import annotations

import numpy as np
import pytest

from conicshield.experimental.adapters.projection import ResearchProjectionResult
from conicshield.experimental.adapters.track1_protocols import CanonicalSolverStatus
from conicshield.experimental.assurance.levels import VerificationStatus
from conicshield.experimental.corpus.generate import load_all_scenarios
from conicshield.experimental.gradients.active_set_protocol import (
    ActiveSetTransitionClass,
    classify_active_set_transition,
)
from conicshield.experimental.gradients.adapters import (
    DIFFERENTIATION_TARGET_CATALOG,
    IMPLEMENTED_DIFFERENTIATION_TARGETS,
    AdapterId,
    differentiate_target_central_fd,
    list_implemented_adapters,
    list_implemented_targets,
    run_pytorch_autograd,
)
from conicshield.experimental.gradients.capability import CapabilityStatus
from conicshield.experimental.gradients.forward_gate import verify_forward_projection
from conicshield.experimental.gradients.modes import GradientMode
from conicshield.experimental.gradients.observatory import observe_proposed_action_fd
from conicshield.experimental.gradients.smoothed_study import run_smoothed_study
from conicshield.experimental.gradients.step_size_study import default_log_grid, run_step_size_study
from conicshield.specs.schema import SafetySpec


def _interior_scenario() -> tuple[SafetySpec, dict]:
    scenario = next(s for s in load_all_scenarios() if s["family"] == "interior_feasible")
    return SafetySpec.model_validate(scenario["spec"]), scenario


def test_implemented_targets_include_ready_adapters() -> None:
    assert "proposed_action" in IMPLEMENTED_DIFFERENTIATION_TARGETS
    assert "previous_action" in IMPLEMENTED_DIFFERENTIATION_TARGETS
    assert "reference_action" in IMPLEMENTED_DIFFERENTIATION_TARGETS
    assert "policy_weight" in IMPLEMENTED_DIFFERENTIATION_TARGETS
    assert "reference_weight" in IMPLEMENTED_DIFFERENTIATION_TARGETS
    assert "box_bounds" in IMPLEMENTED_DIFFERENTIATION_TARGETS
    assert "policy_logits" in DIFFERENTIATION_TARGET_CATALOG
    assert "policy_logits" not in IMPLEMENTED_DIFFERENTIATION_TARGETS
    assert "rate_limits" not in IMPLEMENTED_DIFFERENTIATION_TARGETS
    adapters = list_implemented_adapters()
    ids = {a["adapter_id"] for a in adapters}
    assert str(AdapterId.CENTRAL_FD) in ids
    assert str(AdapterId.RESEARCH_KKT) in ids
    # Unimplemented optional frameworks must not claim implemented=True falsely.
    for row in adapters:
        if row["adapter_id"] == str(AdapterId.JAX_AUTODIFF) and not row["implemented"]:
            assert row["implemented"] is False


def test_active_set_transition_classification() -> None:
    stable = classify_active_set_transition(
        active_set_base=("a",),
        active_set_plus=("a",),
        active_set_minus=("a",),
        epsilon=1e-5,
    )
    assert stable.classification == ActiveSetTransitionClass.STABLE
    assert stable.prefer_one_sided_derivatives is False

    one = classify_active_set_transition(
        active_set_base=("a",),
        active_set_plus=("a", "b"),
        active_set_minus=("a",),
        epsilon=1e-5,
    )
    assert one.classification == ActiveSetTransitionClass.ONE_SIDED
    assert one.prefer_one_sided_derivatives is True

    two = classify_active_set_transition(
        active_set_base=("a",),
        active_set_plus=("b",),
        active_set_minus=("c",),
        epsilon=1e-5,
    )
    assert two.classification == ActiveSetTransitionClass.TWO_SIDED

    amb = classify_active_set_transition(
        active_set_base=("a",),
        active_set_plus=("b",),
        active_set_minus=("b",),
        epsilon=1e-5,
    )
    assert amb.classification == ActiveSetTransitionClass.AMBIGUOUS


def test_forward_gate_blocks_missing_residuals() -> None:
    spec, scenario = _interior_scenario()
    primary = ResearchProjectionResult(
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        corrected_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        intervened=False,
        intervention_norm=0.0,
        solver_status="optimal",
        canonical_status=CanonicalSolverStatus.OPTIMAL,
        equality_residual=None,
        inequality_residual=None,
        active_constraints=[],
    )
    vf = verify_forward_projection(primary=primary, spec=spec, require_feasible=True)
    assert vf.verified is False


def test_target_adapters_ready_and_unimplemented_fail_closed() -> None:
    spec, scenario = _interior_scenario()
    proposed = np.asarray(scenario["proposed_action"], dtype=np.float64)
    previous = np.asarray(scenario["previous_action"], dtype=np.float64)
    reference = np.asarray(scenario["reference_action"], dtype=np.float64)
    from conicshield.experimental.solver_assurance.backends import create_research_projector

    projector = create_research_projector(backend_id="cvxpy_clarabel", spec=spec)
    primary = projector.project(
        proposed, previous, reference_action=reference, policy_weight=1.0, reference_weight=0.25
    )
    vf = verify_forward_projection(
        primary=primary,
        spec=spec,
        previous_action=previous,
        reference_action=reference,
        policy_weight=1.0,
        reference_weight=0.25,
        require_feasible=True,
    )
    assert vf.verified is True

    registry = {r["target"]: r for r in list_implemented_targets()}
    assert registry["proposed_action"]["implemented"] is True
    assert registry["policy_logits"]["implemented"] is False

    prev_jac = differentiate_target_central_fd(
        forward=vf,
        spec=spec,
        target="previous_action",
        previous_action=previous,
        reference_action=reference,
        policy_weight=1.0,
        reference_weight=0.25,
        h=1e-5,
    )
    assert prev_jac.available is True
    assert prev_jac.jacobian is not None
    assert prev_jac.forward_solution_digest == vf.forward_solution_digest

    pw_jac = differentiate_target_central_fd(
        forward=vf,
        spec=spec,
        target="policy_weight",
        previous_action=previous,
        reference_action=reference,
        policy_weight=1.0,
        reference_weight=0.25,
        h=1e-4,
    )
    assert pw_jac.available is True
    assert pw_jac.jacobian is not None
    assert pw_jac.jacobian.shape[1] == 1

    unimplemented = differentiate_target_central_fd(
        forward=vf,
        spec=spec,
        target="policy_logits",
        previous_action=previous,
        reference_action=reference,
        policy_weight=1.0,
        reference_weight=0.25,
    )
    assert unimplemented.available is False
    assert "not_implemented" in unimplemented.reason
    assert unimplemented.extras.get("implemented") is False


def test_observatory_forward_gate_and_digest_binding() -> None:
    spec, scenario = _interior_scenario()
    report = observe_proposed_action_fd(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        include_research_gradients=True,
        include_torch=True,
        include_jax=True,
        run_step_size=False,
        run_smoothed=False,
        scenario_id=str(scenario["scenario_id"]),
    )
    assert report.gradient_unavailable is False
    assert report.verified_forward["verified"] is True
    assert len(report.verified_forward["forward_solution_digest"]) == 64
    assert len(report.verified_forward["problem_digest"]) == 64
    payload = report.as_dict()
    assert payload["claims_production_differentiation_api"] is False
    assert "proposed_action" in payload["differentiation_targets"]
    assert "previous_action" in payload["differentiation_targets"]
    assert "box_bounds" in payload["differentiation_targets"]
    assert "policy_logits" not in payload["differentiation_targets"]
    assert str(AdapterId.CENTRAL_FD) in report.adapters
    assert str(AdapterId.RESEARCH_KKT) in report.adapters
    assert "differentiation_targets" in report.adapters
    for key, ad in report.adapters.items():
        if key == "differentiation_targets":
            continue
        assert ad.get("claims_production_differentiation_api") is False
        if ad.get("available"):
            assert ad.get("forward_solution_digest") == report.verified_forward["forward_solution_digest"]


def test_step_size_study_log_grid() -> None:
    def f(x: np.ndarray) -> np.ndarray:
        return np.array([x[0] + 2.0 * x[1], x[0] ** 2], dtype=np.float64)

    x = np.array([1.0, 0.5], dtype=np.float64)
    grid = default_log_grid(h_min=1e-7, h_max=1e-3, n=5)
    report = run_step_size_study(f, x, grid=grid)
    assert report.selected_step is not None
    assert len(report.samples) == len(grid)
    regimes = {s.regime for s in report.samples}
    assert "failed" not in regimes or any(s.regime != "failed" for s in report.samples)


def test_smoothed_study_distinct_digests() -> None:
    spec, scenario = _interior_scenario()
    study = run_smoothed_study(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        epsilons=(1e-2, 1e-3),
        compare_fd=False,
        scenario_id=str(scenario["scenario_id"]),
    )
    assert study.rows
    for row in study.rows:
        if row.available:
            assert row.digests_distinct is True
            assert row.soft_forward_digest != row.hard_forward_digest
            assert row.soft_vs_hard_l2 is not None


def test_pytorch_adapter_when_torch_installed() -> None:
    torch = pytest.importorskip("torch")
    del torch
    spec, scenario = _interior_scenario()
    report = observe_proposed_action_fd(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        include_research_gradients=False,
        include_torch=True,
        include_jax=False,
        run_step_size=False,
        run_smoothed=False,
    )
    assert report.gradient_unavailable is False
    torch_ad = report.adapters.get(str(AdapterId.PYTORCH_AUTOGRAD))
    assert torch_ad is not None
    assert torch_ad["claims_production_differentiation_api"] is False
    if torch_ad["available"]:
        assert torch_ad["jacobian"] is not None
        assert GradientMode.PYTORCH_AUTOGRAD.value in {str(m.mode) for m in report.metrics}


def test_unverified_forward_blocks_adapters() -> None:
    spec, scenario = _interior_scenario()
    from conicshield.experimental.gradients.forward_gate import VerifiedForward

    bogus = VerifiedForward(
        verified=False,
        verification_status=VerificationStatus.UNVERIFIED,
        problem_digest="0" * 64,
        forward_solution_digest="1" * 64,
        topology_digest="2" * 64,
        canonical_status="unknown",
        equality_residual=None,
        inequality_residual=None,
        corrected_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        active_set=(),
        residual_tolerance=1e-6,
        reason="test_unverified",
    )
    result = run_pytorch_autograd(
        forward=bogus,
        spec=spec,
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        policy_weight=1.0,
        reference_weight=0.0,
    )
    assert result.available is False
    assert result.status == CapabilityStatus.UNAVAILABLE
    assert "unverified_forward" in result.reason

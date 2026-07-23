"""Schema validation tests for research artifacts."""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
from jsonschema import Draft202012Validator

from conicshield.experimental.assurance.bundle import AssuranceBundle
from conicshield.experimental.corpus.generate import load_all_scenarios
from conicshield.experimental.corpus.paths import SCHEMAS_DIR
from conicshield.experimental.domains.cbf_2d import AgentState2D, CircularObstacle
from conicshield.experimental.domains.cbf_rh import run_receding_horizon_filter
from conicshield.experimental.domains.stage4_gate import evaluate_stage4_gate
from conicshield.experimental.provenance import begin_experiment_provenance
from conicshield.experimental.solver_assurance.disagreement import SolverDisagreement


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def test_scenario_schema_accepts_corpus() -> None:
    validator = _validator("scenario.schema.json")
    for scenario in load_all_scenarios():
        validator.validate(scenario)


def test_disagreement_schema() -> None:
    validator = _validator("disagreement.schema.json")
    d = SolverDisagreement(
        status_disagreement=False,
        release_disagreement=False,
        corrected_action_l2=0.0,
        corrected_action_linf=0.0,
        objective_gap_abs=None,
        objective_gap_rel=None,
        equality_residual_gap=0.0,
        inequality_residual_gap=0.0,
        active_set_symmetric_difference=(),
        iteration_ratio=None,
        timeout_asymmetry=False,
        warm_cold_disagreement=None,
    )
    validator.validate(d.as_dict())


def test_assurance_and_provenance_schemas(sample_assurance_bundle: AssuranceBundle) -> None:
    _validator("assurance_bundle.schema.json").validate(sample_assurance_bundle.as_dict())
    prov = begin_experiment_provenance(
        scenario_corpus_version="r0-v0.1.0",
        backend="test",
        exact_command="pytest",
    )
    _validator("experiment_provenance.schema.json").validate(prov.as_dict())


def test_schema_files_exist() -> None:
    for name in (
        "scenario.schema.json",
        "assurance_bundle.schema.json",
        "experiment_provenance.schema.json",
        "disagreement.schema.json",
        "sampling_study.schema.json",
        "cbf_receding_horizon.schema.json",
        "cbf_stage4_gate.schema.json",
        "cbf_infeasibility_audit.schema.json",
        "cbf_held_out_corpus.schema.json",
    ):
        assert (SCHEMAS_DIR / name).is_file()


def test_cbf_rh_and_stage4_gate_schemas() -> None:
    gate = evaluate_stage4_gate()
    _validator("cbf_stage4_gate.schema.json").validate(gate.as_dict())
    fake_green = SimpleNamespace(
        as_dict=lambda: {
            "stage4_status": "experimental_rh_available",
            "unblock_allowed": True,
            "all_required_passed": True,
            "passed_count": 6,
            "required_count": 6,
        }
    )
    rh = run_receding_horizon_filter(
        AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]), "schema_a0"),
        CircularObstacle(np.array([1.2, 0.0]), 0.5, "schema_o0"),
        horizon=3,
        require_stage4_checklist_green=True,
        gate_evaluation=fake_green,
        compare_baselines=False,
    )
    _validator("cbf_receding_horizon.schema.json").validate(rh.as_dict())


def test_sampling_study_schema_shape() -> None:
    validator = _validator("sampling_study.schema.json")
    sample = {
        "schema_id": "research.sampling_study.v0",
        "corpus_version": "r0-v0.2.0",
        "primary_backend": "cvxpy_clarabel",
        "shadow_backend": "cvxpy_scs",
        "results": [
            {
                "policy": "residual",
                "budget_fraction": 0.5,
                "shadowed_count": 9,
                "scenario_count": 18,
                "shadow_cost_relative": 0.5,
                "detection_rate": 1.0,
                "false_skip_rate": 0.0,
            }
        ],
        "promotion_gate": "test",
    }
    validator.validate(sample)

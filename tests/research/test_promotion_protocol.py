"""Candidate-stack promotion protocol tests."""

from __future__ import annotations

from pathlib import Path

from conicshield.experimental.solver_assurance.promotion_protocol import (
    PROMOTION_PROTOCOL_SCHEMA_ID,
    run_candidate_stack_promotion,
)


def test_candidate_stack_promotion_runs(tmp_path: Path) -> None:
    protocol = run_candidate_stack_promotion(
        output_dir=tmp_path,
        exact_command="pytest:test_candidate_stack_promotion_runs",
    )
    assert protocol.as_dict()["schema_id"] == PROMOTION_PROTOCOL_SCHEMA_ID
    required = set(protocol.metrics_required)
    assert required <= set(protocol.results.keys())
    assert "disagreement_frequency" in protocol.results
    assert "action_difference_distribution" in protocol.results
    assert "affected_scenario_families" in protocol.results
    assert (tmp_path / "candidate_stack_promotion.json").is_file()

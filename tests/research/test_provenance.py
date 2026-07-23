"""Provenance recorder tests."""

from __future__ import annotations

from conicshield.experimental.provenance import (
    begin_experiment_provenance,
    finalize_experiment_provenance,
)


def test_provenance_required_fields() -> None:
    prov = begin_experiment_provenance(
        scenario_corpus_version="r0-v0.3.0",
        backend="cvxpy_clarabel",
        exact_command="pytest tests/research/test_provenance.py",
        random_seeds={"a": 1},
        tolerances={"rtol": 1e-6},
    )
    data = prov.as_dict()
    for key in (
        "repository_commit",
        "dirty_worktree",
        "scenario_corpus_version",
        "python_version",
        "operating_system",
        "backend",
        "solver_settings",
        "random_seeds",
        "tolerances",
        "exact_command",
        "start_time_utc",
    ):
        assert key in data
    finalize_experiment_provenance(prov)
    assert prov.completion_time_utc is not None
    from conicshield.experimental.provenance import audit_provenance_completeness

    audit = audit_provenance_completeness(prov)
    assert audit["complete"] is True
    assert not audit["missing_keys"]

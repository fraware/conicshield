"""Corpus integrity and regeneration tests."""

from __future__ import annotations

from conicshield.experimental.corpus.generate import load_all_scenarios, load_manifest
from conicshield.experimental.corpus.paths import CORPUS_VERSION, SCENARIO_FAMILIES
from conicshield.experimental.corpus.validate import validate_corpus


def test_corpus_integrity() -> None:
    errors = validate_corpus(regenerate_check=True)
    assert errors == [], errors


def test_all_required_families_present() -> None:
    scenarios = load_all_scenarios()
    families = {s["family"] for s in scenarios}
    assert set(SCENARIO_FAMILIES) <= families


def test_active_set_trajectories_cover_constraint_families() -> None:
    scenarios = [s for s in load_all_scenarios() if s["family"] == "active_set_transition_neighborhoods"]
    families = {(s.get("extras") or {}).get("constraint_family") for s in scenarios}
    assert {"box", "rate", "turn_feasibility"} <= families
    assert len(scenarios) >= 15


def test_soft_load_infeasible_regime() -> None:
    from conicshield.experimental.corpus.spec_load import load_research_safety_spec

    scenario = next(s for s in load_all_scenarios() if s["family"] == "infeasible")
    spec, meta = load_research_safety_spec(scenario)
    assert meta["soft_load"] is True
    assert spec.action_dim == 4


def test_manifest_version() -> None:
    manifest = load_manifest()
    assert manifest["corpus_version"] == CORPUS_VERSION
    assert manifest["scenario_count"] == len(load_all_scenarios())
    assert CORPUS_VERSION.startswith("r0-v0.3")

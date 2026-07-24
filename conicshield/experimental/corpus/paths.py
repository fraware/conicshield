"""Corpus paths and version constants for Track 2 R0."""

from __future__ import annotations

from pathlib import Path

CORPUS_VERSION = "r0-v0.4.0"
CORPUS_FAMILY_ID = "research.solver_assurance.r0"

# research/solver-assurance-and-gradients/
RESEARCH_ROOT = Path(__file__).resolve().parents[3] / "research" / "solver-assurance-and-gradients"
CORPUS_ROOT = RESEARCH_ROOT / "corpus"
SCENARIOS_DIR = CORPUS_ROOT / "scenarios"
MANIFEST_PATH = CORPUS_ROOT / "manifest.json"
VERSION_PATH = CORPUS_ROOT / "VERSION"
SCHEMAS_DIR = RESEARCH_ROOT / "schemas"
SCENARIO_SCHEMA_PATH = SCHEMAS_DIR / "scenario.schema.json"

# Scenario families required by the directive
SCENARIO_FAMILIES: tuple[str, ...] = (
    "interior_feasible",
    "single_active_bound",
    "multiple_active_bounds",
    "simplex_corner",
    "rate_limited_transitions",
    "changing_admissibility_masks",
    "near_infeasible",
    "infeasible",
    "poorly_conditioned_objectives",
    "active_set_transition_neighborhoods",
    "solver_timeout_iteration_limit",
    "warm_start_success_failure",
    "heterogeneous_batches",
    "sidecar_interruption",
    "backend_version_changes",
    "consequential_disagreement_regimes",
)

"""JSON Schema contract for scripts/performance_benchmark.py output."""

from __future__ import annotations

import json

import jsonschema
import pytest

from tests._repo import repo_root

_SCHEMA = repo_root() / "schemas" / "performance_summary.schema.json"


def _validator() -> jsonschema.Draft202012Validator:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema)


def test_performance_summary_schema_file_exists() -> None:
    assert _SCHEMA.is_file()


def test_validate_minimal_empty_rows() -> None:
    sample = {
        "generated_at_utc": "2026-04-07T12:00:00Z",
        "repeats_config": 5,
        "rows": [],
        "errors": ["cvxpy: MOREAU not installed"],
        "cuda_claim_note": "test",
    }
    _validator().validate(sample)


def test_validate_sweep_mode_and_scenario_columns() -> None:
    sample = {
        "generated_at_utc": "2026-04-07T12:00:00Z",
        "repeats_config": 3,
        "sweep_mode": True,
        "shield_action_dims": [4, 8],
        "batch_sizes": [8],
        "sweep_auto_tune": False,
        "rows": [
            {
                "path": "cvxpy_moreau",
                "device": "cpu",
                "repeats": 3,
                "mean_sec": 0.01,
                "p50_sec": 0.009,
                "p95_sec": 0.02,
                "scenario_id": "n4_nominal_s0",
                "conditioning": "nominal",
                "action_dim": 4,
                "auto_tune": False,
            },
            {
                "path": "native_microbatch",
                "device": "cpu",
                "repeats": 2,
                "mean_sec": 0.02,
                "p50_sec": 0.019,
                "p95_sec": 0.021,
                "batch_size": 8,
                "mean_sec_per_solve": 0.0025,
                "scenario_id": "n4_nominal_batch8",
                "conditioning": "nominal",
                "action_dim": 4,
                "auto_tune": False,
            },
            {
                "path": "native_compiled_real_batch",
                "device": "cpu",
                "repeats": 2,
                "mean_sec": 0.015,
                "p50_sec": 0.014,
                "p95_sec": 0.016,
                "batch_size": 8,
                "mean_sec_per_solve": 0.001875,
                "scenario_id": "n4_nominal_batch8",
                "conditioning": "nominal",
                "action_dim": 4,
                "auto_tune": False,
            },
        ],
        "errors": [],
        "cuda_claim_note": "note",
    }
    _validator().validate(sample)


def test_validate_full_row_shapes() -> None:
    sample = {
        "generated_at_utc": "2026-04-07T12:00:00Z",
        "repeats_config": 5,
        "rows": [
            {
                "path": "cvxpy_moreau",
                "device": "cpu",
                "repeats": 5,
                "mean_sec": 0.01,
                "p50_sec": 0.009,
                "p95_sec": 0.02,
            },
            {
                "path": "native_cold",
                "device": "cpu",
                "repeats": 5,
                "mean_sec": 0.005,
                "p50_sec": 0.005,
                "p95_sec": 0.008,
            },
            {
                "path": "native_warm_sequence",
                "device": "cuda",
                "repeats": 5,
                "mean_sec": 0.01,
                "p50_sec": 0.01,
                "p95_sec": 0.012,
                "warm_start_speedup_vs_first": 1.2,
            },
        ],
        "errors": [],
        "cuda_claim_note": "note",
    }
    _validator().validate(sample)


def test_rejects_unknown_top_level_key() -> None:
    sample = {
        "generated_at_utc": "2026-04-07T12:00:00Z",
        "repeats_config": 5,
        "rows": [],
        "errors": [],
        "cuda_claim_note": "n",
        "extra": 1,
    }
    with pytest.raises(jsonschema.ValidationError):
        _validator().validate(sample)


def test_fixture_performance_summary_json_if_present() -> None:
    """When output/performance_summary.json exists (local vendor run), it must validate."""
    path = repo_root() / "output" / "performance_summary.json"
    if not path.is_file():
        pytest.skip("no output/performance_summary.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    _validator().validate(data)

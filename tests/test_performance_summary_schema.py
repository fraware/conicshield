"""JSON Schema contract for scripts/performance_benchmark.py output."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

_SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "performance_summary.schema.json"


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
    path = Path(__file__).resolve().parents[1] / "output" / "performance_summary.json"
    if not path.is_file():
        pytest.skip("no output/performance_summary.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    _validator().validate(data)

"""§7.1 artifact / bundle validation edge cases (malformed JSONL, config cross-refs)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from conicshield.artifacts.validator import (
    ArtifactValidationError,
    validate_run_bundle,
    validate_summary_records,
)


def _copy_valid_bundle(dest: Path) -> None:
    src = Path("tests/fixtures/parity_reference")
    dest.mkdir(parents=True, exist_ok=True)
    for name in [
        "config.json",
        "config.schema.json",
        "summary.json",
        "summary.schema.json",
        "episodes.jsonl",
        "episodes.schema.json",
        "transition_bank.json",
    ]:
        shutil.copy2(src / name, dest / name)


def test_jsonl_skips_empty_lines(tmp_path: Path) -> None:
    d = tmp_path / "run"
    _copy_valid_bundle(d)
    raw = (d / "episodes.jsonl").read_text(encoding="utf-8")
    lines = raw.splitlines()
    (d / "episodes.jsonl").write_text(lines[0] + "\n\n  \n" + "\n".join(lines[1:]) + "\n", encoding="utf-8")
    validate_run_bundle(d)


def test_jsonl_invalid_json_raises(tmp_path: Path) -> None:
    d = tmp_path / "run"
    _copy_valid_bundle(d)
    (d / "episodes.jsonl").write_text("{not json\n", encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="Invalid JSONL"):
        validate_run_bundle(d)


def test_jsonl_non_object_raises(tmp_path: Path) -> None:
    d = tmp_path / "run"
    _copy_valid_bundle(d)
    (d / "episodes.jsonl").write_text('["array"]\n', encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="JSON object"):
        validate_run_bundle(d)


def test_unknown_arm_label_raises(tmp_path: Path) -> None:
    d = tmp_path / "run"
    _copy_valid_bundle(d)
    line = (d / "episodes.jsonl").read_text(encoding="utf-8").splitlines()[0]
    ep = json.loads(line)
    ep["arm_label"] = "not-a-declared-arm"
    (d / "episodes.jsonl").write_text(json.dumps(ep) + "\n", encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="not declared"):
        validate_run_bundle(d)


def test_duplicate_episode_id_same_arm_raises(tmp_path: Path) -> None:
    d = tmp_path / "run"
    _copy_valid_bundle(d)
    lines = (d / "episodes.jsonl").read_text(encoding="utf-8").splitlines()
    dup = lines[0] + "\n" + lines[0] + "\n" + "\n".join(lines[1:]) + "\n"
    (d / "episodes.jsonl").write_text(dup, encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="Duplicate episode_id"):
        validate_run_bundle(d)


_BUNDLE_REQUIRED = [
    "config.json",
    "config.schema.json",
    "summary.json",
    "summary.schema.json",
    "episodes.jsonl",
    "episodes.schema.json",
    "transition_bank.json",
]


@pytest.mark.parametrize("omit", _BUNDLE_REQUIRED, ids=lambda x: x.replace(".", "_"))
def test_validate_run_bundle_missing_required_file(tmp_path: Path, omit: str) -> None:
    d = tmp_path / "run"
    _copy_valid_bundle(d)
    (d / omit).unlink()
    with pytest.raises(ArtifactValidationError, match="Missing required files"):
        validate_run_bundle(d)


def test_validate_run_bundle_summary_episodes_count_mismatch(tmp_path: Path) -> None:
    d = tmp_path / "run"
    _copy_valid_bundle(d)
    summ = json.loads((d / "summary.json").read_text(encoding="utf-8"))
    for row in summ:
        if row["label"] == "baseline-unshielded":
            row["episodes"] = 99
            break
    (d / "summary.json").write_text(json.dumps(summ, indent=2), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="episodes count mismatch"):
        validate_run_bundle(d)


def test_validate_run_bundle_summary_avg_reward_mismatch(tmp_path: Path) -> None:
    d = tmp_path / "run"
    _copy_valid_bundle(d)
    summ = json.loads((d / "summary.json").read_text(encoding="utf-8"))
    for row in summ:
        if row["label"] == "baseline-unshielded":
            row["avg_reward"] = float(row.get("avg_reward", 0.0)) + 999.0
            break
    (d / "summary.json").write_text(json.dumps(summ, indent=2), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="avg_reward mismatch"):
        validate_run_bundle(d)


def test_validate_summary_records_direct_missing_summaries_for_label() -> None:
    episodes = [
        {
            "arm_label": "arm-a",
            "episode_id": "x",
            "num_steps": 0,
            "steps": [],
            "num_interventions": 0,
            "total_reward": 0.0,
        }
    ]
    summaries: list[dict] = []
    with pytest.raises(ArtifactValidationError, match="Missing summaries for labels"):
        validate_summary_records(summaries, episodes)


def test_validate_run_bundle_transition_bank_invalid_schema(tmp_path: Path) -> None:
    d = tmp_path / "run"
    _copy_valid_bundle(d)
    (d / "transition_bank.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="transition_bank.json"):
        validate_run_bundle(d)

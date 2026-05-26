"""Host-realistic refresh cycle defaults and flagship targeting."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.host_realistic_refresh_cycle import (
    default_refresh_run_id,
    flagship_run_id,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_flagship_run_id_reads_current_published_bundle() -> None:
    repo = _root()
    rid = flagship_run_id(repo)
    assert rid == "host-realistic-20260525"
    assert (repo / "benchmarks" / "published_runs" / rid).is_dir()


def test_default_refresh_run_id_prefers_flagship() -> None:
    repo = _root()
    assert default_refresh_run_id(repo, new_milestone=False) == "host-realistic-20260525"


def test_default_refresh_run_id_new_milestone_is_dated() -> None:
    repo = _root()
    rid = default_refresh_run_id(repo, new_milestone=True)
    assert rid.startswith("host-realistic-")
    assert len(rid) == len("host-realistic-YYYYMMDD")


def test_flagship_run_id_missing_when_current_points_at_missing_bundle(tmp_path: Path) -> None:
    rel = tmp_path / "benchmarks" / "releases" / "conicshield-transition-bank-v1"
    rel.mkdir(parents=True)
    (rel / "CURRENT.json").write_text(
        json.dumps({"current_run_id": "does-not-exist-on-disk"}),
        encoding="utf-8",
    )
    assert flagship_run_id(tmp_path) is None

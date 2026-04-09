from __future__ import annotations

from pathlib import Path

import pytest

from conicshield.benchmark_paths import resolve_run_directory


def test_resolve_run_directory_prefers_published(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    rid = "run-xyz"
    pub = tmp_path / "benchmarks" / "published_runs" / rid
    pub.mkdir(parents=True)
    (pub / "config.json").write_text("{}", encoding="utf-8")
    ephem = tmp_path / "benchmarks" / "runs" / rid
    ephem.mkdir(parents=True)
    (ephem / "config.json").write_text('{"ephemeral": true}', encoding="utf-8")

    resolved = resolve_run_directory(rid)
    assert resolved.resolve() == pub.resolve()
    assert "ephemeral" not in (resolved / "config.json").read_text(encoding="utf-8")


def test_resolve_run_directory_falls_back_to_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    rid = "run-abc"
    ephem = tmp_path / "benchmarks" / "runs" / rid
    ephem.mkdir(parents=True)
    (ephem / "marker.txt").write_text("1", encoding="utf-8")

    resolved = resolve_run_directory(rid)
    assert resolved.resolve() == ephem.resolve()

"""§7.1 governance: validate_release_directory required files and manifest schema."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from conicshield.governance.family_manifest import FamilyManifestError
from conicshield.governance.release_validator import ReleaseDirectoryError, validate_release_directory
from tests._repo import repo_root

_REPO = repo_root()


def _minimal_release_dir(tmp: Path, family_id: str, *, include_manifest: bool) -> Path:
    rel = tmp / "benchmarks" / "releases" / family_id
    rel.mkdir(parents=True)
    shutil.copy2(
        _REPO / "benchmarks/releases/conicshield-transition-bank-v1/FAMILY_MANIFEST.schema.json",
        rel / "FAMILY_MANIFEST.schema.json",
    )
    (rel / "CURRENT.json").write_text(
        json.dumps(
            {
                "family_id": family_id,
                "task_contract_version": "v1",
                "fixture_version": "fixture-v1",
                "current_run_id": None,
                "state": "uninitialized",
                "publishable_arms": [],
                "artifact_gate": "unknown",
                "parity_gate": "unknown",
                "promotion_gate": "unknown",
                "published_at_utc": None,
                "notes": "",
            }
        ),
        encoding="utf-8",
    )
    (rel / "HISTORY.json").write_text(json.dumps({"family_id": family_id, "entries": []}), encoding="utf-8")
    if include_manifest:
        base = json.loads(
            (_REPO / "benchmarks/releases/conicshield-transition-bank-v1/FAMILY_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        base["family_id"] = family_id
        base["benchmark_name"] = f"Hermetic {family_id}"
        (rel / "FAMILY_MANIFEST.json").write_text(json.dumps(base, indent=2), encoding="utf-8")
    return rel


def test_validate_release_directory_missing_manifest(tmp_path: Path) -> None:
    _minimal_release_dir(tmp_path, "rel-missing-manifest", include_manifest=False)
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        with pytest.raises(ReleaseDirectoryError, match="Missing required release-directory files"):
            validate_release_directory("rel-missing-manifest")
    finally:
        os.chdir(cwd)


def test_validate_release_directory_invalid_manifest(tmp_path: Path) -> None:
    rel = _minimal_release_dir(tmp_path, "rel-bad-manifest", include_manifest=True)
    bad = json.loads((rel / "FAMILY_MANIFEST.json").read_text(encoding="utf-8"))
    bad.pop("required_arms", None)
    (rel / "FAMILY_MANIFEST.json").write_text(json.dumps(bad), encoding="utf-8")
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        with pytest.raises(FamilyManifestError, match="Invalid family manifest"):
            validate_release_directory("rel-bad-manifest")
    finally:
        os.chdir(cwd)

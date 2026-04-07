"""§7.1 governance: hermetic finalize→publish; audit detects registry vs CURRENT skew."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from conicshield.governance.finalize import FinalizationInputs, finalize_run
from conicshield.governance.publish import publish_from_governance_status

_REPO = Path(__file__).resolve().parents[1]


def _copy_parity_run(src: Path, dest: Path) -> None:
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
        (dest / name).write_text((src / name).read_text(encoding="utf-8"), encoding="utf-8")


def _summary_with_promotion_passing(src: Path) -> list[dict]:
    rows: list[dict] = json.loads((src / "summary.json").read_text(encoding="utf-8"))
    for row in rows:
        if row["label"] in ("shielded-rules-only", "shielded-rules-plus-geometry"):
            row["reward_retention_vs_baseline"] = 1.0
    return rows


def _seed_hermetic_family(tmp: Path, family_id: str) -> None:
    rel = tmp / "benchmarks" / "releases" / family_id
    rel.mkdir(parents=True)
    shutil.copy2(
        _REPO / "benchmarks/releases/conicshield-transition-bank-v1/FAMILY_MANIFEST.schema.json",
        rel / "FAMILY_MANIFEST.schema.json",
    )
    base_manifest = json.loads(
        (_REPO / "benchmarks/releases/conicshield-transition-bank-v1/FAMILY_MANIFEST.json").read_text(encoding="utf-8")
    )
    base_manifest["family_id"] = family_id
    base_manifest["benchmark_name"] = f"Hermetic {family_id}"
    (rel / "FAMILY_MANIFEST.json").write_text(json.dumps(base_manifest, indent=2), encoding="utf-8")
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
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (rel / "HISTORY.json").write_text(
        json.dumps({"family_id": family_id, "entries": []}, indent=2),
        encoding="utf-8",
    )

    reg = tmp / "benchmarks" / "registry.json"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(
        json.dumps(
            {
                "benchmark_families": [
                    {
                        "family_id": family_id,
                        "status": "active",
                        "task_contract_version": "v1",
                        "current_fixture_version": "fixture-v1",
                        "current_run_id": None,
                        "published_at_utc": None,
                        "history": [],
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_finalize_and_publish_hermetic_updates_current_history_registry(tmp_path: Path) -> None:
    family_id = "hermetic-fam-v1"
    _seed_hermetic_family(tmp_path, family_id)
    src = _REPO / "tests/fixtures/parity_reference"
    run_dir = tmp_path / "benchmarks" / "runs" / "hermetic-001"
    _copy_parity_run(src, run_dir)
    (run_dir / "summary.json").write_text(
        json.dumps(_summary_with_promotion_passing(src), indent=2),
        encoding="utf-8",
    )

    current_path = tmp_path / "benchmarks" / "releases" / family_id / "CURRENT.json"
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        status = finalize_run(
            FinalizationInputs(
                run_dir=run_dir,
                family_id=family_id,
                task_contract_version="v1",
                fixture_version="fixture-v1",
                reference_fixture_dir=src,
                parity_summary_path=None,
                current_release_path=current_path,
            )
        )
        assert status["state"] == "review-locked"
        (run_dir / "governance_decision.md").write_text("hermetic publish chain", encoding="utf-8")
        publish_from_governance_status(run_dir=run_dir, reason="hermetic e2e")

        current = json.loads(current_path.read_text(encoding="utf-8"))
        registry = json.loads((tmp_path / "benchmarks" / "registry.json").read_text(encoding="utf-8"))
        fam = registry["benchmark_families"][0]
        assert fam["current_run_id"] == current["current_run_id"] == "hermetic-001"
        assert fam["task_contract_version"] == current["task_contract_version"]
        assert fam["current_fixture_version"] == current["fixture_version"]

        history = json.loads(
            (tmp_path / "benchmarks" / "releases" / family_id / "HISTORY.json").read_text(encoding="utf-8")
        )
        assert any(e.get("run_id") == "hermetic-001" and e.get("status") == "published" for e in history["entries"])
    finally:
        os.chdir(cwd)


def test_audit_cli_strict_fails_on_registry_current_run_id_skew(tmp_path: Path) -> None:
    family_id = "skew-audit-fam"
    _seed_hermetic_family(tmp_path, family_id)
    current_path = tmp_path / "benchmarks" / "releases" / family_id / "CURRENT.json"
    cur = json.loads(current_path.read_text(encoding="utf-8"))
    cur["current_run_id"] = "run-b"
    current_path.write_text(json.dumps(cur, indent=2), encoding="utf-8")

    reg_path = tmp_path / "benchmarks" / "registry.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    reg["benchmark_families"][0]["current_run_id"] = "run-a"
    reg_path.write_text(json.dumps(reg, indent=2), encoding="utf-8")

    env = {**os.environ, "PYTHONPATH": str(_REPO)}
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "conicshield.governance.audit_cli",
            "--strict",
            "--family-id",
            family_id,
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "current_run_id" in proc.stdout or "current_run_id" in proc.stderr

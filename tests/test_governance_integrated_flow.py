from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from conicshield.governance.audit import audit_benchmark_tree
from conicshield.governance.finalize import FinalizationInputs, finalize_run
from conicshield.governance.release import decide_release_mode


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


def test_finalize_release_dry_run_and_strict_audit(tmp_path: Path) -> None:
    src = Path("tests/fixtures/parity_reference")
    run_dir = tmp_path / "governed_run"
    _copy_parity_run(src, run_dir)
    (run_dir / "summary.json").write_text(
        json.dumps(_summary_with_promotion_passing(src), indent=2),
        encoding="utf-8",
    )

    current_release = Path("benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json")
    status = finalize_run(
        FinalizationInputs(
            run_dir=run_dir,
            family_id="conicshield-transition-bank-v1",
            task_contract_version="v1",
            fixture_version="fixture-v1",
            reference_fixture_dir=src,
            parity_summary_path=None,
            current_release_path=current_release,
        )
    )
    assert status["state"] == "review-locked"
    assert status["promotion_gate"] == "green"

    decision = decide_release_mode(run_dir=run_dir, family_id="conicshield-transition-bank-v1")
    assert decision.mode == "same-family"

    repo = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(repo)}
    dry = subprocess.run(
        [
            sys.executable,
            "-m",
            "conicshield.governance.release_cli",
            "--run-dir",
            str(run_dir),
            "--family-id",
            "conicshield-transition-bank-v1",
            "--reason",
            "integration test dry-run",
            "--dry-run",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert dry.returncode == 0, dry.stderr + dry.stdout

    audit = subprocess.run(
        [sys.executable, "-m", "conicshield.governance.audit_cli", "--strict"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert audit.returncode == 0, audit.stderr + audit.stdout

    report = audit_benchmark_tree(family_id="conicshield-transition-bank-v1")
    assert report.ok
    assert not any(i["level"] == "error" for i in report.as_dict()["issues"])

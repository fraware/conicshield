#!/usr/bin/env python3
"""Repeatable host-realistic refresh: export → publish → parity → finalize → optional release → index.

See CONTRIBUTING.md and make host-realistic-refresh-cycle-licensed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

_FAMILY_ID = "conicshield-transition-bank-v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def flagship_run_id(repo: Path) -> str | None:
    """Family ``current_run_id`` when its published bundle exists on disk."""
    current_path = repo / "benchmarks" / "releases" / _FAMILY_ID / "CURRENT.json"
    if not current_path.is_file():
        return None
    run_id = json.loads(current_path.read_text(encoding="utf-8")).get("current_run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        return None
    if (repo / "benchmarks" / "published_runs" / run_id).is_dir():
        return run_id
    return None


def default_refresh_run_id(repo: Path, *, new_milestone: bool) -> str:
    if new_milestone:
        return f"host-realistic-{datetime.now(UTC).strftime('%Y%m%d')}"
    return flagship_run_id(repo) or f"host-realistic-{datetime.now(UTC).strftime('%Y%m%d')}"


def _run(cmd: list[str], *, cwd: Path) -> int:
    print("Running:", " ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd, cwd=str(cwd))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Published run id (default: family current_run_id when published, else dated milestone).",
    )
    p.add_argument(
        "--new-milestone",
        action="store_true",
        help="Use host-realistic-YYYYMMDD even when a flagship current_run_id exists.",
    )
    p.add_argument(
        "--skip-vendor-verify",
        action="store_true",
        help="Skip performance sweep and batch acceptance (governance-only refresh).",
    )
    p.add_argument(
        "--live-graph-json",
        type=Path,
        default=None,
        help="Replace committed export from live inter-sim dump before publish.",
    )
    p.add_argument(
        "--export-json",
        type=Path,
        default=None,
        help="Export JSON (default: benchmarks/external_evidence/offline_graph_export_upstream.json).",
    )
    p.add_argument(
        "--promote-release",
        action="store_true",
        help="Run release_cli after publish (requires approved governance_decision.md).",
    )
    p.add_argument(
        "--governance-only",
        action="store_true",
        help="Only refresh parity/finalize on existing benchmarks/runs/<run_id> (no bundle rebuild).",
    )
    p.add_argument("--force", action="store_true")
    p.add_argument(
        "--trigger",
        type=str,
        default="manual",
        help="Cadence trigger label for record_reference_refresh (e.g. calendar-cadence).",
    )
    p.add_argument(
        "--record-refresh",
        action="store_true",
        help="Append reference_refresh_log + EXPORT_PROVENANCE.refresh_history after success.",
    )
    p.add_argument(
        "--amend-last-refresh",
        action="store_true",
        help="With --record-refresh: update the latest log row (e.g. after export-only refresh).",
    )
    args = p.parse_args()

    repo = _repo_root()
    run_id = args.run_id or default_refresh_run_id(repo, new_milestone=args.new_milestone)
    print(f"Refresh target run_id={run_id}", file=sys.stderr)
    export = args.export_json or (
        repo / "benchmarks" / "external_evidence" / "offline_graph_export_upstream.json"
    )

    if args.live_graph_json is not None:
        rc = _run(
            [
                sys.executable,
                str(repo / "scripts" / "refresh_live_upstream_export.py"),
                "--graph-json",
                str(args.live_graph_json),
            ],
            cwd=repo,
        )
        if rc != 0:
            return rc

    if args.governance_only:
        cmd = [
            sys.executable,
            str(repo / "scripts" / "upgrade_host_realistic_vendor.py"),
            "--run-id",
            run_id,
            "--refresh-governance",
        ]
        return _run(cmd, cwd=repo)

    cmd = [
        sys.executable,
        str(repo / "scripts" / "run_host_realistic_publish.py"),
        "--export-json",
        str(export),
        "--run-id",
        run_id,
        "--no-passthrough",
        "--include-native-arm",
        "--governance-scaffold",
        "--copy-to-published",
        "--refresh-index",
    ]
    if args.force:
        cmd.append("--force")
    rc = _run(cmd, cwd=repo)
    if rc != 0:
        return rc

    published = repo / "benchmarks" / "published_runs" / run_id
    gdec = published / "governance_decision.md"
    runs_gdec = repo / "benchmarks" / "runs" / run_id / "governance_decision.md"
    if gdec.is_file() and "approve" in gdec.read_text(encoding="utf-8").lower():
        runs_gdec.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(gdec, runs_gdec)

    current_run_id = flagship_run_id(repo)
    sync_release = args.promote_release or current_run_id == run_id
    if sync_release:
        gdec = published / "governance_decision.md"
        if not gdec.is_file() or "approve" not in gdec.read_text(encoding="utf-8").lower():
            print(
                f"Refusing release sync: complete and approve {gdec} first.",
                file=sys.stderr,
            )
            return 2
        rc = _run(
            [
                sys.executable,
                "-m",
                "conicshield.governance.release_cli",
                "--run-dir",
                str(published),
                "--family-id",
                _FAMILY_ID,
                "--reason",
                f"Host-realistic refresh cycle {run_id}",
            ],
            cwd=repo,
        )
        if rc != 0:
            return rc
        rc = _run([sys.executable, "-m", "conicshield.governance.audit_cli", "--strict"], cwd=repo)
        if rc != 0:
            return rc

    if not args.governance_only and not args.skip_vendor_verify:
        vdir = repo / "output" / "host_realistic_refresh_verify"
        rc = _run(
            [
                sys.executable,
                str(repo / "scripts" / "performance_benchmark.py"),
                "--out-dir",
                str(vdir),
                "--repeats",
                "5",
                "--sweep",
                "--batch-sizes",
                "4,8,16",
            ],
            cwd=repo,
        )
        if rc != 0:
            return rc
        rc = _run(
            [
                sys.executable,
                str(repo / "scripts" / "batch_solve_report.py"),
                "--input",
                str(vdir / "performance_summary.json"),
                "--out",
                str(vdir / "batch_solve_report.json"),
            ],
            cwd=repo,
        )
        if rc != 0:
            return rc
        latest = repo / "benchmarks" / "reports" / "batch_solve_report.latest.json"
        latest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(vdir / "batch_solve_report.json", latest)
        rc = _run(
            [
                sys.executable,
                str(repo / "scripts" / "check_batch_acceptance.py"),
                "--tier",
                "viability",
                "--report",
                str(vdir / "batch_solve_report.json"),
            ],
            cwd=repo,
        )
        if rc != 0:
            return rc

    rc = _run([sys.executable, str(repo / "scripts" / "finalize_community_dataset.py")], cwd=repo)
    if rc != 0:
        return rc
    for script in (
        "scripts/generate_reference_authority_snapshot.py",
        "scripts/generate_reference_system_status.py",
    ):
        rc = _run([sys.executable, str(repo / script)], cwd=repo)
        if rc != 0:
            return rc

    rc = _run([sys.executable, str(repo / "scripts" / "reference_authority_check.py")], cwd=repo)
    if rc != 0:
        return rc

    _run([sys.executable, str(repo / "scripts" / "update_engineering_status_from_flagship.py")], cwd=repo)

    if args.record_refresh:
        workflow = "live-export-full" if not args.skip_vendor_verify else "live-export"
        cmd = [
            sys.executable,
            str(repo / "scripts" / "record_reference_refresh.py"),
            "--trigger",
            args.trigger,
            "--workflow",
            workflow,
            "--authority-ok",
            "--notes",
            f"host-realistic-refresh-cycle {run_id}",
        ]
        if args.amend_last_refresh:
            cmd.append("--amend-last")
        rc = _run(cmd, cwd=repo)
        if rc != 0:
            return rc

    print(
        f"\nRefresh cycle complete for {run_id}. "
        "Commit published_runs/, PUBLISHED_RUN_INDEX.json, reports/, benchmarks/reports/reference_refresh_log.md.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

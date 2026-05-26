#!/usr/bin/env python3
"""Repeatable host-realistic refresh: export → publish → parity → finalize → optional release → index.

See docs/HOST_REALISTIC_REFRESH_PROCEDURE.md.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run(cmd: list[str], *, cwd: Path) -> int:
    print("Running:", " ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd, cwd=str(cwd))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Published run id (default: host-realistic-YYYYMMDD from UTC date).",
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
    args = p.parse_args()

    repo = _repo_root()
    run_id = args.run_id or f"host-realistic-{datetime.now(UTC).strftime('%Y%m%d')}"
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
    if args.promote_release:
        gdec = published / "governance_decision.md"
        if not gdec.is_file() or "approve" not in gdec.read_text(encoding="utf-8").lower():
            print(
                f"Refusing --promote-release: complete and approve {gdec} first.",
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
                "conicshield-transition-bank-v1",
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

    for script in (
        "scripts/refresh_published_run_index.py",
        "scripts/generate_reference_authority_snapshot.py",
        "scripts/sync_published_run_readmes.py",
    ):
        rc = _run([sys.executable, str(repo / script)], cwd=repo)
        if rc != 0:
            return rc

    print(
        f"\nRefresh cycle complete for {run_id}. "
        "Commit published_runs/, PUBLISHED_RUN_INDEX.json, reports/.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

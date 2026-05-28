#!/usr/bin/env python3
"""Canonical native-arm publish entry: reference bundle + governed promotion hints.

Does not replace ``finalize_cli`` / ``release_cli`` / human ``governance_decision.md``.
See CONTRIBUTING.md.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser(description="Produce native-arm reference bundle (licensed host).")
    p.add_argument("--export-json", type=Path, required=True)
    p.add_argument("--run-id", type=str, required=True)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    repo = _repo_root()
    host_script = repo / "scripts" / "run_host_realistic_publish.py"
    cmd = [
        sys.executable,
        str(host_script),
        "--export-json",
        str(args.export_json),
        "--run-id",
        args.run_id,
        "--no-passthrough",
        "--include-native-arm",
        "--seed",
        str(args.seed),
    ]
    if args.force:
        cmd.append("--force")
    print("Running:", " ".join(cmd), file=sys.stderr)
    rc = subprocess.call(cmd, cwd=str(repo))
    if rc != 0:
        return rc

    runs_dir = repo / "benchmarks" / "runs" / args.run_id
    promo = [
        sys.executable,
        str(repo / "scripts" / "governed_local_promotion.py"),
        "all",
        "--source",
        str(runs_dir),
    ]
    print("Running:", " ".join(promo), file=sys.stderr)
    rc = subprocess.call(promo, cwd=str(repo))
    if rc != 0:
        return rc

    print(
        "\nNative-arm publish checklist:\n"
        "  1. Parity CLI → parity_summary.json\n"
        "  2. finalize_cli --parity-summary-path ...\n"
        "  3. Copy to benchmarks/published_runs/<run_id>/ + governance_decision.md\n"
        "  4. release_cli → audit_cli --strict\n"
        "  5. python scripts/refresh_published_run_index.py\n"
        "See CONTRIBUTING.md",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

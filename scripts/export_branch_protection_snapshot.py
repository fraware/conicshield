#!/usr/bin/env python3
"""Write remote main branch protection snapshot for audit trail."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from audit_branch_protection_api import _fetch_protection, _github_repo, _required_contexts  # noqa: E402


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Default: benchmarks/reports/branch_protection_remote_snapshot.json",
    )
    args = p.parse_args()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("No GITHUB_TOKEN", file=sys.stderr)
        return 2
    owner, repo = _github_repo()
    if not owner:
        print("GITHUB_REPOSITORY not set", file=sys.stderr)
        return 2
    protection = _fetch_protection(owner=owner, repo=repo, token=token)
    root = _repo_root()
    out = args.out or (root / "benchmarks" / "reports" / "branch_protection_remote_snapshot.json")
    payload = {
        "schema_version": "conicshield_branch_protection_remote_snapshot/v1",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repository": f"{owner}/{repo}",
        "branch": "main",
        "configured": protection is not None,
        "required_contexts": sorted(_required_contexts(protection)) if protection else [],
        "raw": protection,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(out)
    return 0 if protection else 1


if __name__ == "__main__":
    raise SystemExit(main())

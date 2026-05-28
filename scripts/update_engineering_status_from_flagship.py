#!/usr/bin/env python3
"""Refresh solver version rows in docs/ENGINEERING_STATUS.md from flagship solver_versions.json."""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = _repo_root()
    flagship = "host-realistic-20260525"
    sv_path = root / "benchmarks" / "published_runs" / flagship / "solver_versions.json"
    status_path = root / "docs" / "ENGINEERING_STATUS.md"
    if not sv_path.is_file():
        print(f"Missing {sv_path}", file=sys.stderr)
        return 2
    versions = json.loads(sv_path.read_text(encoding="utf-8"))
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    text = status_path.read_text(encoding="utf-8")
    rows = []
    for pkg in ("moreau", "cvxpy", "cvxpylayers"):
        if pkg not in versions:
            continue
        rows.append(
            f"| `{pkg}` | `{versions[pkg]}` | {today} | "
            f"`benchmarks/published_runs/{flagship}/solver_versions.json` |"
        )
    table_body = "\n".join(rows)
    pattern = re.compile(
        r"(\| Package \| Version \| Date \(UTC\) \| Source \|\n\|[-| ]+\|\n)"
        r"([\s\S]*?)"
        r"(\n\n```bash)",
        re.MULTILINE,
    )
    if not pattern.search(text):
        print("ENGINEERING_STATUS.md table anchor not found", file=sys.stderr)
        return 2
    text = pattern.sub(rf"\1{table_body}\3", text, count=1)
    status_path.write_text(text, encoding="utf-8")
    print(status_path, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Update docs/ENGINEERING_STATUS.md solver table from solver_versions.json."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path


def _replace_row(text: str, package: str, version: str, date_utc: str) -> str:
    pattern = re.compile(
        rf"^\|\s*`{re.escape(package)}`\s*\|[^|]*\|[^|]*\|[^|]*\|$",
        re.MULTILINE,
    )
    repl = (
        f"| `{package}` | `{version}` | {date_utc} | "
        "Updated from vendor solver_versions.json |"
    )
    updated, count = pattern.subn(repl, text)
    if count != 1:
        raise RuntimeError(
            f"Could not uniquely update `{package}` row in ENGINEERING_STATUS.md"
        )
    return updated


def main() -> int:
    p = argparse.ArgumentParser(
        description="Patch ENGINEERING_STATUS.md with validated solver versions."
    )
    p.add_argument(
        "--solver-versions",
        type=Path,
        required=True,
        help="Path to solver_versions.json artifact.",
    )
    p.add_argument(
        "--engineering-status",
        type=Path,
        default=Path("docs/ENGINEERING_STATUS.md"),
        help="Path to docs/ENGINEERING_STATUS.md",
    )
    p.add_argument(
        "--date-utc",
        type=str,
        default=datetime.now(UTC).strftime("%Y-%m-%d"),
        help="Validation date (UTC) for the solver table.",
    )
    args = p.parse_args()
    versions = json.loads(args.solver_versions.read_text(encoding="utf-8"))
    for required in ("moreau", "cvxpy", "cvxpylayers"):
        if required not in versions or not str(versions[required]).strip():
            raise SystemExit(f"Missing `{required}` in {args.solver_versions}")
    text = args.engineering_status.read_text(encoding="utf-8")
    text = _replace_row(text, "moreau", str(versions["moreau"]), args.date_utc)
    text = _replace_row(text, "cvxpy", str(versions["cvxpy"]), args.date_utc)
    text = _replace_row(text, "cvxpylayers", str(versions["cvxpylayers"]), args.date_utc)
    args.engineering_status.write_text(text, encoding="utf-8")
    print(args.engineering_status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Scan external-facing docs/examples for banned oversell phrases."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Patterns stronger than PUBLIC_CLAIMS.md allows without qualification.
_BANNED: list[tuple[str, str]] = [
    (r"\buniversal(?:ly)?\s+faster\b", "universal speedup"),
    (r"\buniversal\s+batch\s+speedup\b", "universal batch speedup"),
    (r"\bproduction\s+shield\s+autograd\b", "production autograd product"),
    (r"\bmaps/session\s+navigation\s+graph\b", "Maps/session navigation claim"),
    (r"\bprogress/clearance\b", "progress/clearance (not implemented)"),
]

_SCAN_GLOBS = (
    "README.md",
    "docs/*.md",
    "examples/*.md",
    "examples/*.py",
    "benchmarks/published_runs/*/README.md",
)

_SKIP_PARTS = (
    "CHANGELOG.md",
    "PUBLIC_CLAIMS.md",
    "DIFFERENTIATION_PUBLIC_STANCE.md",
    "PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md",
    "QUICKSTART_",
    "CONTRIBUTING.md",
)


def _should_scan(path: Path) -> bool:
    if any(part in path.name for part in _SKIP_PARTS):
        return False
    if "PUBLIC_CLAIMS" in path.name or "DIFFERENTIATION_PUBLIC" in path.name:
        return False
    return True


def scan_repo(repo_root: Path) -> list[str]:
    failures: list[str] = []
    for pattern in _SCAN_GLOBS:
        for path in repo_root.glob(pattern):
            if not path.is_file() or not _should_scan(path):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for line_no, line in enumerate(text.splitlines(), start=1):
                low = line.lower()
                if any(
                    marker in low
                    for marker in (
                        "does not prove",
                        "does not claim",
                        "not claim",
                        "not a universal",
                        "not yet claimable",
                        "do not ",
                        "out of public",
                        "| not ",
                        "**not**",
                        "— not",
                        "without ",
                    )
                ):
                    continue
                if re.match(
                    r"^\s*-\s+(production shield|universal batch|claim of universal|full upstream maps|full maps|progress\s*/\s*clearance)",
                    line,
                    re.IGNORECASE,
                ):
                    continue
                if "| does not prove |" in low or "| does not |" in low:
                    continue
                for regex, label in _BANNED:
                    if re.search(regex, line, re.IGNORECASE):
                        rel = path.relative_to(repo_root).as_posix()
                        failures.append(f"{rel}:{line_no}: banned phrase ({label}): {line.strip()[:120]}")
    return failures


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    failures = scan_repo(root)
    if failures:
        print("public claim phrase check FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        print("See docs/PUBLIC_CLAIMS.md", file=sys.stderr)
        return 1
    print("public claim phrase check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

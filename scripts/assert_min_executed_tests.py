#!/usr/bin/env python3
"""Fail when a JUnit report shows fewer executed tests than required."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _count_executed(path: Path) -> tuple[int, int]:
    root = ET.parse(path).getroot()
    suites = list(root.iter("testsuite"))
    if not suites and root.tag == "testsuite":
        suites = [root]
    executed = 0
    skipped = 0
    for suite in suites:
        for case in suite.findall("testcase"):
            if case.find("skipped") is not None:
                skipped += 1
                continue
            executed += 1
    return executed, skipped


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--junit", type=Path, required=True)
    p.add_argument("--min-executed", type=int, required=True)
    p.add_argument("--label", default="pytest")
    args = p.parse_args()
    if not args.junit.is_file():
        print(f"ERROR: missing junit {args.junit}", file=sys.stderr)
        return 2
    executed, skipped = _count_executed(args.junit)
    print(f"{args.label}: executed={executed} skipped={skipped} min={args.min_executed}")
    if executed < args.min_executed:
        print(
            f"ERROR: {args.label} executed only {executed} test(s); "
            f"required minimum is {args.min_executed}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

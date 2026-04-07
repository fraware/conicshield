#!/usr/bin/env python3
"""Run the broadest pytest selection (all markers) with a clean addopts override.

Writes Moreau-related metrics to output/moreau_metrics.json (see tests/conftest.py).

Usage:
  python scripts/run_full_pytest.py [--junit-xml PATH] [--tb MODE] [extra pytest args...]
"""

from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--junit-xml", default=None, help="Write JUnit XML to this path")
    p.add_argument("--tb", default="no", help="Traceback style (default: no)")
    p.add_argument("rest", nargs=argparse.REMAINDER, help="Extra args after --")
    args = p.parse_args()

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "--override-ini",
        "addopts=-q --durations=20",
        "-m",
        "slow or not slow",
        f"--tb={args.tb}",
    ]
    if args.junit_xml:
        cmd.extend(["--junit-xml", args.junit_xml])
    if args.rest:
        cmd.extend(args.rest)
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())

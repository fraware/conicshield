#!/usr/bin/env python3
"""CLI for published benchmark bundles: list, show, verify."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from conicshield.published_runs import (
    get_current_run,
    list_runs,
    load_run,
    load_summary,
    verify_run,
)


def _cmd_list(_: argparse.Namespace) -> int:
    for entry in list_runs():
        print(entry.run_id)
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    bundle = load_run(args.run_id)
    summary = load_summary(args.run_id)
    payload = {
        "run_id": bundle.run_id,
        "path": str(bundle.path),
        "evidence_tier": (
            bundle.community.evidence_tier if bundle.community else None
        ),
        "governance_state": (bundle.governance_status or {}).get("state"),
        "publishable_arms": (bundle.governance_status or {}).get("publishable_arms"),
        "summary_labels": [r.label for r in summary],
    }
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    verify_run(args.run_id)
    print(f"OK integrity: {args.run_id}")
    return 0


def _cmd_current(args: argparse.Namespace) -> int:
    bundle = get_current_run(args.family_id)
    print(bundle.run_id)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List governed run ids").set_defaults(func=_cmd_list)

    show = sub.add_parser("show", help="Show bundle summary JSON")
    show.add_argument("run_id")
    show.set_defaults(func=_cmd_show)

    verify = sub.add_parser("verify", help="Verify index SHA-256 for run_id")
    verify.add_argument("run_id")
    verify.set_defaults(func=_cmd_verify)

    current = sub.add_parser("current", help="Print family current_run_id")
    current.add_argument("family_id", nargs="?", default="conicshield-transition-bank-v1")
    current.set_defaults(func=_cmd_current)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

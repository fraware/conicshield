#!/usr/bin/env python3
"""Emit a JSON summary of the trusted-only conic suite (CLARABEL/SCS; no vendor MOREAU).

Use for local or CI artifacts: per-case status, n, density, conditioning, family.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import cvxpy as cp
except ImportError as exc:  # pragma: no cover
    raise SystemExit("cvxpy is required: pip install cvxpy") from exc

from conicshield.reference_correctness.conic_suite import run_conic_suite_trusted_only


def _main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--profile",
        choices=("smoke", "standard", "stress"),
        default="standard",
        help="Suite profile (matches conic_suite.run_conic_suite_trusted_only).",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write JSON to this path (default: stdout only).",
    )
    args = p.parse_args()

    rows = run_conic_suite_trusted_only(cp, profile=args.profile)
    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile": args.profile,
        "trusted_solver_lane": True,
        "cases": rows,
        "summary": {
            "total": len(rows),
            "ok": sum(1 for r in rows if r.get("status") == "ok"),
            "failed": [r.get("case_id") for r in rows if r.get("status") != "ok"],
        },
    }
    text = json.dumps(payload, indent=2)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(args.out)
    else:
        print(text)
    return 0 if not payload["summary"]["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(_main())

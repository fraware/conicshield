from __future__ import annotations

import argparse
import json
from pathlib import Path

from conicshield.governance.audit import audit_benchmark_tree


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit benchmark governance tree.")
    parser.add_argument("--family-id", default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero on warnings as well as errors.")
    args = parser.parse_args()

    report = audit_benchmark_tree(family_id=args.family_id)
    payload = report.as_dict()

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2))

    has_error = any(issue["level"] == "error" for issue in payload["issues"])
    has_warning = any(issue["level"] == "warning" for issue in payload["issues"])

    if has_error:
        raise SystemExit(1)
    if args.strict and has_warning:
        raise SystemExit(2)

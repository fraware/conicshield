#!/usr/bin/env python3
"""Post-test gate for vendor CI (CS-SOLVER-003).

Fails when:
  - no vendor-marked tests executed
  - any required vendor test was skipped
  - expected native solve count is zero
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _parse_junit(path: Path) -> tuple[int, int, int, int, list[str]]:
    """Return (executed, skipped, failed, errors, skipped_vendor_names)."""
    root = ET.parse(path).getroot()
    # Support both <testsuites> and bare <testsuite>.
    suites = list(root.iter("testsuite"))
    if not suites and root.tag == "testsuite":
        suites = [root]

    executed = 0
    skipped = 0
    failed = 0
    errors = 0
    skipped_vendor: list[str] = []

    for suite in suites:
        for case in suite.findall("testcase"):
            name = f"{case.get('classname', '')}::{case.get('name', '')}"
            skip_el = case.find("skipped")
            fail_el = case.find("failure")
            err_el = case.find("error")
            if skip_el is not None:
                skipped += 1
                # Pytest junit often puts markers in classname path / properties absent;
                # treat any skipped case under vendor test paths as vendor-required.
                classname = (case.get("classname") or "").lower()
                nodename = (case.get("name") or "").lower()
                pathish = f"{classname}/{nodename}"
                if (
                    "vendor" in pathish
                    or "requires_moreau" in pathish
                    or "moreau" in pathish
                    or "native_moreau" in pathish
                    or "cvxpy_moreau" in pathish
                ):
                    reason = skip_el.get("message") or (skip_el.text or "") or "skipped"
                    skipped_vendor.append(f"{name}: {reason[:200]}")
                continue
            if fail_el is not None:
                failed += 1
                executed += 1
                continue
            if err_el is not None:
                errors += 1
                executed += 1
                continue
            executed += 1
    return executed, skipped, failed, errors, skipped_vendor


def _write_summary(
    *,
    executed: int,
    skipped: int,
    failed: int,
    errors: int,
    native_solves: int,
    skipped_vendor: list[str],
    summary_path: Path | None,
) -> None:
    lines = [
        "## Vendor CI evidence gate",
        "",
        f"- executed tests: **{executed}**",
        f"- skipped tests: **{skipped}**",
        f"- failed tests: **{failed}**",
        f"- error tests: **{errors}**",
        f"- native solves (mandatory evidence): **{native_solves}**",
        f"- skipped vendor-required tests: **{len(skipped_vendor)}**",
        "",
    ]
    if skipped_vendor:
        lines.append("### Skipped vendor tests")
        lines.append("")
        for row in skipped_vendor[:30]:
            lines.append(f"- `{row}`")
        lines.append("")
    text = "\n".join(lines)
    if summary_path is not None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with summary_path.open("a", encoding="utf-8") as fh:
            fh.write(text)
    print(text)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--junit", type=Path, required=True, help="Pytest JUnit XML path.")
    p.add_argument(
        "--native-evidence",
        type=Path,
        required=True,
        help="JSON from scripts/vendor_mandatory_native_solves.py.",
    )
    p.add_argument(
        "--min-executed",
        type=int,
        default=1,
        help="Minimum executed (non-skipped) vendor suite tests.",
    )
    p.add_argument(
        "--github-summary",
        type=Path,
        default=None,
        help="Append markdown summary (defaults to $GITHUB_STEP_SUMMARY when set).",
    )
    args = p.parse_args()

    if not args.junit.is_file():
        print(f"ERROR: missing junit file {args.junit}", file=sys.stderr)
        return 2
    if not args.native_evidence.is_file():
        print(f"ERROR: missing native evidence {args.native_evidence}", file=sys.stderr)
        return 2

    executed, skipped, failed, errors, skipped_vendor = _parse_junit(args.junit)
    evidence = json.loads(args.native_evidence.read_text(encoding="utf-8"))
    native_solves = int(evidence.get("native_solve_count") or 0)
    feasible_ok = bool(evidence.get("known_feasible_ok"))
    infeasible_ok = bool(evidence.get("known_infeasible_or_failure_policy_ok"))

    summary = args.github_summary
    if summary is None:
        import os

        env_sum = os.environ.get("GITHUB_STEP_SUMMARY")
        if env_sum:
            summary = Path(env_sum)

    _write_summary(
        executed=executed,
        skipped=skipped,
        failed=failed,
        errors=errors,
        native_solves=native_solves,
        skipped_vendor=skipped_vendor,
        summary_path=summary,
    )

    problems: list[str] = []
    if executed < args.min_executed:
        problems.append(
            f"no vendor test executed (executed={executed}, min={args.min_executed}); "
            "vendor CI must not pass via empty/skipped suites"
        )
    if skipped_vendor:
        problems.append(
            f"{len(skipped_vendor)} required vendor test(s) skipped under CONICSHIELD_VENDOR_REQUIRED"
        )
    if failed > 0 or errors > 0:
        problems.append(
            f"vendor suite reported failures/errors (failed={failed}, errors={errors}); "
            "evidence gate must not pass a red pytest run"
        )
    if native_solves <= 0 or not feasible_ok:
        problems.append(
            f"expected native solve count is zero or known-feasible failed "
            f"(native_solve_count={native_solves}, known_feasible_ok={feasible_ok})"
        )
    if not infeasible_ok:
        problems.append("known-infeasible / failure-policy mandatory check did not pass")

    if problems:
        for msg in problems:
            print(f"ERROR: {msg}", file=sys.stderr)
        return 1
    print("OK: vendor CI evidence gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

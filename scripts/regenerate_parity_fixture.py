from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    from conicshield.artifacts.validator import validate_run_bundle
    from conicshield.parity.fixture_policy import validate_fixture_policy

    parser = argparse.ArgumentParser(
        description=(
            "Copy a validated reference benchmark bundle into tests/fixtures/parity_reference. "
            "Run conicshield.bench.reference_run (without passthrough) on a licensed host first, "
            "or promote a known-good benchmarks/runs/<id> directory."
        )
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Directory that already passes validate_run_bundle (e.g. benchmarks/runs/<run_id>).",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("tests/fixtures/parity_reference"),
        help="Fixture directory to overwrite (default: tests/fixtures/parity_reference).",
    )
    args = parser.parse_args()

    validate_run_bundle(args.source)

    dest: Path = args.dest
    dest.mkdir(parents=True, exist_ok=True)

    sync_files = [
        "config.json",
        "summary.json",
        "episodes.jsonl",
        "transition_bank.json",
        "config.schema.json",
        "summary.schema.json",
        "episodes.schema.json",
        "FIXTURE_MANIFEST.json",
        "REGENERATION_NOTE.md",
    ]
    for name in sync_files:
        src = args.source / name
        if not src.exists():
            raise SystemExit(f"Missing {src}")
        shutil.copy2(src, dest / name)

    gov = args.source / "governance_status.json"
    gov_schema = args.source / "governance_status.schema.json"
    if gov.exists() and gov_schema.exists():
        shutil.copy2(gov, dest / "governance_status.json")
        shutil.copy2(gov_schema, dest / "governance_status.schema.json")

    validate_run_bundle(dest)
    validate_fixture_policy(dest)
    print(f"Fixture synced from {args.source} to {dest}")
    print("Update REGENERATION_NOTE.md per fixture policy before merging.")


if __name__ == "__main__":
    main()

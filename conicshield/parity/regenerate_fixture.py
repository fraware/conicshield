from __future__ import annotations

import argparse
from pathlib import Path

from conicshield.artifacts.validator import validate_run_bundle
from conicshield.parity.fixture_policy import validate_fixture_policy


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a manually regenerated parity fixture.")
    parser.add_argument("--reference-dir", type=Path, required=True)
    args = parser.parse_args()
    validate_run_bundle(args.reference_dir)
    validate_fixture_policy(args.reference_dir)
    print(f"Validated regenerated fixture: {args.reference_dir}")


if __name__ == "__main__":
    main()

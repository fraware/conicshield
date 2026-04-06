from __future__ import annotations

import argparse
from pathlib import Path

from conicshield.artifacts.validator import validate_run_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a benchmark run bundle.")
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    validate_run_bundle(args.run_dir)
    print(args.run_dir)


if __name__ == "__main__":
    main()

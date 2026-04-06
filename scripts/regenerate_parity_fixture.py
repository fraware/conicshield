from __future__ import annotations

from pathlib import Path

from conicshield.artifacts.validator import validate_run_bundle


def main() -> None:
    fixture_dir = Path("tests/fixtures/parity_reference")
    raise NotImplementedError("Wire this script to the known-good reference benchmark generator.")
    validate_run_bundle(fixture_dir)
    print(f"Regenerated and validated: {fixture_dir}")


if __name__ == "__main__":
    main()

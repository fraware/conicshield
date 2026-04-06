from __future__ import annotations

import argparse
from pathlib import Path

from conicshield.governance.finalize import FinalizationInputs, finalize_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize a benchmark run into governance_status.json.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--family-id", required=True)
    parser.add_argument("--task-contract-version", required=True)
    parser.add_argument("--fixture-version", required=True)
    parser.add_argument("--reference-fixture-dir", type=Path, default=None)
    parser.add_argument("--parity-summary-path", type=Path, default=None)
    parser.add_argument("--current-release-path", type=Path, default=None)
    args = parser.parse_args()

    status = finalize_run(
        FinalizationInputs(
            run_dir=args.run_dir,
            family_id=args.family_id,
            task_contract_version=args.task_contract_version,
            fixture_version=args.fixture_version,
            reference_fixture_dir=args.reference_fixture_dir,
            parity_summary_path=args.parity_summary_path,
            current_release_path=args.current_release_path,
        )
    )

    print(args.run_dir / "governance_status.json")
    print(status["state"])


if __name__ == "__main__":
    main()

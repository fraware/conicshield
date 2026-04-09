from __future__ import annotations

import argparse
from pathlib import Path

from conicshield.governance.finalize import (
    FinalizationInputs,
    finalize_run,
    sync_current_release_from_status,
)
from conicshield.governance.policy import GovernanceError


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Finalize a benchmark run into governance_status.json.",
    )
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--family-id", required=True)
    parser.add_argument("--task-contract-version", required=True)
    parser.add_argument("--fixture-version", required=True)
    parser.add_argument("--reference-fixture-dir", type=Path, default=None)
    parser.add_argument("--parity-summary-path", type=Path, default=None)
    parser.add_argument("--current-release-path", type=Path, default=None)
    parser.add_argument(
        "--sync-current-release",
        action="store_true",
        help=(
            "After finalizing, copy artifact/parity/promotion gates and publishable_arms "
            "from governance_status into --current-release-path when current_run_id matches "
            "this run. Does not modify HISTORY.json or benchmarks/registry.json "
            "(unlike release/publish)."
        ),
    )
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

    if args.sync_current_release:
        if args.current_release_path is None:
            raise SystemExit("--sync-current-release requires --current-release-path")
        try:
            sync_current_release_from_status(
                current_release_path=args.current_release_path,
                status=status,
            )
        except GovernanceError as exc:
            raise SystemExit(str(exc)) from exc

    print(args.run_dir / "governance_status.json")
    print(status["state"])


if __name__ == "__main__":
    main()

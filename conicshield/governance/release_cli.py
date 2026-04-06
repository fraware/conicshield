from __future__ import annotations

import argparse
from pathlib import Path

from conicshield.governance.release import decide_release_mode, release_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Release orchestration for governed benchmark runs.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--family-id", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--allow-family-bump", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        decision = decide_release_mode(run_dir=args.run_dir, family_id=args.family_id)
        print(decision.as_dict())
        return

    decision = release_run(
        run_dir=args.run_dir,
        family_id=args.family_id,
        reason=args.reason,
        allow_family_bump=args.allow_family_bump,
    )
    print(decision.as_dict())


if __name__ == "__main__":
    main()

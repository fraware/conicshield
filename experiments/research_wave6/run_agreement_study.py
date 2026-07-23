#!/usr/bin/env python3
"""Wave 6: corpus-wide (or CI-small) KKT ↔ FD agreement study."""

from __future__ import annotations

from pathlib import Path

from conicshield.experimental.gradients.agreement_study import run_agreement_study

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "research" / "wave6" / "agreement_study"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ci-small", action="store_true")
    parser.add_argument("--full", action="store_true", help="Full corpus (nightly)")
    args = parser.parse_args()
    ci_small = not args.full
    if args.ci_small:
        ci_small = True
    report = run_agreement_study(
        ci_small=ci_small,
        output_dir=OUT,
        exact_command="python experiments/research_wave6/run_agreement_study.py",
    )
    print(
        f"wrote {OUT} n={report.overall.get('n_scenarios')} "
        f"kkt_mean_rel={report.overall.get('kkt_mean_rel_fro')}"
    )


if __name__ == "__main__":
    main()

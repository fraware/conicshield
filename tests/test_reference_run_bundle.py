from __future__ import annotations

from pathlib import Path

from conicshield.artifacts.validator import validate_run_bundle
from conicshield.bench.reference_run import run_benchmark_bundle
from conicshield.bench.transition_bank import TransitionBank


def test_reference_run_writes_valid_bundle_passthrough(tmp_path: Path) -> None:
    bank_path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "parity_reference" / "transition_bank.json"
    bank = TransitionBank.from_json(bank_path)
    out = tmp_path / "run0"
    run_benchmark_bundle(
        out_dir=out,
        bank=bank,
        use_passthrough_projector=True,
        seed=7,
        include_native_arm=False,
        benchmark_name="pytest-tmp-bundle",
    )
    validate_run_bundle(out)

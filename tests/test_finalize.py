from pathlib import Path

from conicshield.governance.finalize import FinalizationInputs, finalize_run


def test_finalize_run_writes_governance_status(tmp_path) -> None:
    src = Path("tests/fixtures/parity_reference")
    run_dir = tmp_path / "run_fixture"
    run_dir.mkdir()
    for name in [
        "config.json",
        "config.schema.json",
        "summary.json",
        "summary.schema.json",
        "episodes.jsonl",
        "episodes.schema.json",
        "transition_bank.json",
    ]:
        (run_dir / name).write_text((src / name).read_text(encoding="utf-8"), encoding="utf-8")

    current_release = Path("benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json")

    status = finalize_run(
        FinalizationInputs(
            run_dir=run_dir,
            family_id="conicshield-transition-bank-v1",
            task_contract_version="v1",
            fixture_version="fixture-v1",
            reference_fixture_dir=src,
            parity_summary_path=None,
            current_release_path=current_release,
        )
    )
    assert (run_dir / "governance_status.json").exists()
    assert status["artifact_gate"] == "green"

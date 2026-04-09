from __future__ import annotations

from pathlib import Path


def test_parity_fixture_present() -> None:
    root = Path(__file__).resolve().parents[2]
    fixture = root / "tests" / "fixtures" / "parity_reference" / "episodes.jsonl"
    assert fixture.is_file()

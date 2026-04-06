from pathlib import Path

from conicshield.parity.fixture_policy import validate_fixture_policy


def test_fixture_policy_passes() -> None:
    validate_fixture_policy(Path("tests/fixtures/parity_reference"))

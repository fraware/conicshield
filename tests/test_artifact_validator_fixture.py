from pathlib import Path

from conicshield.artifacts.validator import validate_run_bundle
from conicshield.parity.fixture_policy import validate_fixture_policy


def test_reference_fixture_validates() -> None:
    ref = Path("tests/fixtures/parity_reference")
    validate_run_bundle(ref)
    validate_fixture_policy(ref)

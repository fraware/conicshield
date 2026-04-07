# Regeneration Note

## Why the fixture changed
- Initial synthetic frozen reference fixture for governance and parity tests.

## What changed in the reference path
- Nothing yet. This is the bootstrap fixture.

## Governed regeneration path

See [docs/PARITY_AND_FIXTURES.md](../../../docs/PARITY_AND_FIXTURES.md) for the full checklist. Summary:

1. Run a **validated** reference benchmark directory (e.g. `python -m conicshield.bench.reference_run` with the real solver, not `--passthrough-projector`, on a licensed host).
2. Confirm `python -m conicshield.artifacts.validator_cli --run-dir <dir>` passes (or equivalent `validate_run_bundle`).
3. Run `python scripts/regenerate_parity_fixture.py --source <dir>`.
4. Re-run `python -m conicshield.parity.regenerate_fixture --reference-dir tests/fixtures/parity_reference`.
5. Update this note with what changed and why.

## What did not change
- Reference arm remains `shielded-rules-plus-geometry`
- Reference backend remains `cvxpy_moreau`

## Expected effect on parity
- Native parity tests should use this fixture as the gold reference stream.

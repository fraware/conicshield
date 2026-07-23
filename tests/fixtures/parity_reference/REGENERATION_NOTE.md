# Regeneration Note

**Fixture status:** Promoted from a **committed governed bundle** in-repo. The parity gold stream is synced from `benchmarks/published_runs/wsl-real-20260409-132450/` (see `RUN_PROVENANCE.json` there and in this fixture).

## Why the fixture changed

- Regenerated via `scripts/regenerate_parity_fixture.py --source benchmarks/published_runs/wsl-real-20260409-132450` so CI parity tests track the same reference stream as the auditable published bundle.
- 2026-07-23: refreshed `active_constraints` labels on shielded arms to S2 stable IDs (`turn_feasibility[i]`, `box.lower[i]`, …) so native/reference active-set parity matches residual-derived activity (actions unchanged; `max_corrected_l2` remains ~1e-16).

## What changed in the reference path

- Files under `tests/fixtures/parity_reference/` were refreshed from that source directory per [docs/PARITY_AND_FIXTURES.md](../../../docs/PARITY_AND_FIXTURES.md).
- `episodes.jsonl` active-constraint labels updated for S2 verification naming (see above).

## Governed regeneration path

See [docs/PARITY_AND_FIXTURES.md](../../../docs/PARITY_AND_FIXTURES.md) for the full checklist. Summary:

1. Run a **validated** reference benchmark directory (e.g. `python -m conicshield.bench.reference_run` with the real solver, not `--passthrough-projector`, on a licensed host, or `python scripts/produce_reference_bundle.py ... --no-passthrough` from an offline export). Prefer promoting from a bundle already copied to **`benchmarks/published_runs/<run_id>/`** so the source matches committed governance artifacts.
2. Confirm `python -m conicshield.artifacts.validator_cli --run-dir <dir>` passes (or equivalent `validate_run_bundle`).
3. Run `python scripts/regenerate_parity_fixture.py --source <dir>`.
4. Re-run `python -m conicshield.parity.regenerate_fixture --reference-dir tests/fixtures/parity_reference`.
5. Update this note with what changed and why.

## What did not change

- Reference arm remains `shielded-rules-plus-geometry`
- Reference backend remains `cvxpy_moreau`
- **Parity gold was not regenerated from** `host-realistic-20260525` (export-evidence bundle; parity fixture stays aligned with `wsl-real-20260409-132450` until a licensed native/reference promotion is approved)

## Expected effect on parity

- Native parity tests should use this fixture as the gold reference stream.
- Active-constraint match rate should be 1.0 when candidate labels use S2 residual-derived IDs.

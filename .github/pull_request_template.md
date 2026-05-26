## Summary

<!-- What changed and why -->

## Testing

- [ ] Default CI (`quality`, `conic-trusted-shape`, `governance-audit`) is green or pending

## Solver / parity / published runs

If this PR touches `conicshield/core/moreau*`, `conicshield/parity/`, `benchmarks/published_runs/`, `tests/fixtures/parity_reference/`, or related governance scripts:

- [ ] `solver-touch` ran and passed (or explain why paths did not trigger)
- [ ] On the **canonical** repo: `vendor-ci-moreau` is green **or** I linked a maintainer manual vendor run / local `make test-vendor-moreau` result
- [ ] If published bundles changed: `python scripts/refresh_published_run_index.py` was run and committed

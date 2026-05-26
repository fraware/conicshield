## Summary

<!-- What changed and why -->

## Testing

- [ ] Default CI (`quality`, `conic-trusted-shape`, `governance-audit`) is green or pending

## Solver / parity / published runs

If this PR touches `conicshield/core/moreau*`, `conicshield/parity/`, `benchmarks/published_runs/`, `tests/fixtures/parity_reference/`, or related governance scripts:

- [ ] `solver-touch` ran and passed (or explain why paths did not trigger)
- [ ] **Required:** vendor proof attached — green `vendor-ci-moreau` **or** maintainer attestation (workflow run URL or `make test-vendor-moreau` summary). **Merge is blocked without this.**
- [ ] If published bundles changed: `python scripts/refresh_published_run_index.py` was run and committed

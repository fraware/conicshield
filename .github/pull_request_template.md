## Summary

<!-- What changed and why -->

## Testing

- [ ] Default CI (`quality`, `conic-trusted-shape`, `governance-audit`, `reference-authority`) is green or pending

## Solver / parity / published runs

If this PR touches `conicshield/core/moreau*`, `conicshield/parity/`, `benchmarks/published_runs/`, `tests/fixtures/parity_reference/`, or related governance scripts:

- [ ] `solver-touch` ran and passed (or explain why paths did not trigger)
- [ ] **Required (Policy B — repository law):** vendor attestation — green [`vendor-ci-moreau`](https://github.com/fraware/conicshield/actions/workflows/solver-ci.yml) run URL, `workflow_dispatch` link, or `make test-vendor-moreau` log excerpt. **Merge blocked without this.**
- [ ] Reviewer checklist completed: [`docs/REVIEWER_MERGE_CHECKLIST.md`](docs/REVIEWER_MERGE_CHECKLIST.md)
- [ ] If published bundles changed: `python scripts/refresh_published_run_index.py` was run and committed

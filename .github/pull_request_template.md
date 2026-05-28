## Summary

<!-- What changed and why -->

## Testing

- [ ] Default CI (`quality`, `conic-trusted-shape`, `governance-audit`, `reference-authority`) is green or pending
- [ ] If `docs/`, `examples/`, or published bundle READMEs changed public claims: cited [`docs/PUBLIC_CLAIMS.md`](docs/PUBLIC_CLAIMS.md) (or related stance doc) and `python scripts/check_public_claim_phrases.py` passes

## Solver / parity / published runs

If this PR touches `conicshield/core/moreau*`, `conicshield/parity/`, `benchmarks/published_runs/`, `tests/fixtures/parity_reference/`, or related governance scripts:

- [ ] `solver-touch` ran and passed (or explain why paths did not trigger)
- [ ] **Required (Policy B — repository law):** vendor attestation — green [`vendor-ci-moreau`](https://github.com/fraware/conicshield/actions/workflows/solver-ci.yml) run URL, `workflow_dispatch` link, or `make test-vendor-moreau` log excerpt. **Merge blocked without this.**
- [ ] Reviewer checklist completed: [`docs/REVIEWER_MERGE_CHECKLIST.md`](docs/REVIEWER_MERGE_CHECKLIST.md)
- [ ] If published bundles changed: `python scripts/refresh_published_run_index.py` was run and committed

## Host-realistic refresh triggers

If this PR changes `third_party/inter-sim-rl/REVISION`, export scripts, transition-bank generation, or release/governance logic:

- [ ] [`HOST_REALISTIC_CADENCE_POLICY.md`](docs/HOST_REALISTIC_CADENCE_POLICY.md) immediate refresh completed or scheduled
- [ ] `EXPORT_PROVENANCE.json` / [`REFERENCE_AUTHORITY_LOG.md`](docs/REFERENCE_AUTHORITY_LOG.md) updated
- [ ] `python scripts/generate_reference_system_status.py` committed

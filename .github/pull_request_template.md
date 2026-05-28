## Summary

<!-- What changed and why -->

## Testing

- [ ] Default CI (`quality`, `conic-trusted-shape`, `governance-audit`, `reference-authority`) is green or pending
- [ ] If public claims changed: aligned with [`docs/PUBLIC_CLAIMS.md`](docs/PUBLIC_CLAIMS.md) and `python scripts/check_public_claim_phrases.py` passes

## Solver / parity / published runs

If this PR touches solver, parity, `benchmarks/published_runs/`, or governance scripts:

- [ ] `solver-touch` ran and passed (or explain why paths did not trigger)
- [ ] **Policy B:** vendor attestation (green `vendor-ci-moreau`, workflow link, or `make test-vendor-moreau` excerpt)
- [ ] Published bundles: `refresh_published_run_index.py` committed; `make verify-v1-lock-quick` green

## Host-realistic refresh

If export, inter-sim pin, or flagship publish logic changed:

- [ ] `EXPORT_PROVENANCE.json` and [`benchmarks/reports/reference_refresh_log.md`](benchmarks/reports/reference_refresh_log.md) updated if a refresh ran
- [ ] `python scripts/generate_reference_system_status.py` committed when status fields change

# Reference evidence tiers

Label: `RUN_PROVENANCE.json` → `evidence_tier`.

| Tier | `evidence_tier` | Projector | Export | Example `run_id` |
|------|-----------------|-----------|--------|------------------|
| S0 | `contract_fixture` | passthrough / reference | minimal fixture | CI only |
| S1 | `structural_export` | passthrough or reference, no native publish | non-minimal committed export | rehearsal |
| S2 | `vendor_reference` | real CVXPY/Moreau | validated export | `wsl-real-20260409-132450` |
| S3 | `vendor_native` | native + parity | governed export | **`host-realistic-20260525`**, `wsl-native-20260409-091141` |

**Flagship (S3):** `host-realistic-20260525` — family `current_run_id`, `live_upstream_dump`, fork graph via inter-sim API.

## CI enforcement

| Tier | Without vendor secrets |
|------|------------------------|
| S0–S1 | `governance-audit`, `verify-reference-system` |
| S2–S3 | Above + `solver-touch`; solves need `vendor-ci-moreau` or maintainer attestation |

Required on `main`: includes `reference-authority` — [`CI_MERGE_GATES.md`](CI_MERGE_GATES.md).

## Refresh (flagship)

```bash
make capture-inter-sim-graph
make refresh-live-upstream-export-live
make host-realistic-refresh-cycle
```

Log: [`REFERENCE_REFRESH_LOG.md`](REFERENCE_REFRESH_LOG.md).

## Parity fixture

Gold: `tests/fixtures/parity_reference/` — promote from **S2** only. [`REGENERATION_NOTE.md`](../tests/fixtures/parity_reference/REGENERATION_NOTE.md).

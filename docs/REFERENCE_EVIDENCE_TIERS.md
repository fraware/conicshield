# Reference evidence tiers

ConicShield separates **what the repo proves in public CI** from **what requires a licensed Moreau stack**. Published runs are labeled by tier in `RUN_PROVENANCE.json` (`evidence_tier`).

| Tier | `evidence_tier` | Projector | Export source | Example `run_id` |
|------|-----------------|-----------|---------------|------------------|
| **S0 — contract smoke** | `contract_fixture` | passthrough or reference | `tests/fixtures/offline_graph_export_minimal.json` | CI rehearsal only |
| **S1 — structural export loop** | `structural_export` | passthrough (or reference without native) | `benchmarks/external_evidence/` (non-minimal graph) | `host-realistic-20260525` |
| **S2 — vendor reference** | `vendor_reference` | real CVXPY/Moreau reference | any validated export | `wsl-real-20260409-132450` |
| **S3 — vendor native** | `vendor_native` | native compiled + parity | governed export | `wsl-native-20260409-091141` |

## Public CI coverage

| Tier | Enforced without vendor secrets |
|------|--------------------------------|
| S0–S1 | `governance-audit`, `verify-reference-system`, host-realistic provenance tests |
| S2–S3 | `solver-touch` index/parity; full solve oracle requires `vendor-ci-moreau` |

## Upgrade path (S1 → S3)

On a licensed host with patched `inter-sim-rl`:

```bash
python scripts/upgrade_host_realistic_vendor.py
```

Or follow [`HOST_REALISTIC_RUNBOOK.md`](HOST_REALISTIC_RUNBOOK.md) step by step.

## Parity fixture policy

Parity gold (`tests/fixtures/parity_reference/`) is promoted from **S2** reference bundles, not from S1 structural runs. See [`tests/fixtures/parity_reference/REGENERATION_NOTE.md`](../tests/fixtures/parity_reference/REGENERATION_NOTE.md).

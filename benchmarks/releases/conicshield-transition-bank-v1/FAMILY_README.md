# Benchmark Family: conicshield-transition-bank-v1

**Governance:** [../../../docs/BENCHMARK_GOVERNANCE.md](../../../docs/BENCHMARK_GOVERNANCE.md), [../../../docs/RELEASE_POLICY.md](../../../docs/RELEASE_POLICY.md).

## Purpose
This family defines the current semantic contract for the ConicShield transition-bank benchmark.

## Task contract
See `FAMILY_MANIFEST.json`.

## Current release
See `CURRENT.json` (gates and `publishable_arms` are explained in [`docs/BENCHMARK_GOVERNANCE.md`](../../../docs/BENCHMARK_GOVERNANCE.md)). After parity work, gate fields may be updated with `finalize_cli --sync-current-release` per [`docs/MAINTAINER_RUNBOOK.md`](../../../docs/MAINTAINER_RUNBOOK.md).

## Historical releases
See `HISTORY.json`.

## Committed run bundles (audit)

Canonical benchmark trees for this family live under [`../../published_runs/`](../../published_runs/README.md). `CURRENT.json` lists `benchmark_bundle_paths` (current and superseded runs referenced in `HISTORY.json`) so reviewers can open the same paths in Git without guessing `run_id` layout. Integrity hashes for committed bundles: [`../../PUBLISHED_RUN_INDEX.json`](../../PUBLISHED_RUN_INDEX.json) (see [`benchmarks/published_runs/README.md`](../../published_runs/README.md)).

**Other families:** a second family directory exists as scaffold only — [`../conicshield-shield-qp-micro-v1/FAMILY_README.md`](../conicshield-shield-qp-micro-v1/FAMILY_README.md).

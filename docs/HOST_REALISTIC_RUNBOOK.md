# Host-realistic benchmark loop (operational bar)

The repository proves governance, parity, and **structural** inter-sim integration using minimal exports and fixtures. The **acceptance bar for host-realistic evidence** is still: a **real** upstream `inter-sim-rl` offline graph export (from your patched host), not only [`tests/fixtures/offline_graph_export_minimal.json`](../tests/fixtures/offline_graph_export_minimal.json).

This document is the checklist to close that bar once on a licensed maintainer machine. It does not automate your upstream simulator.

## Preconditions

- Linux or WSL2, [`docs/MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md`](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md) satisfied.
- Patched `inter-sim-rl` checkout or submodule per [`docs/INTER_SIM_RL_INTEGRATION.md`](INTER_SIM_RL_INTEGRATION.md), `INTERSIM_RL_ROOT` or equivalent.
- `python scripts/run_live_vendor_tests.py --bootstrap` and green vendor smoke where applicable.

## Sequence (one end-to-end proof)

1. **Export** — Produce a real offline graph export JSON from the upstream stack (same schema as ConicShield’s offline export contract). Save it outside ephemeral dirs if you need a long-lived artifact path.
2. **Transition bank** — Build `transition_bank.json` from that export (see `conicshield.bench` builders / [`scripts/build_transition_bank`](../scripts/) helpers and [`benchmarks/runs/README.md`](../benchmarks/runs/README.md)).
3. **Reference bundle** — Run `python -m conicshield.bench.reference_run` (or the governed wrapper you use for publishes) with a **non-passthrough** projector and **`--include-native-arm`** when native evidence is required. Output under `benchmarks/runs/<run_id>/` or your staging path.
4. **Validate** — `python -m conicshield.artifacts.validator_cli --run-dir <bundle_dir>`.
5. **Parity** — Run `python -m conicshield.parity.cli` against `tests/fixtures/parity_reference/` or refresh the fixture from this bundle only when promotion is approved ([`docs/PARITY_AND_FIXTURES.md`](PARITY_AND_FIXTURES.md)).
6. **Publish** — Copy the validated bundle to `benchmarks/published_runs/<run_id>/`, add human `governance_decision.md`, run `finalize_cli` / `release_cli` / `audit_cli --strict` per [`docs/MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).
7. **Index** — `python scripts/refresh_published_run_index.py` and commit `benchmarks/PUBLISHED_RUN_INDEX.json` (schema ≥ 2 records hashes for the full validated bundle file set; see [`benchmarks/published_runs/README.md`](../benchmarks/published_runs/README.md)).
8. **Record** — Update [`tests/fixtures/parity_reference/REGENERATION_NOTE.md`](../tests/fixtures/parity_reference/REGENERATION_NOTE.md) if the fixture was regenerated from this run.

Orchestration helpers: [`scripts/governed_local_promotion.py`](../scripts/governed_local_promotion.py), [`benchmarks/published_runs/README.md`](../benchmarks/published_runs/README.md) (*Host-realistic rehearsal*).

## What “done” means

You have a committed `run_id` under `benchmarks/published_runs/` whose `RUN_PROVENANCE.json` / notes identify the **real** upstream export, green validator + governance gates, and (if native is claimed) parity artifacts attached to the same promotion. Until then, the roadmap item **host-realistic substrate** remains open ([`ROADMAP.md`](ROADMAP.md)).

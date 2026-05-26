# Host-realistic benchmark loop (operational bar)

The repository **closes** the host-realistic bar in Git with committed upstream-shaped export evidence under [`benchmarks/external_evidence/`](../benchmarks/external_evidence/) and flagship published run [`host-realistic-20260525`](../benchmarks/published_runs/host-realistic-20260525/) (`evidence_tier: vendor_native`, `real_projector`, `parity_out/`, family `current_run_id`).

This document is the checklist for **refreshing** that evidence on a licensed maintainer machine or reproducing the loop for a new `run_id`. It does not automate your upstream simulator.

## Preconditions

- Linux or WSL2, [`docs/MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md`](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md) satisfied.
- Patched `inter-sim-rl` checkout or submodule per [`docs/INTER_SIM_RL_INTEGRATION.md`](INTER_SIM_RL_INTEGRATION.md), `INTERSIM_RL_ROOT` or equivalent.
- `python scripts/run_live_vendor_tests.py --bootstrap` and green vendor smoke where applicable.

## Sequence (one end-to-end proof)

1. **Export** — Produce a real offline graph export JSON from the upstream stack (same schema as ConicShield’s offline export contract). Use [`scripts/export_inter_sim_offline_graph.py`](../scripts/export_inter_sim_offline_graph.py) with `--graph-json` from a patched-host `offline_transition_graph` dump, or `--rehearsal-fork` for the committed structural graph. Save outside ephemeral dirs if you need a long-lived artifact path.
2. **Transition bank** — Build `transition_bank.json` from that export (see `conicshield.bench` builders / [`scripts/build_transition_bank`](../scripts/) helpers and [`benchmarks/runs/README.md`](../benchmarks/runs/README.md)).
3. **Reference bundle** — Run `python -m conicshield.bench.reference_run` (or the governed wrapper you use for publishes) with a **non-passthrough** projector and **`--include-native-arm`** when native evidence is required. Output under `benchmarks/runs/<run_id>/` or your staging path.
4. **Validate** — `python -m conicshield.artifacts.validator_cli --run-dir <bundle_dir>`.
5. **Parity** — Run automatically when using [`scripts/run_host_realistic_publish.py`](../scripts/run_host_realistic_publish.py) with `--governance-scaffold` (native arm present), or manually: `python -m conicshield.parity.cli` against `tests/fixtures/parity_reference/`. Refresh the fixture from this bundle only when promotion is approved ([`docs/PARITY_AND_FIXTURES.md`](PARITY_AND_FIXTURES.md)).
6. **Publish** — Copy the validated bundle to `benchmarks/published_runs/<run_id>/`, complete `governance_decision.md`, run `finalize_cli` / `release_cli` / `audit_cli --strict` per [`docs/MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).
7. **Index** — `python scripts/refresh_published_run_index.py` and commit `benchmarks/PUBLISHED_RUN_INDEX.json` (schema ≥ 2 records hashes for the full validated bundle file set; see [`benchmarks/published_runs/README.md`](../benchmarks/published_runs/README.md)).
8. **Record** — Update [`tests/fixtures/parity_reference/REGENERATION_NOTE.md`](../tests/fixtures/parity_reference/REGENERATION_NOTE.md) if the fixture was regenerated from this run.

Orchestration helpers: [`scripts/run_host_realistic_publish.py`](../scripts/run_host_realistic_publish.py) (export → bundle → parity → finalize → optional `published_runs` copy with `--refresh-index`; rejects minimal fixture by default), [`scripts/upgrade_host_realistic_vendor.py`](../scripts/upgrade_host_realistic_vendor.py) (`make upgrade-host-realistic-vendor`), [`scripts/governed_local_promotion.py`](../scripts/governed_local_promotion.py), [`benchmarks/external_evidence/README.md`](../benchmarks/external_evidence/README.md), [`benchmarks/published_runs/README.md`](../benchmarks/published_runs/README.md).

## What “done” means (in-repo today)

You have a committed `run_id` under `benchmarks/published_runs/` whose `RUN_PROVENANCE.json` identifies a **non-minimal** upstream-shaped export, green `validate_run_bundle`, and for vendor claims:

- `projector_mode: real_projector`
- `evidence_tier: vendor_native`
- `parity_out/parity_summary.json` and `governance_status.json` with `parity_gate` / `promotion_gate` green
- `shielded-native-moreau` in `publishable_arms`

**Flagship:** `host-realistic-20260525` satisfies this bar. See [`docs/REFERENCE_EVIDENCE_TIERS.md`](REFERENCE_EVIDENCE_TIERS.md).

## Optional refresh

| Goal | Command |
|------|---------|
| Full vendor rebuild | `make upgrade-host-realistic-vendor` or `python scripts/upgrade_host_realistic_vendor.py --force` |
| Governance + parity only | `python scripts/upgrade_host_realistic_vendor.py --refresh-governance` |
| Live upstream dump | `python scripts/refresh_live_upstream_export.py --graph-json <dump.json>` then `make upgrade-host-realistic-vendor` |

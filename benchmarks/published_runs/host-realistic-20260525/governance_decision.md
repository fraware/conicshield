# Governance decision record

**Policy:** [BENCHMARK_GOVERNANCE.md](../../docs/BENCHMARK_GOVERNANCE.md), [MAINTAINER_RUNBOOK.md](../../docs/MAINTAINER_RUNBOOK.md) (publish sequence).

## Run

- **run_id:** `host-realistic-20260525`
- **family_id:** `conicshield-transition-bank-v1`
- **task_contract_version:** `v1`
- **fixture_version:** `fixture-v1`

## Decision

- **Outcome:** `approve`
- **Reviewer(s):** `maintainer`
- **Date (UTC):** `2026-05-25`

## Evidence

- Artifact validation: `pass` — `validate_run_bundle` green on published directory.
- Native parity: `green` — summary path: `parity_out/parity_summary.json` (offline replay vs `tests/fixtures/parity_reference/`).
- Promotion / review-lock gates: `green` — all required arms present; native promotion thresholds satisfied; `review_locked: true`.

## Rationale

Same-family publish promoting flagship **host-realistic** external-evidence run: upstream-shaped export (`benchmarks/external_evidence/offline_graph_export_upstream.json`), `vendor_native` tier, `real_projector`, native arm with parity and promotion gates green. Replaces `wsl-native-20260409-091141` as `current_run_id` while retaining historical bundles in `benchmark_bundle_paths`. No task-contract or fixture-version change.

## Follow-ups

- Optional: live inter-sim re-export to refresh committed export JSON and `EXPORT_PROVENANCE.json` when upstream dump is available.
- Parity fixture promotion remains governed by S2 reference policy (`REGENERATION_NOTE.md`).

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

Same-family flagship **host-realistic** external-evidence run (`vendor_native`, `real_projector`). Refresh cycles re-validated export → bundle → parity → finalize; gates remain green. `current_run_id` unchanged. Live export path executed 2026-05-26 (`export_kind: live_upstream_dump`); graph remains host-realistic fork topology via inter-sim `RLEnvironment`, not a full navigation-session graph.

## Follow-ups

- Re-capture when `third_party/inter-sim-rl/REVISION` changes or a **navigation-session** graph exists (not fork-only).
- Log each refresh in `docs/REFERENCE_REFRESH_LOG.md`.
- Parity gold: S2 policy only (`tests/fixtures/parity_reference/REGENERATION_NOTE.md`).

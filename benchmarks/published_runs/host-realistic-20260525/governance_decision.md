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

Same-family flagship **host-realistic** external-evidence run (`vendor_native`, `real_projector`). Scheduled refresh cycle re-validated export → bundle → parity → finalize; gates remain green. `current_run_id` unchanged.

## Follow-ups

- Optional live inter-sim re-export when upstream dump available (`scripts/refresh_live_upstream_export.py`).
- Parity fixture promotion remains governed by S2 reference policy (`REGENERATION_NOTE.md`).

# Governance decision record

**Policy:** [BENCHMARK_GOVERNANCE.md](../../docs/BENCHMARK_GOVERNANCE.md), [MAINTAINER_RUNBOOK.md](../../docs/MAINTAINER_RUNBOOK.md) (publish sequence).

Replace placeholders before publish. Copy this file to the run directory as `governance_decision.md` **before** `python -m conicshield.governance.release_cli` **without** `--dry-run`. `finalize_cli` and `release_cli --dry-run` do not read it; `publish_from_governance_status` requires it alongside `governance_status.json`.

## Run

- **run_id:** `host-realistic-20260525`
- **family_id:** `conicshield-transition-bank-v1`
- **task_contract_version:** `v1`
- **fixture_version:** `fixture-v1`

## Decision

- **Outcome:** `defer`
- **Reviewer(s):** `maintainer`
- **Date (UTC):** `pending`

## Evidence

- Artifact validation: `<pass | fail>` — notes: `<...>`
- Native parity (if native arm is publishable): `<green | red | n/a>` — summary path: `<path/to/parity_summary.json>`
- Promotion / review-lock gates: `<...>`

## Rationale

`<Why this run is or is not eligible for same-family publish. Reference benchmark card, risk, or semantic changes.>`

## Follow-ups

- `<e.g. bump family, refresh fixture, solver stack pin update>`

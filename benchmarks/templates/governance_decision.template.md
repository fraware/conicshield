# Governance decision record

**Policy:** [BENCHMARK_GOVERNANCE.md](../../docs/BENCHMARK_GOVERNANCE.md), [MAINTAINER_RUNBOOK.md](../../docs/MAINTAINER_RUNBOOK.md) (publish sequence).

Replace placeholders before publish. This file must exist as `governance_decision.md` in the run directory; `publish_from_governance_status` requires it alongside `governance_status.json`.

## Run

- **run_id:** `<RUN_ID>`
- **family_id:** `<FAMILY_ID>`
- **task_contract_version:** `<TASK_CONTRACT_VERSION>`
- **fixture_version:** `<FIXTURE_VERSION>`

## Decision

- **Outcome:** `<approve | reject | defer>`
- **Reviewer(s):** `<names or roles>`
- **Date (UTC):** `<ISO-8601>`

## Evidence

- Artifact validation: `<pass | fail>` — notes: `<...>`
- Native parity (if native arm is publishable): `<green | red | n/a>` — summary path: `<path/to/parity_summary.json>`
- Promotion / review-lock gates: `<...>`

## Rationale

`<Why this run is or is not eligible for same-family publish. Reference benchmark card, risk, or semantic changes.>`

## Follow-ups

- `<e.g. bump family, refresh fixture, solver stack pin update>`

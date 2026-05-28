# Host-realistic refresh cadence policy

Binding schedule for flagship `host-realistic-20260525` (`conicshield-transition-bank-v1`). Procedure: [`HOST_REALISTIC_REFRESH_PROCEDURE.md`](HOST_REALISTIC_REFRESH_PROCEDURE.md). Durable log: [`REFERENCE_AUTHORITY_LOG.md`](REFERENCE_AUTHORITY_LOG.md).

## Default cadence

| Rule | Action |
|------|--------|
| **Monthly** | Run the full live workflow on a licensed Linux/WSL host by the **1st UTC** (GitHub: [`host-realistic-refresh-cadence.yml`](../.github/workflows/host-realistic-refresh-cadence.yml) reminds + records export steps). |
| **Immediate** | Re-run full cycle after any of the triggers below. |

## Immediate triggers (same full cycle)

1. **`third_party/inter-sim-rl/REVISION` changes** — re-capture graph; verify export contract.
2. **Export parsing changes** — `export_inter_sim_offline_graph.py`, `capture_inter_sim_offline_graph.py`, upstream JSON schema handling.
3. **Transition-bank generation changes** — `produce_reference_bundle.py`, bank builders, host-realistic publish path.
4. **Release / governance logic changes** — `finalize_cli`, `release_cli`, `reference_authority_check`, family `CURRENT.json` rules.

## Full cycle definition

Each refresh must complete, in order:

1. `make host-realistic-refresh-cycle-licensed` (capture → export → publish → parity → release → batch → index → snapshot → authority check → log amend)
2. Commit governed artifacts (see procedure doc)

`--skip-vendor-verify` is for export-only or governance-only emergencies; **do not** use for monthly cadence sign-off.

## Evidence bar (acceptance)

| Requirement | How verified |
|-------------|----------------|
| ≥2 independent refreshes on flagship path | [`REFERENCE_AUTHORITY_LOG.md`](REFERENCE_AUTHORITY_LOG.md) rows |
| ≥1 refresh tied to live upstream workflow | Row with `live_upstream_dump` + `workflow=live-export-full` + `authority_ok` |
| Authority aligned after each cycle | `reference_authority_check` green; committed `reference_authority_snapshot.json` |
| Unattended schedule evidenced | Monthly workflow run + log row `trigger=calendar-cadence-workflow` |

## Staleness guard

```bash
python scripts/check_reference_refresh_cadence.py --max-days 35
python scripts/check_flagship_full_refresh_cadence.py --max-days 35
```

Fails CI when export or **full** (`live-export-full` + `authority_ok`) refresh is older than 35 days.

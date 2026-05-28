# v1 reference system lock checklist

Use this before declaring the **host-realistic flagship** reference system locked for external consumers. Machine summary: [`benchmarks/reports/reference_system_status.json`](../benchmarks/reports/reference_system_status.json).

## 1. Local verification (any maintainer machine)

```bash
make verify-v1-lock          # full gate (includes governance pytest subset)
make verify-v1-lock-quick    # fast auditor summary (no verify-reference-system)
python scripts/verify_v1_lock.py --json
```

Full target: `verify-reference-system`, `community-verify`, index/status `--check`, and `verify_v1_lock.py` report.

## 2. Flagship cadence

| Gate | Command |
|------|---------|
| Export staleness (35d) | `python scripts/check_reference_refresh_cadence.py --max-days 35` |
| Full cycle (35d) | `python scripts/check_flagship_full_refresh_cadence.py --max-days 35` |
| Authority alignment | `make reference-authority-check` |

Licensed full refresh: `make host-realistic-refresh-cycle-licensed` ([procedure](HOST_REALISTIC_REFRESH_PROCEDURE.md)).

## 3. Community dataset

| Step | Command |
|------|---------|
| Finalize bundles | `make finalize-community-dataset` |
| Consumer smoke | `make community-verify` |
| Flagship integrity | `python -m conicshield.published_runs.cli verify host-realistic-20260525` |

## 4. Public claim boundaries (do not overstate)

- Batch: viability-governed; not universal speedup — [`PUBLIC_CLAIMS.md`](PUBLIC_CLAIMS.md)
- Differentiation: validation only — [`DIFFERENTIATION_PUBLIC_STANCE.md`](DIFFERENTIATION_PUBLIC_STANCE.md)
- Graph: inter-sim fork topology; not Maps/session navigation

## 5. CI on `main`

After push, confirm green: `quality`, `conic-trusted-shape`, `governance-audit`, `reference-authority`, `solver-touch` (when paths match). See [`CI_MERGE_GATES.md`](CI_MERGE_GATES.md).

## Machine status (committed)

```bash
python scripts/print_v1_status.py
python scripts/verify_v1_lock.py --json
```

Reads [`benchmarks/reports/reference_system_status.json`](../benchmarks/reports/reference_system_status.json). Expect `reference_authority_aligned: true`, `full_refresh_cadence_ok: true`, `cadence_policy_ok: true`.

## v1 complete when

- [ ] `make verify-v1-lock` passes locally
- [ ] `make onboard` passes (community smoke + status)
- [ ] `reference-authority` green on `main`
- [ ] At least one `live-export-full` refresh with `authority_ok` within 35 days

Open backlog after lock: [`ROADMAP.md`](ROADMAP.md) items 1–6.

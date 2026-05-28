# Reference refresh log

Durable refresh record for `conicshield-transition-bank-v1` / flagship `host-realistic-20260525`.  
Machine source: `benchmarks/external_evidence/EXPORT_PROVENANCE.json` (`refresh_history`).

| # | completed_at_utc | trigger | workflow | export_kind | git_ref | authority_ok | notes |
|---|------------------|---------|----------|-------------|---------|--------------|-------|
| 1 | 2026-05-26T04:36:00Z | event-driven | manual | structural_committed → live | `2ff5fea` | yes | v1 refresh execution |
| 2 | 2026-05-26T06:05:21Z | event-driven-live-export | live-export | live_upstream_dump | `381004e` | yes | capture + full cycle |
| 3 | 2026-05-28T16:28:58Z | calendar-cadence | live-export | live_upstream_dump | `5485dfb` | yes | monthly maintainer cycle |
| 4 | 2026-05-28T17:00:56Z | calendar-cadence | live-export-full | live_upstream_dump | `2777cc6` | yes | host-realistic-refresh-cycle host-realistic-20260525 |

<!-- Append rows via: python scripts/record_reference_refresh.py -->

Licensed full cycle:

```bash
make host-realistic-refresh-cycle-licensed
```

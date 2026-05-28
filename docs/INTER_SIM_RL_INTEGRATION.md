# inter-sim-rl integration

ConicShield does not vendor upstream code. Pin: [`third_party/inter-sim-rl/REVISION`](../third_party/inter-sim-rl/REVISION).

**Flagship evidence:** export → publish closed with `host-realistic-20260525` ([`REFERENCE_AUTHORITY.md`](REFERENCE_AUTHORITY.md)).

## Pin (current)

| Field | Value |
|-------|--------|
| Repository | https://github.com/fraware/inter-sim-rl |
| SHA | `f1f04ee11d064262f5ee2810abfcb01715260182` |
| Checkout | `third_party/inter-sim-rl/checkout` or `INTERSIM_RL_ROOT` |

Re-validate on API changes; update `REVISION` and re-run capture + refresh cycle.

## Runtime seam

| Step | Contract |
|------|----------|
| Input | `q_values`, `action_space`, `context` (see `schemas/shield_context.schema.json`) |
| Output | Corrected action string |
| Actions | `turn_left`, `turn_right`, `go_straight`, `turn_back` |

M2 patch: `get_shield_context()`, action-conditioned transitions, `offline_transition_graph` export.

## Export → bank

1. `offline_transition_graph` dict JSON (or `make capture-inter-sim-graph`)
2. `export_inter_sim_offline_graph.py` → `offline_transition_graph_export/v1`
3. `build_transition_bank --from-offline-graph-export`

Schema: [`schemas/offline_transition_graph_export.schema.json`](../schemas/offline_transition_graph_export/schema.json).

## Capture path (flagship)

```bash
make capture-inter-sim-graph          # RLEnvironment + host-realistic fork
make refresh-live-upstream-export-live
```

Writes `benchmarks/external_evidence/live_dumps/` and updates `EXPORT_PROVENANCE.json` (`export_kind: live_upstream_dump`).

**Not claimed:** full Maps/session graph unless a future capture documents it.

## CI without upstream checkout

- Structural export: `make export-upstream-rehearsal`
- Minimal fixture: contract smoke only — not flagship tier

## Tests

- `pytest -m inter_sim_rl` — needs checkout + dev deps
- Workflow: `inter-sim-rl-ci.yml` (manual dispatch)

## Validation

`conicshield.adapters.inter_sim_rl.context_validate.validate_shield_context_dict`

## Related

- [`HOST_REALISTIC_REFRESH_PROCEDURE.md`](HOST_REALISTIC_REFRESH_PROCEDURE.md)
- [`benchmarks/external_evidence/README.md`](../benchmarks/external_evidence/README.md)
- [`third_party/inter-sim-rl/README.md`](../third_party/inter-sim-rl/README.md)

LabTrust-Gym: separate repo; `REVISION_LABTRUST_GYM` for bookkeeping only.

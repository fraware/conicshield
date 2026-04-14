# `inter-sim-rl` integration plan

This repository is intentionally standalone. It does not vendor the external `inter-sim-rl` codebase.

**Benchmark closure (export → bank → governed publish):** Tracked in [docs/ROADMAP.md](ROADMAP.md) (*External integration* and open backlog). **Operational checklist** for a real upstream export: [docs/HOST_REALISTIC_RUNBOOK.md](HOST_REALISTIC_RUNBOOK.md).

**Canonical upstream:** [https://github.com/fraware/inter-sim-rl](https://github.com/fraware/inter-sim-rl)

## Integration seam

1. external environment produces a state object and a four-action space
2. external policy produces four Q-values or action scores
3. ConicShield consumes:
   - `q_values`
   - `action_space`
   - `context`
4. ConicShield returns a corrected action string

## Expected action space

```python
["turn_left", "turn_right", "go_straight", "turn_back"]
```

## Expected context shape

At minimum:
- `allowed_actions`
- `blocked_actions`
- `action_upper_bounds`
- `rule_choice`
- `previous_instruction`
- `hazard_score`

Optional:
- `current_heading_deg`
- `branch_bearings_deg`
- transition-bank candidate metadata

## Recommended patch surface in the external environment

- add `get_shield_context()`
- preserve the current observation contract
- let chosen action affect transitions
- expose a transition-bank export path (see below)

## Transition bank export contract

After the M2 patch, `RLEnvironment` can run with `offline_transition_graph: Dict[str, List[Dict]]` (address to candidate edges). To freeze a bank for ConicShield:

1. Serialize that graph plus coordinates for every visited address into **offline_transition_graph_export/v1** JSON (schema: [`schemas/offline_transition_graph_export.schema.json`](../schemas/offline_transition_graph_export.schema.json)).
2. Build a validated transition bank file:

   ```bash
   python -m conicshield.bench.build_transition_bank \
     --from-offline-graph-export path/to/export.json \
     --out /tmp/bank.json
   ```

Example minimal export: [`tests/fixtures/offline_graph_export_minimal.json`](../tests/fixtures/offline_graph_export_minimal.json).

## End-to-end chain without a live environment

You can exercise the full **export → bank → benchmark bundle** spine using only in-repo JSON and no running simulator:

1. Use [`tests/fixtures/offline_graph_export_minimal.json`](../tests/fixtures/offline_graph_export_minimal.json) (or a copy of your own export that validates against [`schemas/offline_transition_graph_export.schema.json`](../schemas/offline_transition_graph_export.schema.json)).
2. Run [`scripts/produce_reference_bundle.py`](../scripts/produce_reference_bundle.py) with `--export-json` and `--run-id` (add `--passthrough` on unlicensed hosts; use `--no-passthrough` for governed reference arms).
3. Validate with `python -m conicshield.artifacts.validator_cli --run-dir benchmarks/runs/<run_id>`.

This path matches the operational P0 sequence in [`benchmarks/runs/README.md`](../benchmarks/runs/README.md) without API calls into a patched host.

**Production acceptance (P2):** a pinned [`third_party/inter-sim-rl/REVISION`](../third_party/inter-sim-rl/REVISION) checkout exports a real `offline_transition_graph_export/v1` JSON; `build_transition_bank` validates it; `reference_run` (or `scripts/produce_reference_bundle.py`) consumes the bank under `benchmarks/runs/<run_id>/` with **no live** environment API calls in the benchmark path. Until that runs on a patched host, treat the in-repo minimal export as contract-only evidence.

Engineering control for clone URL and revision: [`third_party/inter-sim-rl/README.md`](../third_party/inter-sim-rl/README.md).

## Revision pin

Pinned `main` at the time this record was updated (see `third_party/inter-sim-rl/REVISION` for the same values):

| Field | Value |
| ----- | ----- |
| Repository | [fraware/inter-sim-rl](https://github.com/fraware/inter-sim-rl) |
| Branch | `main` |
| SHA | `f1f04ee11d064262f5ee2810abfcb01715260182` |
| Commit | [view on GitHub](https://github.com/fraware/inter-sim-rl/commit/f1f04ee11d064262f5ee2810abfcb01715260182) |

Re-validate and update the SHA when ConicShield or upstream APIs change.

Optional local checkout: submodule at `third_party/inter-sim-rl/checkout`, or set `INTERSIM_RL_ROOT` to a clone root.

End-to-end tests that import upstream `RLEnvironment` require **`matplotlib`** (pulled in via `pip install -e ".[dev]"`). Install dev deps before running `tests/test_inter_sim_rl_e2e.py`.

In-repo contract tests validate payloads against `schemas/shield_context.schema.json`; they do not require the upstream repo to be present.

## Related Fraware repository

[LabTrust-Gym](https://github.com/fraware/LabTrust-Gym) is a separate multi-agent lab automation environment. It is not the `inter-sim-rl` integration target; a reference `main` SHA is recorded in `third_party/inter-sim-rl/REVISION_LABTRUST_GYM` for cross-repo bookkeeping.

## Contract validation

Python adapters may validate context with `conicshield.adapters.inter_sim_rl.context_validate.validate_shield_context_dict` or `ShieldContextModel.from_mapping` (`context_model.py`).

## Related ConicShield documentation

- [DEVENV.md](DEVENV.md) — `inter_sim_rl` pytest marker and optional CI workflow
- [README.md](../README.md) — `third_party/` pin and integration overview
- [schemas/shield_context.schema.json](../schemas/shield_context.schema.json) — contract schema

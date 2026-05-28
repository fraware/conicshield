# Host-realistic runbook

Manual steps for the export → publish loop. **Routine refresh:** [`HOST_REALISTIC_REFRESH_PROCEDURE.md`](HOST_REALISTIC_REFRESH_PROCEDURE.md) (`make host-realistic-refresh-cycle-licensed` on a licensed Linux/WSL host).

## Preconditions

- Linux/WSL2; [`MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md`](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md)
- `inter-sim-rl` checkout at [`third_party/inter-sim-rl/REVISION`](../third_party/inter-sim-rl/REVISION); M2 patch applied
- Green `python scripts/run_live_vendor_tests.py --bootstrap` where applicable

## Flagship bar (met by `host-realistic-20260525`)

| Requirement | Flagship field |
|-------------|----------------|
| Non-minimal export | `host_realistic_evidence: true`, not `minimal_fixture_export` |
| Real projector | `projector_mode: real_projector` |
| Native tier | `evidence_tier: vendor_native` |
| Parity | `parity_out/parity_summary.json`, `parity_gate: green` |
| Native arm | `shielded-native-moreau` in `publishable_arms` |
| Live export kind | `EXPORT_PROVENANCE.export_kind: live_upstream_dump` |

**Qualification:** graph is host-realistic **fork** via `RLEnvironment`, not a full navigation-session dump. See bundle README evidence section.

## Sequence

| Step | Action |
|------|--------|
| 1 | Export: `make capture-inter-sim-graph` + `make refresh-live-upstream-export-live`, or `export_inter_sim_offline_graph.py --graph-json <dump>` |
| 2 | Bank: `build_transition_bank --from-offline-graph-export` |
| 3 | Bundle: `run_host_realistic_publish.py --no-passthrough --include-native-arm --governance-scaffold --copy-to-published` |
| 4 | Validate: `validator_cli --run-dir <dir>` |
| 5 | Parity | Included in publish script when native arm present |
| 6 | Publish | `governance_decision.md` (approve) → `release_cli` → `audit_cli --strict` |
| 7 | Index | `refresh_published_run_index.py` |

Orchestrated: `make upgrade-host-realistic-vendor` or `make host-realistic-refresh-cycle`.

## One-shot commands

```bash
make host-realistic-refresh-cycle
# or
make upgrade-host-realistic-vendor --force
```

## Parity fixture

Promote gold from **S2** reference bundle only ([`PARITY_AND_FIXTURES.md`](PARITY_AND_FIXTURES.md)). Update [`REGENERATION_NOTE.md`](../tests/fixtures/parity_reference/REGENERATION_NOTE.md) when promoted.

## Tiers

[`REFERENCE_EVIDENCE_TIERS.md`](REFERENCE_EVIDENCE_TIERS.md) — flagship is **S3**.

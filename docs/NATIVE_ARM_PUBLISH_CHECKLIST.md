# Native arm publish checklist

Goal: `shielded-native-moreau` in `publishable_arms` with green parity/promotion.

**Flagship:** `host-realistic-20260525` — refresh with `make host-realistic-refresh-cycle`.

## Fast path (flagship)

```bash
make host-realistic-refresh-cycle
```

Or:

```bash
python scripts/run_host_realistic_publish.py \
  --export-json benchmarks/external_evidence/offline_graph_export_upstream.json \
  --run-id host-realistic-20260525 \
  --no-passthrough --include-native-arm \
  --governance-scaffold --copy-to-published --refresh-index --force
```

Then: approved `governance_decision.md` → `release_cli` → `audit_cli --strict`.

## `finalize_cli` requirements

1. `summary.json` row `"label": "shielded-native-moreau"` (real projector, not passthrough).
2. `parity_out/parity_summary.json` — pass `--parity-summary-path` to `finalize_cli`.
3. Promotion thresholds green (`conicshield/governance/promotion.py`).

## Manual sequence

| Step | Command |
|------|---------|
| Bundle | `reference_run` with `--no-passthrough`, native arm |
| Validate | `validator_cli --run-dir …` |
| Parity | `conicshield.parity.cli` vs `tests/fixtures/parity_reference/` |
| Finalize | `finalize_cli` + `--parity-summary-path` |
| Publish | `governance_decision.md` → `release_cli` |

Detail: [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md), [`HOST_REALISTIC_RUNBOOK.md`](HOST_REALISTIC_RUNBOOK.md).

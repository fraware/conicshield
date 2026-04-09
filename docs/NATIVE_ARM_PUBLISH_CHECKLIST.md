# Checklist: endorse `shielded-native-moreau`

`finalize_cli` adds `shielded-native-moreau` to `publishable_arms` only when **all** of the following hold:

1. **`summary.json`** includes a row with `"label": "shielded-native-moreau"` (produce it with a real projector, not `--passthrough-projector`):

   ```bash
   python -m conicshield.bench.reference_run \
     --out benchmarks/runs/<run_id> \
     --bank /path/to/transition_bank.json \
     --include-native-arm
   ```

2. **Parity evidence** for the native path: run `conicshield.parity.cli` against the frozen fixture and pass `--parity-summary-path` to `finalize_cli` so `parity_gate` is green for native endorsement.

3. **Promotion gate** green (latency thresholds vs geometry reference in `summary.json`, per finalize rules).

4. **Artifact validation** passes on the run directory; copy the validated bundle to `benchmarks/published_runs/<run_id>/` before merge (see [`benchmarks/published_runs/README.md`](../benchmarks/published_runs/README.md)).

5. **Governance sequence:** `finalize_cli` (with `--parity-summary-path` pointing at `parity_summary.json`) → add `governance_decision.md` from [`benchmarks/templates/governance_decision.template.md`](../benchmarks/templates/governance_decision.template.md) to the **same** directory you will pass to `release_cli` (required for real publish; not for `--dry-run`) → `release_cli` (dry-run then real) → `audit_cli --strict`. Details: [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md), [`benchmarks/published_runs/README.md`](../benchmarks/published_runs/README.md).

Reference-only publishes (no native row in `summary.json`) may still show green parity for the reference stream; they do **not** prove native-arm promotion.

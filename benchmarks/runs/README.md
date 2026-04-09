# Benchmark run directories

Validated governed bundles live here as `benchmarks/runs/<run_id>/` after you run `python -m conicshield.bench.reference_run --out ...`.

**Chained path (offline export → bank → bundle):** on a licensed host, build from a real or fixture export with:

```bash
python scripts/produce_reference_bundle.py \
  --export-json tests/fixtures/offline_graph_export_minimal.json \
  --run-id canonical-from-minimal-export \
  --no-passthrough
```

Use `--passthrough` only for structural CI smoke (not for parity promotion or publish).

## P0 checklist (licensed host → governed publish)

Operational sequence (full detail in [`docs/MAINTAINER_RUNBOOK.md`](../../docs/MAINTAINER_RUNBOOK.md)):

1. Produce a **non-passthrough** bundle under `benchmarks/runs/<run_id>/` (real `CVXPY`/`MOREAU` arms).
2. `python -m conicshield.artifacts.validator_cli --run-dir benchmarks/runs/<run_id>`.
3. Promote parity: `python scripts/regenerate_parity_fixture.py --source benchmarks/runs/<run_id>` and update [`tests/fixtures/parity_reference/REGENERATION_NOTE.md`](../../tests/fixtures/parity_reference/REGENERATION_NOTE.md).
4. Parity CLI / pytest gates per [`docs/PARITY_AND_FIXTURES.md`](../../docs/PARITY_AND_FIXTURES.md); keep `parity_summary.json` for the next step.
5. `finalize_cli` (with `--parity-summary-path` when native parity applies, and `--current-release-path` as needed). Writes `governance_status.json`; does **not** require `governance_decision.md`.
6. Copy the validated bundle to [`benchmarks/published_runs/<run_id>/`](../published_runs/README.md) before merge if your workflow keeps a canonical published copy (recommended once `CURRENT.json` will reference this `run_id`).
7. Add `governance_decision.md` from [`benchmarks/templates/governance_decision.template.md`](../templates/governance_decision.template.md) to the **same directory you pass to `release_cli`** (after the copy, update both trees if you use two). Required for **`release_cli` without `--dry-run`** only; not read by `finalize_cli` or `release_cli --dry-run`.
8. `release_cli ... --dry-run`, then `release_cli` (real) → `audit_cli --strict`.

After a run is already published, you can refresh `CURRENT.json` gate fields (same `current_run_id`) with `python -m conicshield.governance.finalize_cli ... --parity-summary-path ... --current-release-path ... --sync-current-release` (see [`docs/MAINTAINER_RUNBOOK.md`](../../docs/MAINTAINER_RUNBOOK.md)).

Rehearsal without mutating `CURRENT.json`: `python scripts/first_governance_publish_dry_run.py --run-dir ...` (optional `--parity-summary-path` when native parity evidence exists).

## Layout

Each run directory should pass `validate_run_bundle` and typically contains at least:

- `config.json`, `summary.json`, `episodes.jsonl`, `transition_bank.json`
- Schema sidecars copied by `reference_run` (`*.schema.json`)

After validation, you can emit a Layer G report: `python scripts/artifact_validation_report.py --run-dir benchmarks/runs/<run_id>` (see [docs/VERIFICATION_AND_STRESS_TEST_PLAN.md](../../docs/VERIFICATION_AND_STRESS_TEST_PLAN.md)).

## Promotion to parity fixture

When a run is approved for native parity regression testing, promote it with:

```bash
python scripts/regenerate_parity_fixture.py --source benchmarks/runs/<run_id>
```

See [`docs/PARITY_AND_FIXTURES.md`](../docs/PARITY_AND_FIXTURES.md) for the fixture promotion checklist.

## Git policy

Ephemeral run directories under `benchmarks/runs/` are ignored by default (see `.gitignore` here) so local and CI rehearsal bundles are not committed.

**Published runs:** once a `run_id` is listed in a family `CURRENT.json`, commit the validated bundle under [`benchmarks/published_runs/<run_id>/`](../published_runs/README.md) so release metadata and on-disk artifacts stay auditable together. Tools resolve `published_runs` first, then `runs/`.

The parity **fixture** under `tests/fixtures/parity_reference/` is the minimal frozen contract kept in-repo for CI until promoted from a real governed bundle.

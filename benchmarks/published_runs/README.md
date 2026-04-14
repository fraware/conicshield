# Published benchmark bundles (`benchmarks/published_runs/`)

**Canonical committed copies** of governed runs live here as `benchmarks/published_runs/<run_id>/` once a family publishes that `run_id` (see `benchmarks/releases/<family_id>/CURRENT.json`). Produce the bundle first under `benchmarks/runs/<run_id>/` with `python -m conicshield.bench.reference_run --out ...`, validate, finalize, then copy here before merge so artifacts stay auditable with release metadata. Tools resolve `published_runs/<run_id>` before `runs/<run_id>` when both exist.

**Auditing after clone:** from the repository root, integrity checks for indexed files are enforced in CI via `tests/governance/test_published_run_index.py` (SHA-256 vs disk for **every indexed file**, **`assert_index_includes_required_hashes`** for the validator-required bundle surface, full `validate_run_bundle` on each run, and parity `REGENERATION_NOTE.md` run ids listed in the index). **`tests/governance/test_native_arm_publish_evidence.py`** asserts the family `CURRENT.json` `current_run_id` bundle’s `summary.json` still contains a `shielded-native-moreau` row with plausible timings (guards drift after publish). Locally:

```bash
python scripts/refresh_published_run_index.py --check
```

```bash
python -c "from pathlib import Path; from conicshield.published_run_index import assert_parity_note_run_ids_indexed, verify_index_integrity; verify_index_integrity(repo_root=Path('.')); assert_parity_note_run_ids_indexed(repo_root=Path('.')); print('index ok')"
```

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
5. `finalize_cli` (pass `--parity-summary-path` to your `parity_summary.json` when native parity applies, and `--current-release-path` as needed). This writes `governance_status.json` under the run dir; it does **not** require `governance_decision.md`.
6. Copy the validated bundle to `benchmarks/published_runs/<run_id>/` (or publish from `benchmarks/runs/<run_id>/` if you do not use `published_runs`; use the **same** path for `release_cli` and keep it consistent).
7. Add `governance_decision.md` from [`benchmarks/templates/governance_decision.template.md`](../templates/governance_decision.template.md) to **that same run directory** and replace placeholders. Required only for a **real** publish: `release_cli` without `--dry-run` calls `publish_from_governance_status`, which errors if this file is missing. **`release_cli --dry-run` and `finalize_cli` do not read it.**
8. `python -m conicshield.governance.release_cli ... --dry-run`, then the same command **without** `--dry-run` → `python -m conicshield.governance.audit_cli --strict`.

**Summary telemetry:** `summary.json` rows use the same solver-status rules as `conicshield.bench.metrics.step_solver_status_is_failure` (for example ECOS-style optimal code `"1"` is **not** a solve failure). If you change solver backends, re-run `reference_run` so `summary.json` stays consistent with `episodes.jsonl`.

After a run is already published, you can refresh `CURRENT.json` gate fields (same `current_run_id`) with `python -m conicshield.governance.finalize_cli ... --parity-summary-path ... --current-release-path ... --sync-current-release` (see [`docs/MAINTAINER_RUNBOOK.md`](../../docs/MAINTAINER_RUNBOOK.md)).

Rehearsal without mutating `CURRENT.json`: `python scripts/first_governance_publish_dry_run.py --run-dir ...` (optional `--parity-summary-path` when native parity evidence exists).

## Layout

Each run directory should pass `validate_run_bundle` and typically contains at least:

- `config.json`, `summary.json`, `episodes.jsonl`, `transition_bank.json`
- `governance_status.json` (from `finalize_cli`); `governance_decision.md` (human record, required in-tree before real `release_cli`)
- Schema sidecars copied by `reference_run` (`*.schema.json`)

After validation, you can emit a Layer G report: `python scripts/artifact_validation_report.py --run-dir benchmarks/published_runs/<run_id>` (see [docs/VERIFICATION_AND_STRESS_TEST_PLAN.md](../../docs/VERIFICATION_AND_STRESS_TEST_PLAN.md)).

## Promotion to parity fixture

When a run is approved for native parity regression testing, promote it with:

```bash
python scripts/regenerate_parity_fixture.py --source benchmarks/runs/<run_id>
```

See [`docs/PARITY_AND_FIXTURES.md`](../../docs/PARITY_AND_FIXTURES.md) for the fixture promotion checklist.

## Host-realistic rehearsal (full loop)

Closing the loop from environment data to an auditable published bundle: **export → transition bank → `reference_run` → validate → copy to `benchmarks/published_runs/<run_id>/` → finalize / release / audit**, with optional parity fixture refresh from that bundle. Orchestrate steps with [`scripts/governed_local_promotion.py`](../../scripts/governed_local_promotion.py) (`validate`, `parity-sync`, `index`, `all`) and [`docs/MAINTAINER_RUNBOOK.md`](../../docs/MAINTAINER_RUNBOOK.md). Use a real upstream export when proving inter-sim integration; minimal offline exports remain valid for structural smoke only.

## Git policy

Ephemeral run directories under `benchmarks/runs/` are ignored by default (see `.gitignore` under `benchmarks/runs/`) so local and CI rehearsal bundles are not committed.

**Published runs:** once a `run_id` is listed in a family `CURRENT.json`, commit the validated bundle under `benchmarks/published_runs/<run_id>/` so release metadata and on-disk artifacts stay auditable together. Tools resolve `published_runs` first, then `runs/`.

**Whitelist:** [`.gitignore`](.gitignore) ignores unknown paths under this directory. Add `!your-run-id/` and `!your-run-id/**` when committing a new canonical bundle, and add those paths to `benchmark_bundle_paths` in the family `CURRENT.json` (preserved across `release_cli` publishes).

**Discoverability:** `benchmarks/releases/<family_id>/CURRENT.json` may list `benchmark_bundle_paths` pointing at committed trees for reviewers. **`benchmarks/PUBLISHED_RUN_INDEX.json`** (schema version ≥ 2) lists governed `run_id` values with `repository_relative_path` and SHA-256 for **every `validate_run_bundle` required file** (`config.json`, schemas, `summary.json`, `episodes.jsonl`, `transition_bank.json`) plus optional governance, provenance, `README.md`, etc., when present. Regenerate with `python scripts/refresh_published_run_index.py` after changing a canonical bundle; CI runs `python scripts/refresh_published_run_index.py --check` and [`tests/governance/test_published_run_index.py`](../../tests/governance/test_published_run_index.py).

The parity **fixture** under `tests/fixtures/parity_reference/` is the frozen CI contract; it is regenerated from a validated governed bundle (see `REGENERATION_NOTE.md` there and `benchmarks/PUBLISHED_RUN_INDEX.json` for bundle integrity).

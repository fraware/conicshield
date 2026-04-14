# Parity and frozen fixtures

How the frozen parity fixture is governed, how native code is checked against it, and how to refresh it from a validated governed reference bundle.

**Current fixture status:** The checked-in stream under `tests/fixtures/parity_reference/` is **promoted from a committed governed bundle** (`benchmarks/published_runs/wsl-real-20260409-132450/`), not a placeholder bootstrap stream. See [`tests/fixtures/parity_reference/REGENERATION_NOTE.md`](../tests/fixtures/parity_reference/REGENERATION_NOTE.md) for the exact promotion record. Integrity of governed bundles in-repo is listed in [`benchmarks/PUBLISHED_RUN_INDEX.json`](../benchmarks/PUBLISHED_RUN_INDEX.json) (regenerate with `python scripts/refresh_published_run_index.py` after changing files under `benchmarks/published_runs/`).

**See also:** [BENCHMARK_GOVERNANCE.md](BENCHMARK_GOVERNANCE.md), [MAINTAINER_RUNBOOK.md](MAINTAINER_RUNBOOK.md), [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md) (native parity layer).

**CI regression:** `tests/governance/test_published_run_index.py` checks `benchmarks/PUBLISHED_RUN_INDEX.json` against on-disk files and ensures every `run_id` cited in `tests/fixtures/parity_reference/REGENERATION_NOTE.md` appears in the index’s governed list. Run `python scripts/refresh_published_run_index.py --check` (or `--write`) after changing bundles or the index.

---

## Frozen fixture policy

The parity fixture under `tests/fixtures/parity_reference/` is a versioned benchmark artifact. It must only be regenerated when:

- reference shield semantics change intentionally, or
- reference compiler or input-stream semantics change intentionally, or
- a semantic-preserving refresh is explicitly approved.

Do **not** regenerate it only to make native parity pass.

Required companion files include `FIXTURE_MANIFEST.json`, `REGENERATION_NOTE.md`, and the reference bundle artifacts.

---

## Native parity

The native compiled path (`Backend.NATIVE_MOREAU`) is not treated as equivalent to the reference shield path until it passes **parity gates** on the frozen reference stream.

**Replay / CLI thresholds** for comparing native steps to the reference stream live in `conicshield.parity.gates` (`list_default_parity_gate_violations`, `enforce_default_parity_gates`). **Governance** parity for `finalize_cli` uses the numeric checks in `conicshield.governance.finalize` (they should agree on pass/fail for the same `parity_summary.json`). Do not copy threshold numbers into other documents without pointing to those modules.

**Protocol:**

1. Frozen reference: `tests/fixtures/parity_reference/` (episodes, config, transition bank).
2. Replay: `python -m conicshield.parity.cli --reference-dir ... --out-dir ...`
3. Artifacts: `parity_summary.json`, `parity_steps.jsonl`; optional `parity_report.md` via `scripts/generate_parity_report.py` or `make parity-report`.

**Makefile:** `make parity-native-licensed` (requires license and native stack); `make parity-report` after a run.

If parity fails, the native compiled arm is not listed under `publishable_arms` for native endorsement until resolved. Reference-only runs can still show `parity_gate: "green"` when `parity_summary.json` from `parity.cli` passes finalize thresholds.

Performance claims are separate from parity; see [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md).

---

## Replacing the bootstrap fixture

Use this when promoting a **real** reference run (CVXPY + Moreau, not `--passthrough-projector`) into `tests/fixtures/parity_reference`.

**Preconditions**

- Licensed solver stack installed (`pip install -e ".[solver,dev]"` with the vendor index).
- Transition bank JSON validated for the task.
- A green solver run (local or manual **Vendor CI** `vendor-ci-moreau`) is a strong signal before committing fixture bytes.

**Steps**

1. Produce a reference bundle:

   ```bash
   python -m conicshield.bench.reference_run \
     --out benchmarks/runs/<run_id> \
     --bank /path/to/transition_bank.json
   ```

2. Validate:

   ```bash
   python -m conicshield.artifacts.validator_cli --run-dir benchmarks/runs/<run_id>
   ```

3. Review `summary.json`, shield metrics, and reproducibility fields.

4. Promote:

   ```bash
   python scripts/regenerate_parity_fixture.py --source benchmarks/runs/<run_id>
   ```

   Run bundles from `reference_run` / `produce_reference_bundle` do not include `FIXTURE_MANIFEST.json` or `REGENERATION_NOTE.md`; the script copies those from the existing `tests/fixtures/parity_reference/` tree when they are absent on the source (and skips self-copy when source and destination are the same path).

5. If your workflow uses it:

   ```bash
   python -m conicshield.parity.regenerate_fixture --reference-dir tests/fixtures/parity_reference
   ```

6. Update `tests/fixtures/parity_reference/REGENERATION_NOTE.md` with what changed and why.

7. Verify before merge:

   ```bash
   make validate-fixture
   pytest tests/test_fixture_policy.py tests/test_regenerate_parity_fixture_script.py tests/parity/test_parity_layout_smoke.py -q
   python -m conicshield.parity.cli \
     --reference-dir tests/fixtures/parity_reference \
     --reference-arm-label shielded-rules-plus-geometry \
     --out-dir /tmp/native_parity_local
   ```

**Governance parity evidence:** `conicshield.governance.finalize_cli` can take `--parity-summary-path` pointing at `parity_summary.json` from step 7. Thresholds are evaluated in `conicshield.governance.finalize` (same numeric checks as historical native-arm flow). Green parity does not require a `shielded-native-moreau` row in the benchmark `summary.json` when this file is supplied; adding the native arm to `publishable_arms` still requires that arm in `summary.json` and passing gates. After an initial publish, refresh gate columns on `benchmarks/releases/.../CURRENT.json` with `finalize_cli ... --sync-current-release` (see [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md)); do not edit `CURRENT.json` by hand.

**Do not**

- Promote bundles built with `--passthrough-projector` as the canonical parity reference.
- Edit `CURRENT.json` by hand except via governed tooling (`release_cli` / `finalize_cli --sync-current-release`).

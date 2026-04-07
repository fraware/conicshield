# Parity and frozen fixtures

How the frozen parity fixture is governed, how native code is checked against it, and how to replace the bootstrap fixture with a real reference run.

**See also:** [BENCHMARK_GOVERNANCE.md](BENCHMARK_GOVERNANCE.md), [MAINTAINER_RUNBOOK.md](MAINTAINER_RUNBOOK.md), [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md) (native parity layer).

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

**Canonical thresholds** live in code (`conicshield.parity.gates` — `list_default_parity_gate_violations`, `enforce_default_parity_gates`). Do not copy threshold numbers into other documents without pointing to that module.

**Protocol:**

1. Frozen reference: `tests/fixtures/parity_reference/` (episodes, config, transition bank).
2. Replay: `python -m conicshield.parity.cli --reference-dir ... --out-dir ...`
3. Artifacts: `parity_summary.json`, `parity_steps.jsonl`; optional `parity_report.md` via `scripts/generate_parity_report.py` or `make parity-report`.

**Makefile:** `make parity-native-licensed` (requires license and native stack); `make parity-report` after a run.

If parity fails, the native arm is not publishable for native endorsement until resolved.

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

5. If your workflow uses it:

   ```bash
   python -m conicshield.parity.regenerate_fixture --reference-dir tests/fixtures/parity_reference
   ```

6. Update `tests/fixtures/parity_reference/REGENERATION_NOTE.md` with what changed and why.

7. Verify before merge:

   ```bash
   make validate-fixture
   pytest tests/test_parity_replay.py -q
   python -m conicshield.parity.cli \
     --reference-dir tests/fixtures/parity_reference \
     --reference-arm-label shielded-rules-plus-geometry \
     --out-dir /tmp/native_parity_local
   ```

**Do not**

- Promote bundles built with `--passthrough-projector` as the canonical parity reference.
- Edit `CURRENT.json` by hand; use release orchestration after gates are green.

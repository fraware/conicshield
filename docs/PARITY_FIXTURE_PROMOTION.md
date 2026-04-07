# Parity fixture promotion (M4)

This checklist ties the governed benchmark bundle to `tests/fixtures/parity_reference`. Follow it when replacing the bootstrap fixture with a **real** reference run (CVXPY + Moreau, not `--passthrough-projector`).

## Preconditions

- Licensed solver stack installed (`pip install -e ".[solver,dev]"` with Gemfury index).
- Transition bank JSON validated for the task (from `build_transition_bank` or `--from-offline-graph-export`).
- Green local or **Vendor CI track** (`vendor-ci-moreau`) run for solver-marked tests is a strong signal before you commit fixture bytes.

## Steps

1. **Produce a reference bundle** (real projector):

   ```bash
   python -m conicshield.bench.reference_run \
     --out benchmarks/runs/<run_id> \
     --bank /path/to/transition_bank.json
   ```

   Optional: add `--include-native-arm` when you also need native episodes in the same bundle for downstream gates (not required for parity CLI, which replays native against the reference arm).

2. **Validate artifacts**:

   ```bash
   python -m conicshield.artifacts.validator_cli --run-dir benchmarks/runs/<run_id>
   ```

3. **Human review**: inspect `summary.json`, shield metrics, and reproducibility fields; confirm intentional changes.

4. **Promote into the test fixture**:

   ```bash
   python scripts/regenerate_parity_fixture.py --source benchmarks/runs/<run_id>
   ```

5. **Regenerate parity-derived files** (if your workflow uses this step):

   ```bash
   python -m conicshield.parity.regenerate_fixture --reference-dir tests/fixtures/parity_reference
   ```

6. **Update** `tests/fixtures/parity_reference/REGENERATION_NOTE.md` with what changed and why (required by fixture policy).

7. **Verify** before merge:

   ```bash
   make validate-fixture
   pytest tests/test_parity_replay.py -q
   python -m conicshield.parity.cli \
     --reference-dir tests/fixtures/parity_reference \
     --reference-arm-label shielded-rules-plus-geometry \
     --out-dir /tmp/native_parity_local
   ```

## What not to do

- Do not promote bundles produced with `--passthrough-projector` as the canonical parity reference; they skip the real QP path.
- Do not edit `CURRENT.json` by hand; use release orchestration after governance gates are green.

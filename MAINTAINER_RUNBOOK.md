# ConicShield Benchmark Maintainer Runbook

This runbook describes the operational procedures for maintaining the ConicShield benchmark system.

It is the human companion to:
- `BENCHMARK_GOVERNANCE.md`
- the artifact validator
- fixture policy
- native parity gate
- promotion policy
- family manifests
- release orchestration
- governance audit
- governance dashboard

The benchmark system is governed. Do not bypass these procedures informally.

## Core principle

A benchmark result is a governed claim about a stable task.

When something changes, always determine which layer changed:
1. implementation
2. reference fixture
3. task contract

Do not treat those as interchangeable.

## Quick decision tree

### Case A: CI is red on native parity
Ask:
- Did the implementation change?
- Did the fixture change?
- Did the task contract change?

### Case B: benchmark run validates but is not promotable
Ask which gate is red:
- parity
- promotion
- review-lock compatibility
- artifact validation

### Case C: a semantic change is intentional
Do not publish into the current family. Start family-bump procedure.

### Case D: fixture needs regeneration
Use the fixture regeneration procedure. Do not overwrite the fixture casually.

### Case E: a run appears good and all gates are green
Use release orchestration. Do not edit `CURRENT.json` manually.

## Standard commands

### Validate a run bundle
```bash
python -m conicshield.artifacts.validator_cli --run-dir benchmarks/runs/<run_id>
```

### Validate the parity fixture
```bash
python -m conicshield.parity.regenerate_fixture --reference-dir tests/fixtures/parity_reference
```

### Run native parity against the frozen fixture
```bash
python -m conicshield.parity.cli   --reference-dir tests/fixtures/parity_reference   --reference-arm-label shielded-rules-plus-geometry   --out-dir output/native_parity_ci
```

### Finalize governance status for a run
```bash
python -m conicshield.governance.finalize_cli   --run-dir benchmarks/runs/<run_id>   --family-id conicshield-transition-bank-v1   --task-contract-version v1   --fixture-version fixture-v1   --reference-fixture-dir tests/fixtures/parity_reference   --parity-summary-path output/native_parity_ci/parity_summary.json   --current-release-path benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json
```

### Dry-run release decision
```bash
python -m conicshield.governance.release_cli   --run-dir benchmarks/runs/<run_id>   --family-id conicshield-transition-bank-v1   --reason "candidate release review"   --dry-run
```

### Publish same-family release
```bash
python -m conicshield.governance.release_cli   --run-dir benchmarks/runs/<run_id>   --family-id conicshield-transition-bank-v1   --reason "promoted after green artifact, parity, and promotion gates"
```

### Publish with family bump
```bash
python -m conicshield.governance.release_cli   --run-dir benchmarks/runs/<run_id>   --family-id conicshield-transition-bank-v1   --reason "new task contract requires family fork"   --allow-family-bump
```

### Audit the whole governance tree
```bash
python -m conicshield.governance.audit_cli --strict
```

### Generate the governance dashboard
```bash
python -m conicshield.governance.dashboard_cli   --json-output output/governance_dashboard.json   --markdown-output output/governance_dashboard.md
```

## Incident playbooks

### Native parity failure
Freeze publication of any run that endorses `shielded-native-moreau`. Inspect parity artifacts and recent changes.

### Artifact validation failure
Treat the run as invalid. Do not review performance claims yet.

### Promotion gate failure
Keep the run as candidate. Do not publish.

### Family compatibility failure
The task changed materially. Do not overwrite the current family.

### Fixture regeneration request
Allowed only for deliberate reference-side reasons. Never regenerate to make parity green.

## What maintainers must never do

- Never edit `CURRENT.json` manually to publish a run
- Never regenerate the fixture casually
- Never promote a run with red artifact, promotion, or required parity gates
- Never overwrite a family when the task contract changed
- Never use a live benchmark run as the parity reference
- Never bypass the run-finalization step

## Triage priorities

1. artifact validity
2. fixture validity
3. parity validity
4. family compatibility
5. promotion thresholds
6. publication state
7. dashboard cosmetics

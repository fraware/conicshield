PYTHON ?= python

.PHONY: test test-reference test-slow test-solver test-vendor-moreau smoke-solver smoke-check env-check reference-correctness perf-benchmark diff-check trust-dashboard parity-native-licensed artifact-validation-report parity-report audit dashboard validate-fixture lint typecheck format format-check cov cov-gates compile-deps verify-extended bootstrap-moreau

test:
	$(PYTHON) -m pytest -q

test-reference:
	$(PYTHON) -m pytest tests/ -q -m "not vendor_moreau and not requires_moreau and not inter_sim_rl and not slow"

test-slow:
	$(PYTHON) -m pytest tests/ -q -m "slow"

test-solver:
	$(PYTHON) -m pytest tests/ -q -m "solver or requires_moreau"

test-vendor-moreau:
	$(PYTHON) -m pytest tests/ -q -m "vendor_moreau or requires_moreau"

smoke-solver:
	$(PYTHON) -m conicshield.core.solver_smoke_cli

env-check:
	$(PYTHON) scripts/environment_check.py

smoke-check:
	$(PYTHON) scripts/smoke_check.py

reference-correctness:
	$(PYTHON) scripts/reference_correctness_summary.py

perf-benchmark:
	$(PYTHON) scripts/performance_benchmark.py

diff-check:
	$(PYTHON) scripts/differentiation_check.py

trust-dashboard:
	$(PYTHON) scripts/generate_trust_dashboard.py

parity-native-licensed:
	$(PYTHON) -m conicshield.parity.cli \
		--reference-dir tests/fixtures/parity_reference \
		--reference-arm-label shielded-rules-plus-geometry \
		--out-dir output/native_parity_local

artifact-validation-report:
	$(PYTHON) scripts/artifact_validation_report.py --run-dir tests/fixtures/parity_reference

parity-report:
	$(PYTHON) scripts/generate_parity_report.py \
		--parity-summary output/native_parity_local/parity_summary.json \
		--out-dir output/native_parity_local

lint:
	$(PYTHON) -m ruff check conicshield tests

typecheck:
	$(PYTHON) -m mypy conicshield tests

format:
	$(PYTHON) -m ruff format conicshield tests

format-check:
	$(PYTHON) -m ruff format --check conicshield tests

cov:
	$(PYTHON) -m pytest tests/ -q --cov=conicshield --cov-report=term-missing

cov-gates:
	$(PYTHON) -m pytest tests/ -q \
		--cov=conicshield.adapters.inter_sim_rl \
		--cov=conicshield.bench \
		--cov=conicshield.parity \
		--cov=conicshield.artifacts \
		--cov=conicshield.governance \
		--cov-report=term-missing \
		--cov-fail-under=76

# Tiered local verification (stricter than default CI): static + cov-gates + slow + inter_sim_rl + strict audit.
# Does not run solver-marked tests or Hypothesis modules; use make test-solver and optional Hypothesis pytest after pip install hypothesis.
verify-extended:
	$(PYTHON) -m ruff check conicshield tests
	$(PYTHON) -m ruff format --check conicshield tests
	$(PYTHON) -m mypy conicshield tests
	$(PYTHON) -m pytest tests/ -q \
		--cov=conicshield.adapters.inter_sim_rl \
		--cov=conicshield.bench \
		--cov=conicshield.parity \
		--cov=conicshield.artifacts \
		--cov=conicshield.governance \
		--cov-report=term-missing \
		--cov-fail-under=76
	$(PYTHON) -m pytest tests/ -q -m "slow"
	$(PYTHON) -m pytest tests/test_inter_sim_rl_e2e.py -q --override-ini "addopts=-q --durations=15"
	$(PYTHON) -m conicshield.governance.audit_cli --strict

compile-deps:
	$(PYTHON) -m piptools compile --extra dev -o requirements-dev.txt pyproject.toml --no-strip-extras

audit:
	$(PYTHON) -m conicshield.governance.audit_cli --strict

dashboard:
	$(PYTHON) -m conicshield.governance.dashboard_cli \
		--json-output output/governance_dashboard.json \
		--markdown-output output/governance_dashboard.md

validate-fixture:
	$(PYTHON) -m conicshield.parity.regenerate_fixture --reference-dir tests/fixtures/parity_reference

bootstrap-moreau:
	bash scripts/bootstrap_moreau.sh

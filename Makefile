# Cross-platform interpreter for Make targets.
# Git Bash + a WSL-created .venv exposes `python` -> /usr/bin/python.exe (broken on Windows).
# Prefer .venv/Scripts/python.exe on MSYS, else the Windows `py` launcher, else python3.
ifdef MSYSTEM
  ifdef VIRTUAL_ENV
    ifneq ($(wildcard $(VIRTUAL_ENV)/Scripts/python.exe),)
      PYTHON ?= $(VIRTUAL_ENV)/Scripts/python.exe
    else
      PYTHON ?= $(shell py -3 -c "import sys; print(sys.executable)" 2>/dev/null || command -v python3 2>/dev/null || echo python)
    endif
  else
    PYTHON ?= $(shell py -3 -c "import sys; print(sys.executable)" 2>/dev/null || command -v python3 2>/dev/null || echo python)
  endif
else
  ifdef VIRTUAL_ENV
    ifneq ($(wildcard $(VIRTUAL_ENV)/bin/python),)
      PYTHON ?= $(VIRTUAL_ENV)/bin/python
    else ifneq ($(wildcard $(VIRTUAL_ENV)/Scripts/python.exe),)
      PYTHON ?= $(VIRTUAL_ENV)/Scripts/python.exe
    endif
  endif
  ifeq ($(OS),Windows_NT)
    PYTHON ?= python
  else
    PYTHON ?= python3
  endif
endif

.PHONY: test test-reference test-slow test-solver test-vendor-moreau smoke-solver smoke-check env-check reference-correctness perf-benchmark diff-check trust-dashboard parity-native-licensed artifact-validation-report parity-report audit dashboard validate-fixture lint typecheck format format-check cov cov-gates compile-deps verify-extended bootstrap-moreau upgrade-host-realistic-vendor host-realistic-rehearsal export-upstream-rehearsal batch-solve-report check-batch-acceptance check-batch-throughput-advisory validate-published-bundle-profile sync-community-metadata sync-published-run-readmes sync-published-readmes finalize-community-dataset community-verify check-reference-refresh-cadence check-flagship-full-refresh-cadence verify-v1-lock verify-v1-lock-quick v1-status onboard verify-reference-system reference-authority-check reference-authority-snapshot reference-system-status reference-system-status-check capture-inter-sim-graph refresh-live-upstream-export refresh-live-upstream-export-live host-realistic-refresh-cycle host-realistic-refresh-cycle-licensed host-realistic-refresh-milestone sync-published-readmes

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
	$(PYTHON) scripts/performance_benchmark.py --batch-size 4
	$(PYTHON) scripts/batch_solve_report.py
	$(PYTHON) scripts/check_batch_acceptance.py

batch-solve-report:
	$(PYTHON) scripts/batch_solve_report.py

check-batch-acceptance:
	$(PYTHON) scripts/check_batch_acceptance.py --tier viability

check-batch-throughput-advisory:
	$(PYTHON) scripts/check_batch_acceptance.py --tier throughput_advisory

validate-published-bundle-profile:
	$(PYTHON) scripts/validate_published_bundle_profile.py

host-realistic-refresh-cycle:
	$(PYTHON) scripts/host_realistic_refresh_cycle.py --record-refresh --trigger calendar-cadence

host-realistic-refresh-cycle-licensed: capture-inter-sim-graph refresh-live-upstream-export-live
	$(PYTHON) scripts/host_realistic_refresh_cycle.py --record-refresh --amend-last-refresh --trigger calendar-cadence --run-id host-realistic-20260525 --force

host-realistic-refresh-milestone:
	$(PYTHON) scripts/host_realistic_refresh_cycle.py --new-milestone --promote-release --force

sync-published-readmes: sync-published-run-readmes

host-realistic-rehearsal:
	$(PYTHON) scripts/run_host_realistic_publish.py \
		--export-json benchmarks/external_evidence/offline_graph_export_upstream.json \
		--run-id host-realistic-rehearsal \
		--passthrough

export-upstream-rehearsal:
	$(PYTHON) scripts/export_inter_sim_offline_graph.py \
		--rehearsal-fork \
		--out benchmarks/external_evidence/offline_graph_export_upstream.json

upgrade-host-realistic-vendor:
	$(PYTHON) scripts/upgrade_host_realistic_vendor.py --force

reference-authority-check:
	$(PYTHON) scripts/reference_authority_check.py

reference-system-status:
	$(PYTHON) scripts/generate_reference_system_status.py

reference-system-status-check:
	$(PYTHON) scripts/generate_reference_system_status.py --check

reference-authority-snapshot:
	$(PYTHON) scripts/generate_reference_authority_snapshot.py

capture-inter-sim-graph:
	$(PYTHON) scripts/capture_inter_sim_offline_graph.py \
		--host-realistic-fork \
		--out benchmarks/external_evidence/live_dumps/offline_transition_graph_host_realistic.json

refresh-live-upstream-export:
	@echo "Usage: make capture-inter-sim-graph && make refresh-live-upstream-export-live"
	@echo "  or: $(PYTHON) scripts/refresh_live_upstream_export.py --graph-json <path>"

refresh-live-upstream-export-live: capture-inter-sim-graph
	$(PYTHON) scripts/refresh_live_upstream_export.py \
		--graph-json benchmarks/external_evidence/live_dumps/offline_transition_graph_host_realistic.json

verify-v1-lock: verify-reference-system community-verify reference-system-status-check
	$(PYTHON) scripts/refresh_published_run_index.py --check
	$(PYTHON) scripts/verify_v1_lock.py

verify-v1-lock-quick:
	$(PYTHON) scripts/verify_v1_lock.py

v1-status:
	$(PYTHON) scripts/print_v1_status.py

onboard: community-verify v1-status
	@echo ""
	@echo "Community onboarding OK. Next: docs/COMMUNITY_LAYER.md"

sync-community-metadata:
	$(PYTHON) scripts/sync_community_metadata.py

sync-published-run-readmes:
	$(PYTHON) scripts/sync_published_run_readmes.py

finalize-community-dataset:
	$(PYTHON) scripts/finalize_community_dataset.py

community-verify:
	$(PYTHON) -m pytest tests/test_published_runs_api.py tests/test_published_runs_cli.py tests/examples/test_public_examples_smoke.py -q --tb=short
	$(PYTHON) -m conicshield.published_runs.cli list
	$(PYTHON) -m conicshield.published_runs.cli verify host-realistic-20260525

check-reference-refresh-cadence:
	$(PYTHON) scripts/check_reference_refresh_cadence.py --max-days 35

check-flagship-full-refresh-cadence:
	$(PYTHON) scripts/check_flagship_full_refresh_cadence.py --max-days 35

verify-reference-system: reference-authority-check reference-system-status-check check-flagship-full-refresh-cadence validate-published-bundle-profile sync-community-metadata
	$(PYTHON) -m pytest \
		tests/governance/test_published_run_index.py \
		tests/governance/test_host_realistic_publish_evidence.py \
		tests/governance/test_reference_evidence_tiers.py \
		tests/governance/test_reference_authority_invariants.py \
		tests/governance/test_conic_suite_report_clusters.py \
		tests/governance/test_published_run_catalog.py \
		tests/governance/test_check_batch_acceptance.py \
		tests/governance/test_validate_published_bundle_profile.py \
		tests/governance/test_native_arm_publish_evidence.py \
		tests/governance/test_native_batch_report_contract.py \
		tests/governance/test_community_metadata.py \
		tests/governance/test_reference_refresh_cadence.py \
		tests/governance/test_record_reference_refresh.py \
		tests/governance/test_reference_system_status.py \
		tests/governance/test_flagship_full_refresh_cadence.py \
		tests/governance/test_community_metadata_contract.py \
		tests/governance/test_published_run_readme_paths.py \
		tests/test_published_runs_api.py \
		tests/governance/test_run_host_realistic_publish.py \
		tests/governance/test_host_realistic_refresh_cycle.py \
		tests/governance/test_batch_solve_report.py \
		tests/bench/test_inter_sim_export.py \
		tests/scripts/test_export_inter_sim_cli.py \
		tests/core/test_solver_factory.py \
		-q --tb=short

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

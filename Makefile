PYTHON ?= python

.PHONY: test audit dashboard validate-fixture

test:
	$(PYTHON) -m pytest -q

audit:
	$(PYTHON) -m conicshield.governance.audit_cli --strict

dashboard:
	$(PYTHON) -m conicshield.governance.dashboard_cli \
		--json-output output/governance_dashboard.json \
		--markdown-output output/governance_dashboard.md

validate-fixture:
	$(PYTHON) -m conicshield.parity.regenerate_fixture --reference-dir tests/fixtures/parity_reference

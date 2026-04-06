from conicshield.governance.audit import audit_benchmark_tree


def test_audit_tree_runs() -> None:
    report = audit_benchmark_tree()
    payload = report.as_dict()
    assert "issues" in payload
    assert payload["families_checked"] >= 1

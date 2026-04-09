from conicshield.governance.audit import audit_benchmark_tree


def test_audit_tree_runs() -> None:
    report = audit_benchmark_tree()
    payload = report.as_dict()
    assert "issues" in payload
    assert payload["families_checked"] >= 1


def test_audit_unknown_family_is_error() -> None:
    report = audit_benchmark_tree(family_id="definitely-not-a-real-family-id")
    assert not report.ok
    assert any("not found" in i.message.lower() for i in report.issues)

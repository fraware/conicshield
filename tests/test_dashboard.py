from conicshield.governance.dashboard import build_governance_dashboard, render_markdown_dashboard


def test_dashboard_builds() -> None:
    dashboard = build_governance_dashboard()
    payload = dashboard.as_dict()
    assert "families" in payload
    assert isinstance(payload["families"], list)
    assert len(payload["families"]) >= 1
    md = render_markdown_dashboard(dashboard)
    assert "Benchmark Governance Dashboard" in md

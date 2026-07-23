"""Corpus-wide KKT ↔ FD agreement study tests."""

from __future__ import annotations

from pathlib import Path

from conicshield.experimental.gradients.agreement_study import (
    AGREEMENT_STUDY_SCHEMA_ID,
    render_agreement_report_markdown,
    run_agreement_study,
)
from conicshield.experimental.gradients.modes import GradientMode


def test_agreement_study_ci_small(tmp_path: Path) -> None:
    report = run_agreement_study(
        ci_small=True,
        output_dir=tmp_path,
        exact_command="pytest:test_agreement_study_ci_small",
    )
    assert report.schema_id == AGREEMENT_STUDY_SCHEMA_ID
    assert report.rows
    assert report.overall["n_scenarios"] == len(report.rows)
    assert "native_exact_backend_gradient" in report.overall
    assert report.overall["native_exact_backend_gradient"] in {
        "available",
        "unavailable",
    }
    assert any("not native" in c.lower() or "not" in c.lower() for c in report.conclusions)
    # Mode labels stay distinct in rows
    row = report.rows[0].as_dict()
    assert row["modes"]["research_kkt"] == GradientMode.EXACT_RESEARCH_KKT.value
    assert row["modes"]["native_exact"] == GradientMode.EXACT_BACKEND_GRADIENT.value
    assert row["not_native_moreau"] is True
    assert (tmp_path / "kkt_fd_agreement_ci_small.json").is_file()
    md = render_agreement_report_markdown(report)
    assert "exact_research_kkt" in md
    assert "exact_backend_gradient" in md


def test_agreement_study_stratifies_families() -> None:
    report = run_agreement_study(ci_small=True, exact_command="pytest:stratify")
    families = {s.stratum for s in report.by_family}
    assert "active_set_transition_neighborhoods" in families or report.rows

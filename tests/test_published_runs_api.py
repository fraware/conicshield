from __future__ import annotations

from conicshield.published_runs import (
    current_family_run,
    get_current_run,
    list_runs,
    load_provenance,
    load_run,
    load_summary,
    verify_run,
)


def test_list_and_load_flagship() -> None:
    ids = {e.run_id for e in list_runs()}
    assert "host-realistic-20260525" in ids
    bundle = load_run("host-realistic-20260525")
    assert bundle.path.name == "host-realistic-20260525"
    assert bundle.community is not None
    assert bundle.community.evidence_tier == "vendor_native"


def test_get_current_run() -> None:
    bundle = get_current_run("conicshield-transition-bank-v1")
    assert bundle.run_id == "host-realistic-20260525"
    assert current_family_run("conicshield-transition-bank-v1").run_id == bundle.run_id


def test_load_provenance_flagship() -> None:
    prov = load_provenance("host-realistic-20260525")
    assert prov.host_realistic_evidence is True
    assert prov.projector_mode == "real_projector"


def test_verify_flagship() -> None:
    verify_run("host-realistic-20260525")


def test_load_summary_has_native_arm() -> None:
    labels = {r.label for r in load_summary("host-realistic-20260525")}
    assert "shielded-native-moreau" in labels

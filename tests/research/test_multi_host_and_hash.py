"""Wave 7: multi-host soak simulation + governed hash research adapter."""

from __future__ import annotations

from pathlib import Path

from conicshield.experimental.assurance.governed_hash_policy import (
    GOVERNED_HASH_POLICY_SCHEMA_ID,
    check_governed_hashes,
    default_governed_hash_policy,
)
from conicshield.experimental.assurance.multi_host_soak_sim import (
    MULTI_HOST_SIM_SCHEMA_ID,
    run_multi_host_soak_simulation,
    synthesize_second_host_report,
)


def test_governed_hash_policy_research_only() -> None:
    pol = default_governed_hash_policy()
    assert pol.schema_id == GOVERNED_HASH_POLICY_SCHEMA_ID
    assert pol.production_release_integrated is False
    ok = check_governed_hashes(
        artifact_hashes={"assurance_bundle.json": "a" * 64, "provenance.json": "b" * 64},
        sealed_corrected_action_digest="c" * 64,
        dirty_worktree=False,
        peer_sealed_digests=["c" * 64],
    )
    assert ok.passed is True
    assert any("production" in b.lower() for b in ok.blockers)
    assert ok.as_dict()["production_claim"] is False


def test_governed_hash_flags_mismatch_and_dirty() -> None:
    bad = check_governed_hashes(
        artifact_hashes={"assurance_bundle.json": "a" * 64},
        sealed_corrected_action_digest="c" * 64,
        dirty_worktree=True,
        peer_sealed_digests=["other"],
    )
    assert bad.passed is False
    assert bad.missing_keys
    assert bad.digest_mismatches
    assert bad.dirty_worktree_blocked is True


def test_synthesize_match_and_mismatch() -> None:
    primary = {
        "all_passed": True,
        "platform": {
            "host_id": "a",
            "sealed_corrected_action_digest": "digest-a",
            "bundle_sha256": "bundle-a",
            "artifact_hashes": {},
        },
    }
    match = synthesize_second_host_report(primary, digest_mode="match")
    assert match["platform"]["sealed_corrected_action_digest"] == "digest-a"
    assert match["platform"]["extras"]["synthetic_fixture"] is True
    mism = synthesize_second_host_report(primary, digest_mode="mismatch")
    assert mism["platform"]["sealed_corrected_action_digest"] != "digest-a"


def test_multi_host_soak_simulation_match(tmp_path: Path) -> None:
    sim = run_multi_host_soak_simulation(
        output_dir=tmp_path,
        digest_mode="match",
        host_id="test-sim-a",
        exact_command="pytest:multi_host_match",
    )
    d = sim.as_dict()
    assert d["schema_id"] == MULTI_HOST_SIM_SCHEMA_ID
    assert d["is_synthetic"] is True
    assert d["promotion_claim"] is False
    assert d["aggregate"]["n_distinct_hosts"] == 2
    assert d["aggregate"].get("n_real_hosts") == 1
    assert any("real hosts" in b.lower() or "synthetic" in b.lower() for b in d["r4_blockers_remaining"])
    assert (tmp_path / "multi_host_soak_simulation.json").is_file()


def test_multi_host_soak_simulation_mismatch(tmp_path: Path) -> None:
    sim = run_multi_host_soak_simulation(
        output_dir=tmp_path,
        digest_mode="mismatch",
        host_id="test-sim-b",
        exact_command="pytest:multi_host_mismatch",
    )
    assert sim.aggregate.get("digest_mismatches")

"""R12: multi-host soak simulation + governed hash research adapter."""

from __future__ import annotations

from pathlib import Path

from conicshield.experimental.assurance.governed_hash_policy import (
    GOVERNED_HASH_POLICY_SCHEMA_ID,
    GovernedHashPolicy,
    check_governed_hashes,
    default_governed_hash_policy,
    recompute_artifact_hashes,
    sha256_bytes,
    verify_artifact_hashes_on_disk,
)
from conicshield.experimental.assurance.multi_host_soak_sim import (
    MULTI_HOST_SIM_SCHEMA_ID,
    run_multi_host_soak_simulation,
    synthesize_second_host_report,
)


def test_governed_hash_policy_research_only(tmp_path: Path) -> None:
    pol = default_governed_hash_policy()
    assert pol.schema_id == GOVERNED_HASH_POLICY_SCHEMA_ID
    assert pol.production_release_integrated is False
    bundle = tmp_path / "assurance_bundle.json"
    prov = tmp_path / "provenance.json"
    bundle.write_text("{}", encoding="utf-8")
    prov.write_text("{}", encoding="utf-8")
    ah = {
        "assurance_bundle.json": sha256_bytes(b"{}"),
        "provenance.json": sha256_bytes(b"{}"),
    }
    ok = check_governed_hashes(
        artifact_hashes=ah,
        sealed_corrected_action_digest="c" * 64,
        dirty_worktree=False,
        peer_sealed_digests=["c" * 64],
        artifact_paths={
            "assurance_bundle.json": bundle,
            "provenance.json": prov,
        },
        attested=True,
        attestation={"attested": True},
    )
    assert ok.passed is True
    assert ok.attestation_ok is True
    assert ok.on_disk_mismatches == []
    assert any("production" in b.lower() for b in ok.blockers)
    assert ok.as_dict()["production_claim"] is False


def test_governed_hash_rejects_nonempty_strings_without_on_disk() -> None:
    """Nonempty digests alone must not pass when on-disk recompute is required."""

    bad = check_governed_hashes(
        artifact_hashes={
            "assurance_bundle.json": "a" * 64,
            "provenance.json": "b" * 64,
        },
        sealed_corrected_action_digest="c" * 64,
        dirty_worktree=False,
        peer_sealed_digests=["c" * 64],
        attested=True,
    )
    assert bad.passed is False
    assert bad.on_disk_mismatches
    assert any("on-disk" in b.lower() for b in bad.blockers)


def test_governed_hash_verifies_actual_artifact_hashes(tmp_path: Path) -> None:
    bundle = tmp_path / "assurance_bundle.json"
    prov = tmp_path / "provenance.json"
    bundle.write_text('{"ok": true}', encoding="utf-8")
    prov.write_text('{"prov": true}', encoding="utf-8")
    recorded = recompute_artifact_hashes(
        {"assurance_bundle.json": bundle, "provenance.json": prov}
    )
    # Corrupt recorded hash → must fail
    corrupt = dict(recorded)
    corrupt["assurance_bundle.json"] = "0" * 64
    mismatches = verify_artifact_hashes_on_disk(
        recorded_hashes=corrupt,
        artifact_paths={"assurance_bundle.json": bundle, "provenance.json": prov},
    )
    assert mismatches
    ok = check_governed_hashes(
        artifact_hashes=recorded,
        sealed_corrected_action_digest="d" * 64,
        dirty_worktree=False,
        artifact_paths={"assurance_bundle.json": bundle, "provenance.json": prov},
        attested=True,
    )
    assert ok.passed is True
    fail = check_governed_hashes(
        artifact_hashes=corrupt,
        sealed_corrected_action_digest="d" * 64,
        dirty_worktree=False,
        artifact_paths={"assurance_bundle.json": bundle, "provenance.json": prov},
        attested=True,
    )
    assert fail.passed is False
    assert fail.on_disk_mismatches


def test_governed_hash_requires_attestation(tmp_path: Path) -> None:
    bundle = tmp_path / "assurance_bundle.json"
    prov = tmp_path / "provenance.json"
    bundle.write_text("x", encoding="utf-8")
    prov.write_text("y", encoding="utf-8")
    ah = recompute_artifact_hashes(
        {"assurance_bundle.json": bundle, "provenance.json": prov}
    )
    no_att = check_governed_hashes(
        artifact_hashes=ah,
        sealed_corrected_action_digest="e" * 64,
        dirty_worktree=False,
        artifact_paths={"assurance_bundle.json": bundle, "provenance.json": prov},
        attested=False,
    )
    assert no_att.passed is False
    assert no_att.attestation_ok is False


def test_governed_hash_flags_mismatch_and_dirty() -> None:
    pol = GovernedHashPolicy(require_on_disk_recompute=False, require_attestation=False)
    bad = check_governed_hashes(
        artifact_hashes={"assurance_bundle.json": "a" * 64},
        sealed_corrected_action_digest="c" * 64,
        dirty_worktree=True,
        peer_sealed_digests=["other"],
        policy=pol,
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
    assert d["aggregate"].get("r4_multi_host_gate_ready") is False
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

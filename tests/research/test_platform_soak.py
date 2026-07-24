"""R4 / R12 platform soak + multi-host aggregation tests."""

from __future__ import annotations

from pathlib import Path

from conicshield.experimental.assurance.platform_soak import (
    AGGREGATE_SCHEMA_ID,
    PLATFORM_SOAK_SCHEMA_ID,
    aggregate_platform_soaks,
    annotate_deprecated_soak_artifact,
    run_platform_soak,
)


def _full_digest(tag: str) -> str:
    """Deterministic full SHA-256 hex for fixture digests."""

    import hashlib

    return hashlib.sha256(tag.encode("utf-8")).hexdigest()


def test_platform_soak_records_matrix(tmp_path: Path) -> None:
    report = run_platform_soak(
        output_dir=tmp_path,
        host_id="test-host|ci",
        exact_command="pytest:test_platform_soak_records_matrix",
        matrix_role="linux_public",
    )
    assert report.schema_id == PLATFORM_SOAK_SCHEMA_ID
    assert report.platform is not None
    assert report.platform.host_id == "test-host|ci"
    assert report.platform.operating_system
    assert report.platform.python_version
    assert report.platform.solver_versions
    assert report.platform.bundle_sha256
    assert report.platform.matrix_role == "linux_public"
    assert report.platform.problem_digest
    assert report.platform.forward_solution_digest
    assert report.platform.environment_signature
    assert report.platform.artifact_index
    assert report.platform.package_provenance
    assert report.platform.has_shadow is True
    assert report.platform.has_live_sensitivity is False
    assert report.r4_blockers
    assert report.sensitivity_fields_synthetic is False
    assert report.promotion_eligible is False
    assert report.as_dict()["promotion_claim"] is False
    assert (tmp_path / "platform_soak.json").is_file()
    text = (tmp_path / "assurance_bundle.json").read_text(encoding="utf-8")
    assert "sensitivity_evidence" not in text or '"sensitivity_evidence": null' in text


def test_aggregate_flags_single_host_blocker(tmp_path: Path) -> None:
    report = run_platform_soak(
        output_dir=tmp_path,
        host_id="solo",
        exact_command="pytest:aggregate",
        host_kind="real",
        matrix_role="linux_public",
    )
    agg = aggregate_platform_soaks([report])
    assert agg["schema_id"] == AGGREGATE_SCHEMA_ID
    assert agg["n_distinct_hosts"] == 1
    assert agg["n_real_hosts"] == 1
    assert agg["n_synthetic_hosts"] == 0
    assert agg["promotion_claim"] is False
    assert agg["promotion_eligible"] is False
    assert agg["r4_multi_host_gate_ready"] is False
    assert agg["invalidation_reason"]
    assert "insufficient_real_hosts" in agg["rejection_reasons"]
    assert any(">=2" in b or "multi" in b.lower() for b in agg["r4_blockers"])


def test_aggregate_digest_mismatch() -> None:
    pd = _full_digest("problem-same")
    a = {
        "all_passed": True,
        "sensitivity_fields_synthetic": False,
        "platform": {
            "host_id": "h1",
            "host_kind": "real",
            "matrix_role": "linux_public",
            "dirty_worktree": False,
            "repository_commit": "abc",
            "corpus_version": "c1",
            "problem_digest": pd,
            "forward_solution_digest": _full_digest("fwd-a"),
            "sealed_corrected_action_digest": _full_digest("aaa"),
            "bundle_sha256": "b1",
            "environment_signature": _full_digest("env-a"),
            "has_live_sensitivity": False,
            "moreau_native": False,
        },
    }
    b = {
        "all_passed": True,
        "sensitivity_fields_synthetic": False,
        "platform": {
            "host_id": "h2",
            "host_kind": "real",
            "matrix_role": "windows_public",
            "dirty_worktree": False,
            "repository_commit": "abc",
            "corpus_version": "c1",
            "problem_digest": pd,
            "forward_solution_digest": _full_digest("fwd-b"),
            "sealed_corrected_action_digest": _full_digest("bbb"),
            "bundle_sha256": "b2",
            "environment_signature": _full_digest("env-b"),
            "has_live_sensitivity": False,
            "moreau_native": False,
        },
    }
    agg = aggregate_platform_soaks([a, b])
    assert agg["n_distinct_hosts"] == 2
    assert agg["n_real_hosts"] == 2
    assert agg["digest_mismatches"]
    assert agg["sealed_digest_mismatches"]
    assert agg["promotion_claim"] is False
    assert agg["r4_multi_host_gate_ready"] is False
    assert "sealed_digest_mismatch" in agg["rejection_reasons"]


def test_aggregate_two_real_hosts_matching_r12_gate_ready() -> None:
    pd = _full_digest("problem")
    sealed = _full_digest("sealed")
    commit = "deadbeef" * 5
    a = {
        "all_passed": True,
        "sensitivity_fields_synthetic": False,
        "corpus_version": "c1",
        "platform": {
            "host_id": "win|windows|3.13",
            "host_kind": "real",
            "matrix_role": "windows_public",
            "dirty_worktree": False,
            "repository_commit": commit,
            "corpus_version": "c1",
            "problem_digest": pd,
            "forward_solution_digest": _full_digest("fwd"),
            "sealed_corrected_action_digest": sealed,
            "bundle_sha256": "bundle-win",
            "environment_signature": _full_digest("env-win"),
            "has_live_sensitivity": False,
            "moreau_native": False,
            "claimed_evidence_level": "L2_SHADOW_COMPARED",
        },
    }
    b = {
        "all_passed": True,
        "sensitivity_fields_synthetic": False,
        "corpus_version": "c1",
        "platform": {
            "host_id": "linux|linux|3.12",
            "host_kind": "real",
            "matrix_role": "linux_public",
            "dirty_worktree": False,
            "repository_commit": commit,
            "corpus_version": "c1",
            "problem_digest": pd,
            "forward_solution_digest": _full_digest("fwd"),
            "sealed_corrected_action_digest": sealed,
            "bundle_sha256": "bundle-linux",
            "environment_signature": _full_digest("env-linux"),
            "has_live_sensitivity": False,
            "moreau_native": False,
            "claimed_evidence_level": "L2_SHADOW_COMPARED",
        },
    }
    agg = aggregate_platform_soaks([a, b], require_public_matrix=True)
    assert agg["n_real_hosts"] == 2
    assert agg["n_synthetic_hosts"] == 0
    assert agg["sealed_digest_mismatches"] == []
    assert agg["problem_digest_mismatches"] == []
    assert agg["bundle_hash_notes"]
    assert agg["historical_structural_gate_ready"] is True
    assert agg["r4_multi_host_gate_ready"] is True
    assert agg["invalidation_reason"] is None
    assert agg["promotion_eligible"] is False
    assert agg["promotion_claim"] is False
    assert agg["digest_comparison_policy"] == "byte_identity"
    assert agg["numerical_comparison_policy"] == "tolerance"


def test_aggregate_incomplete_r12_fields_still_not_ready() -> None:
    """Pre-R12 style reports (sealed only) remain gate-not-ready."""

    a = {
        "all_passed": True,
        "platform": {
            "host_id": "win|windows|3.13",
            "host_kind": "real",
            "sealed_corrected_action_digest": "same",
            "bundle_sha256": "bundle-win",
        },
    }
    b = {
        "all_passed": True,
        "platform": {
            "host_id": "wsl|linux-wsl|3.12",
            "host_kind": "real",
            "sealed_corrected_action_digest": "same",
            "bundle_sha256": "bundle-wsl",
        },
    }
    agg = aggregate_platform_soaks([a, b])
    assert agg["n_real_hosts"] == 2
    assert agg["historical_structural_gate_ready"] is True
    assert agg["r4_multi_host_gate_ready"] is False
    assert agg["promotion_eligible"] is False
    assert agg["invalidation_reason"]
    assert agg["promotion_claim"] is False
    assert "problem_digest_mismatch_or_missing" in agg["rejection_reasons"]


def test_aggregate_rejects_synthetic_and_moreau_without_native() -> None:
    pd = _full_digest("p")
    sealed = _full_digest("s")
    a = {
        "all_passed": True,
        "sensitivity_fields_synthetic": False,
        "platform": {
            "host_id": "h1",
            "host_kind": "real",
            "matrix_role": "linux_public",
            "dirty_worktree": False,
            "repository_commit": "c1",
            "corpus_version": "v",
            "problem_digest": pd,
            "sealed_corrected_action_digest": sealed,
            "bundle_sha256": "b1",
            "environment_signature": _full_digest("e1"),
            "has_live_sensitivity": False,
            "moreau_native": False,
        },
    }
    b = {
        "all_passed": True,
        "sensitivity_fields_synthetic": False,
        "platform": {
            "host_id": "synthetic-b",
            "host_kind": "synthetic",
            "matrix_role": "unspecified",
            "dirty_worktree": False,
            "repository_commit": "c1",
            "corpus_version": "v",
            "problem_digest": pd,
            "sealed_corrected_action_digest": sealed,
            "bundle_sha256": "b1",
            "environment_signature": _full_digest("e2"),
            "has_live_sensitivity": False,
            "moreau_native": False,
            "extras": {"synthetic_fixture": True},
        },
    }
    agg = aggregate_platform_soaks([a, b])
    assert agg["n_real_hosts"] == 1
    assert agg["n_synthetic_hosts"] == 1
    assert agg["r4_multi_host_gate_ready"] is False
    assert "synthetic_hosts" in agg["rejection_reasons"]

    moreau_claim = {
        "all_passed": True,
        "sensitivity_fields_synthetic": False,
        "platform": {
            "host_id": "h2",
            "host_kind": "real",
            "matrix_role": "linux_wsl_moreau_cpu",
            "dirty_worktree": False,
            "repository_commit": "c1",
            "corpus_version": "v",
            "problem_digest": pd,
            "sealed_corrected_action_digest": sealed,
            "bundle_sha256": "b2",
            "environment_signature": _full_digest("e3"),
            "has_live_sensitivity": False,
            "moreau_native": False,
            "extras": {"moreau_research_claim": True},
        },
    }
    a2 = dict(a)
    a2["platform"] = dict(a["platform"])
    a2["platform"]["host_id"] = "pub"
    agg2 = aggregate_platform_soaks([a2, moreau_claim])
    assert agg2["r4_multi_host_gate_ready"] is False
    assert "moreau_claim_without_native_host" in agg2["rejection_reasons"]


def test_aggregate_rejects_l3_without_gradient_and_stale_commit() -> None:
    pd = _full_digest("p")
    sealed = _full_digest("s")
    a = {
        "all_passed": True,
        "sensitivity_fields_synthetic": False,
        "platform": {
            "host_id": "h1",
            "host_kind": "real",
            "matrix_role": "linux_public",
            "dirty_worktree": False,
            "repository_commit": "commit-a",
            "corpus_version": "v",
            "problem_digest": pd,
            "sealed_corrected_action_digest": sealed,
            "environment_signature": _full_digest("e1"),
            "claimed_evidence_level": "L3_SENSITIVITY_VALIDATED",
            "has_live_sensitivity": False,
            "moreau_native": False,
        },
    }
    b = {
        "all_passed": True,
        "sensitivity_fields_synthetic": False,
        "platform": {
            "host_id": "h2",
            "host_kind": "real",
            "matrix_role": "windows_public",
            "dirty_worktree": False,
            "repository_commit": "commit-b",
            "corpus_version": "v",
            "problem_digest": pd,
            "sealed_corrected_action_digest": sealed,
            "environment_signature": _full_digest("e2"),
            "claimed_evidence_level": "L2_SHADOW_COMPARED",
            "has_live_sensitivity": False,
            "moreau_native": False,
        },
    }
    agg = aggregate_platform_soaks([a, b])
    assert agg["r4_multi_host_gate_ready"] is False
    assert "missing_gradient_for_l3" in agg["rejection_reasons"]
    assert "stale_or_mismatched_commit" in agg["rejection_reasons"]


def test_aggregate_l4_needs_two_independent_envs() -> None:
    pd = _full_digest("p")
    sealed = _full_digest("s")
    same_env = _full_digest("same-env")
    a = {
        "all_passed": True,
        "sensitivity_fields_synthetic": False,
        "l4_candidate": True,
        "platform": {
            "host_id": "h1",
            "host_kind": "real",
            "matrix_role": "linux_public",
            "dirty_worktree": False,
            "repository_commit": "c",
            "corpus_version": "v",
            "problem_digest": pd,
            "sealed_corrected_action_digest": sealed,
            "environment_signature": same_env,
            "claimed_evidence_level": "L4_REPLAYED_AND_GOVERNED",
            "has_live_sensitivity": True,
            "moreau_native": False,
            "extras": {"l4_candidate": True},
        },
    }
    b = {
        "all_passed": True,
        "sensitivity_fields_synthetic": False,
        "l4_candidate": True,
        "platform": {
            "host_id": "h2",
            "host_kind": "real",
            "matrix_role": "windows_public",
            "dirty_worktree": False,
            "repository_commit": "c",
            "corpus_version": "v",
            "problem_digest": pd,
            "sealed_corrected_action_digest": sealed,
            "environment_signature": same_env,
            "claimed_evidence_level": "L4_REPLAYED_AND_GOVERNED",
            "has_live_sensitivity": True,
            "moreau_native": False,
            "extras": {"l4_candidate": True},
        },
    }
    agg = aggregate_platform_soaks([a, b])
    assert agg["n_independent_envs"] == 1
    assert agg["r4_multi_host_gate_ready"] is False
    assert "l4_insufficient_independent_envs" in agg["rejection_reasons"]


def test_aggregate_synthetic_does_not_count_as_real() -> None:
    a = {
        "all_passed": True,
        "platform": {
            "host_id": "h1",
            "host_kind": "real",
            "sealed_corrected_action_digest": "aaa",
            "bundle_sha256": "b1",
        },
    }
    b = {
        "all_passed": True,
        "platform": {
            "host_id": "synthetic-b",
            "host_kind": "synthetic",
            "sealed_corrected_action_digest": "aaa",
            "bundle_sha256": "b1",
            "extras": {"synthetic_fixture": True},
        },
    }
    agg = aggregate_platform_soaks([a, b])
    assert agg["n_real_hosts"] == 1
    assert agg["n_synthetic_hosts"] == 1
    assert agg["r4_multi_host_gate_ready"] is False
    assert any("synthetic" in b.lower() for b in agg["r4_blockers"])


def test_platform_soak_records_host_kind(tmp_path: Path) -> None:
    report = run_platform_soak(
        output_dir=tmp_path / "real",
        host_id="kind-check",
        exact_command="pytest:host_kind",
        host_kind="real",
        matrix_role="windows_public",
    )
    assert report.platform is not None
    assert report.platform.host_kind == "real"
    assert report.platform.matrix_role == "windows_public"
    assert report.platform.extras.get("counts_toward_r4_multi_host_gate") is True


def test_annotate_deprecated_aggregate_preserves_history() -> None:
    raw = {
        "schema_id": "research.platform_soak_aggregate.v0",
        "r4_multi_host_gate_ready": True,
        "n_real_hosts": 2,
        "reports": [],
        "promotion_claim": False,
    }
    annotated = annotate_deprecated_soak_artifact(raw)
    assert annotated["r4_multi_host_gate_ready"] is False
    assert annotated["historical_r4_multi_host_gate_ready"] is True
    assert annotated["promotion_eligible"] is False
    assert annotated["invalidation_reason"]

"""R4 platform soak + multi-host aggregation tests."""

from __future__ import annotations

from pathlib import Path

from conicshield.experimental.assurance.platform_soak import (
    AGGREGATE_SCHEMA_ID,
    PLATFORM_SOAK_SCHEMA_ID,
    aggregate_platform_soaks,
    run_platform_soak,
)


def test_platform_soak_records_matrix(tmp_path: Path) -> None:
    report = run_platform_soak(
        output_dir=tmp_path,
        host_id="test-host|ci",
        exact_command="pytest:test_platform_soak_records_matrix",
    )
    assert report.schema_id == PLATFORM_SOAK_SCHEMA_ID
    assert report.platform is not None
    assert report.platform.host_id == "test-host|ci"
    assert report.platform.operating_system
    assert report.platform.python_version
    assert report.platform.solver_versions
    assert report.platform.bundle_sha256
    assert report.r4_blockers
    assert report.as_dict()["promotion_claim"] is False
    assert (tmp_path / "platform_soak.json").is_file()


def test_aggregate_flags_single_host_blocker(tmp_path: Path) -> None:
    report = run_platform_soak(
        output_dir=tmp_path,
        host_id="solo",
        exact_command="pytest:aggregate",
        host_kind="real",
    )
    agg = aggregate_platform_soaks([report])
    assert agg["schema_id"] == AGGREGATE_SCHEMA_ID
    assert agg["n_distinct_hosts"] == 1
    assert agg["n_real_hosts"] == 1
    assert agg["n_synthetic_hosts"] == 0
    assert agg["promotion_claim"] is False
    assert agg["r4_multi_host_gate_ready"] is False
    assert any(">=2" in b or "multi" in b.lower() for b in agg["r4_blockers"])


def test_aggregate_digest_mismatch() -> None:
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
            "host_id": "h2",
            "host_kind": "real",
            "sealed_corrected_action_digest": "bbb",
            "bundle_sha256": "b2",
        },
    }
    agg = aggregate_platform_soaks([a, b])
    assert agg["n_distinct_hosts"] == 2
    assert agg["n_real_hosts"] == 2
    assert agg["digest_mismatches"]
    assert agg["sealed_digest_mismatches"]
    assert agg["promotion_claim"] is False
    assert agg["r4_multi_host_gate_ready"] is False


def test_aggregate_two_real_hosts_matching_sealed_ready() -> None:
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
    assert agg["n_synthetic_hosts"] == 0
    assert agg["sealed_digest_mismatches"] == []
    assert agg["bundle_hash_notes"]  # informational only
    assert agg["r4_multi_host_gate_ready"] is True
    assert agg["promotion_claim"] is False


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
    )
    assert report.platform is not None
    assert report.platform.host_kind == "real"
    assert report.platform.extras.get("counts_toward_r4_multi_host_gate") is True

"""Sidecar protocol versioning, negotiation, binding, and framing tests."""

from __future__ import annotations

import pytest

from conicshield.platform.sidecar_protocol import (
    PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    FallbackPolicy,
    SidecarProtocolError,
    SolveRequest,
    SolveResultMessage,
    compute_request_binding_digest,
    decode_message,
    encode_message,
    hello_ack_message,
    hello_message,
    negotiate_protocol_version,
    protocol_v2_features_complete,
    validate_request_binding,
)


def test_protocol_version_constant() -> None:
    assert PROTOCOL_VERSION == 2
    assert 2 in SUPPORTED_PROTOCOL_VERSIONS
    assert protocol_v2_features_complete() is True


def test_encode_decode_roundtrip() -> None:
    msg = hello_message(client_id="c1", fallback_policy=FallbackPolicy.PUBLIC_CLARABEL)
    raw = encode_message(msg)
    assert raw.endswith(b"\n")
    parsed = decode_message(raw)
    assert parsed["protocol_version"] == PROTOCOL_VERSION
    assert parsed["type"] == "hello"
    assert parsed["supported_protocol_versions"] == list(SUPPORTED_PROTOCOL_VERSIONS)


def test_version_mismatch_rejected() -> None:
    with pytest.raises(SidecarProtocolError, match="unsupported protocol_version"):
        decode_message('{"type":"ping","protocol_version":999}\n')


def test_negotiate_protocol_version_picks_highest_common() -> None:
    assert negotiate_protocol_version([1, 2], [2, 3]) == 2
    with pytest.raises(SidecarProtocolError, match="negotiation failed"):
        negotiate_protocol_version([1], [2])


def test_hello_ack_includes_negotiation_and_provenance() -> None:
    ack = hello_ack_message(
        worker_id="w1",
        moreau_available=False,
        client_supported_versions=[2],
    )
    assert ack["negotiated_protocol_version"] == 2
    assert ack["supported_protocol_versions"] == list(SUPPORTED_PROTOCOL_VERSIONS)
    assert "worker_provenance" in ack
    assert ack["worker_provenance"]["protocol_version"] == PROTOCOL_VERSION
    assert ack["capabilities"]["request_binding"] is True


def test_request_binding_digest_stable_and_validated() -> None:
    digest = compute_request_binding_digest(
        structural_fingerprint="abc",
        numerical_parameters={"digest": "def"},
        proposed_action=[0.5, 0.5],
        previous_action=[0.25, 0.75],
        reference_action=None,
        policy_weight=1.0,
        reference_weight=0.0,
        row_ids=("r0",),
        backend="native_moreau",
        trace_id="t1",
    )
    assert len(digest) == 64
    again = validate_request_binding(
        declared_digest=digest,
        structural_fingerprint="abc",
        numerical_parameters={"digest": "def"},
        proposed_action=[0.5, 0.5],
        previous_action=[0.25, 0.75],
        reference_action=None,
        policy_weight=1.0,
        reference_weight=0.0,
        row_ids=("r0",),
        backend="native_moreau",
        trace_id="t1",
    )
    assert again == digest
    with pytest.raises(SidecarProtocolError, match="mismatch"):
        validate_request_binding(
            declared_digest="0" * 64,
            structural_fingerprint="abc",
            numerical_parameters={"digest": "def"},
            proposed_action=[0.5, 0.5],
            previous_action=[0.25, 0.75],
            reference_action=None,
            policy_weight=1.0,
            reference_weight=0.0,
            row_ids=("r0",),
            backend="native_moreau",
            trace_id="t1",
        )
    with pytest.raises(SidecarProtocolError, match="missing request_binding_digest"):
        validate_request_binding(
            declared_digest=None,
            structural_fingerprint="abc",
            numerical_parameters={},
            proposed_action=[0.5],
            previous_action=None,
            reference_action=None,
            policy_weight=1.0,
            reference_weight=0.0,
        )


def test_solve_request_message_fields_and_binding() -> None:
    req = SolveRequest(
        trace_id="t1",
        spec={"spec_id": "x", "version": "0.1.0", "action_dim": 2, "constraints": []},
        proposed_action=[0.5, 0.5],
        structural_fingerprint="abc",
        numerical_parameters={"digest": "def"},
        row_ids=("r0",),
        deadline_ms=1000,
    ).with_binding()
    payload = req.to_message()
    assert payload["request_binding_digest"] == req.request_binding_digest
    again = SolveRequest.from_message(payload)
    assert again.trace_id == "t1"
    assert again.row_ids == ("r0",)
    assert again.deadline_ms == 1000
    assert again.request_binding_digest == req.request_binding_digest

    tampered = dict(payload)
    tampered["proposed_action"] = [0.9, 0.1]
    with pytest.raises(SidecarProtocolError, match="request_binding_digest mismatch"):
        SolveRequest.from_message(tampered)


def test_solve_result_requires_verification_flag_for_ok_path() -> None:
    msg = SolveResultMessage(
        trace_id="t1",
        ok=True,
        result={"corrected_action": [0.5, 0.5]},
        verification_complete=True,
        request_binding_digest="a" * 64,
        solver_provenance={"backend": "native_moreau"},
    )
    parsed = SolveResultMessage.from_message(msg.to_message())
    assert parsed.verification_complete is True
    assert parsed.request_binding_digest == "a" * 64
    assert parsed.solver_provenance is not None

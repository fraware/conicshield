"""Sidecar protocol versioning and framing tests."""

from __future__ import annotations

import pytest

from conicshield.platform.sidecar_protocol import (
    PROTOCOL_VERSION,
    FallbackPolicy,
    SidecarProtocolError,
    SolveRequest,
    SolveResultMessage,
    decode_message,
    encode_message,
    hello_message,
)


def test_protocol_version_constant() -> None:
    assert PROTOCOL_VERSION == 1


def test_encode_decode_roundtrip() -> None:
    msg = hello_message(client_id="c1", fallback_policy=FallbackPolicy.PUBLIC_CLARABEL)
    raw = encode_message(msg)
    assert raw.endswith(b"\n")
    parsed = decode_message(raw)
    assert parsed["protocol_version"] == PROTOCOL_VERSION
    assert parsed["type"] == "hello"


def test_version_mismatch_rejected() -> None:
    with pytest.raises(SidecarProtocolError, match="unsupported protocol_version"):
        decode_message('{"type":"ping","protocol_version":999}\n')


def test_solve_request_message_fields() -> None:
    req = SolveRequest(
        trace_id="t1",
        spec={"spec_id": "x", "version": "0.1.0", "action_dim": 2, "constraints": []},
        proposed_action=[0.5, 0.5],
        structural_fingerprint="abc",
        numerical_parameters={"digest": "def"},
        row_ids=("r0",),
        deadline_ms=1000,
    )
    payload = req.to_message()
    again = SolveRequest.from_message(payload)
    assert again.trace_id == "t1"
    assert again.row_ids == ("r0",)
    assert again.deadline_ms == 1000


def test_solve_result_requires_verification_flag_for_ok_path() -> None:
    msg = SolveResultMessage(
        trace_id="t1",
        ok=True,
        result={"corrected_action": [0.5, 0.5]},
        verification_complete=True,
    )
    parsed = SolveResultMessage.from_message(msg.to_message())
    assert parsed.verification_complete is True

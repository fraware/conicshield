"""Sidecar client fallback / no-unverified-release tests (no Moreau required)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from conicshield.platform.sidecar_protocol import (
    PROTOCOL_VERSION,
    FallbackPolicy,
    MessageType,
    encode_message,
)
from conicshield.platform.windows_sidecar_client import (
    SidecarClientConfig,
    SidecarWorkerError,
    WindowsSidecarClient,
    _projection_from_payload,
)
from conicshield.specs.schema import BoxConstraint, SafetySpec, SimplexConstraint
from conicshield.verification.feasibility import VerificationReleaseError


def _spec() -> SafetySpec:
    return SafetySpec(
        spec_id="sidecar/fallback",
        version="0.1.0",
        action_dim=2,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=[0.0, 0.0], upper=[1.0, 1.0]),
        ],
    )


class _FakeProc:
    """Minimal Popen-like object for injecting worker death / bad payloads."""

    def __init__(self, script: list[bytes]) -> None:
        self._script = list(script)
        self.stdin = _Pipe()
        self.stdout = _Out(self._script)
        self.stderr = _Pipe()
        self._rc: int | None = None

    def poll(self) -> int | None:
        return self._rc

    def wait(self, timeout: float | None = None) -> int:  # noqa: ARG002
        self._rc = 0
        return 0

    def kill(self) -> None:
        self._rc = -9


class _Pipe:
    def write(self, data: bytes) -> int:
        return len(data)

    def flush(self) -> None:
        return None


class _Out:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    def readline(self) -> bytes:
        if not self._lines:
            return b""
        item = self._lines.pop(0)
        if item == b"__DIE__":
            return b""
        return item


def test_refuse_materialize_without_verification() -> None:
    with pytest.raises(SidecarWorkerError, match="verification"):
        _projection_from_payload(
            {
                "proposed_action": [0.5, 0.5],
                "corrected_action": [0.5, 0.5],
                "intervened": False,
                "intervention_norm": 0.0,
                "solver_status": "optimal",
            }
        )


def test_worker_death_applies_public_fallback() -> None:
    hello_ack = encode_message(
        {
            "type": MessageType.HELLO_ACK.value,
            "protocol_version": PROTOCOL_VERSION,
            "worker_id": "fake",
            "moreau_available": True,
            "capabilities": {},
        }
    )

    def _spawn() -> _FakeProc:
        return _FakeProc([hello_ack, b"__DIE__"])

    client = WindowsSidecarClient(
        config=SidecarClientConfig(
            fallback_policy=FallbackPolicy.PUBLIC_CLARABEL,
            max_restarts=0,
            hello_timeout_sec=2.0,
            solve_timeout_sec=2.0,
            spawn_factory=_spawn,
        )
    )
    client.start()
    result = client.project(_spec(), np.array([0.6, 0.4], dtype=np.float64))
    assert result.verification is not None and result.verification.passed
    assert any("sidecar" in (h.kind or "") for h in result.fallback_history) or result.metadata.get("sidecar_fallback")
    report = client.overhead_report()
    assert report["fallback_count"] >= 1
    client.close()


def test_fail_closed_policy_raises() -> None:
    hello_ack = encode_message(
        {
            "type": MessageType.HELLO_ACK.value,
            "protocol_version": PROTOCOL_VERSION,
            "worker_id": "fake",
            "moreau_available": True,
            "capabilities": {},
        }
    )
    client = WindowsSidecarClient(
        config=SidecarClientConfig(
            fallback_policy=FallbackPolicy.FAIL_CLOSED,
            max_restarts=0,
            spawn_factory=lambda: _FakeProc([hello_ack, b"__DIE__"]),
        )
    )
    client.start()
    with pytest.raises(VerificationReleaseError, match="fail_closed"):
        client.project(_spec(), np.array([0.5, 0.5], dtype=np.float64))
    client.close()


def test_unverified_worker_payload_does_not_release() -> None:
    """Worker returns ok=false / verification_complete=false → public fallback only."""
    hello_ack = encode_message(
        {
            "type": MessageType.HELLO_ACK.value,
            "protocol_version": PROTOCOL_VERSION,
            "worker_id": "fake",
            "moreau_available": True,
            "capabilities": {},
        }
    )
    bad_result = encode_message(
        {
            "type": MessageType.SOLVE_RESULT.value,
            "protocol_version": PROTOCOL_VERSION,
            "trace_id": "will-be-ignored-mismatch-ok",
            "ok": False,
            "verification_complete": False,
            "error": "simulated",
            "error_code": "unverified",
            "result": {
                "proposed_action": [0.9, 0.1],
                "corrected_action": [0.9, 0.1],
                "intervened": False,
                "intervention_norm": 0.0,
                "solver_status": "optimal",
                # Deliberately omit verification — must not be released as-is.
            },
        }
    )
    client = WindowsSidecarClient(
        config=SidecarClientConfig(
            fallback_policy=FallbackPolicy.PUBLIC_CLARABEL,
            max_restarts=0,
            spawn_factory=lambda: _FakeProc([hello_ack, bad_result]),
        )
    )
    client.start()
    result = client.project(_spec(), np.array([0.9, 0.1], dtype=np.float64), trace_id="t-unverified")
    assert result.verification is not None and result.verification.passed
    # Must have come from public fallback, not the unverified stub.
    assert result.metadata.get("sidecar_fallback") is True
    client.close()


def test_local_worker_process_reuse_without_moreau() -> None:
    """Spin the real worker module as a local subprocess (Moreau may be absent).

    Qualifies: one process, multiple hello/ping round-trips, clean shutdown.
    Skips only if the worker module cannot start at all.
    """
    root = Path(__file__).resolve().parents[3]
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "conicshield.workers.moreau_worker"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(root),
        env=env,
        bufsize=0,
    )
    assert proc.stdin is not None and proc.stdout is not None
    try:
        proc.stdin.write(
            encode_message(
                {
                    "type": MessageType.HELLO.value,
                    "protocol_version": PROTOCOL_VERSION,
                    "client_id": "reuse-test",
                    "fallback_policy": FallbackPolicy.PUBLIC_CLARABEL.value,
                }
            )
        )
        proc.stdin.flush()
        line = proc.stdout.readline()
        assert line, proc.stderr.read() if proc.stderr else b""
        ack = json.loads(line.decode("utf-8"))
        assert ack["type"] == "hello_ack"
        assert ack["protocol_version"] == PROTOCOL_VERSION

        for _ in range(3):
            proc.stdin.write(encode_message({"type": MessageType.PING.value, "protocol_version": PROTOCOL_VERSION}))
            proc.stdin.flush()
            pong = json.loads(proc.stdout.readline().decode("utf-8"))
            assert pong["type"] == "pong"

        proc.stdin.write(encode_message({"type": MessageType.SHUTDOWN.value, "protocol_version": PROTOCOL_VERSION}))
        proc.stdin.flush()
        proc.wait(timeout=5)
        assert proc.returncode == 0
    finally:
        if proc.poll() is None:
            proc.kill()

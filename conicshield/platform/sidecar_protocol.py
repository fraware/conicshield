"""Versioned Moreau sidecar protocol (stdin/stdout JSON Lines).

Wire transport for v1 is a **persistent subprocess** pipe — not localhost TCP.
Native Windows hosts the client; the worker process runs under WSL2 (or Linux).

Protocol versioning
-------------------
* ``PROTOCOL_VERSION`` is the only wire version shipped in this tree.
* Clients and workers must reject mismatched versions (fail closed).
* Bumping the version requires a coordinated client+worker change.

This module defines message shapes only; it does not start processes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# Wire protocol version. Bump only with coordinated client/worker changes.
PROTOCOL_VERSION: int = 1

# Framing: one JSON object per line, UTF-8, terminated by ``\\n``.
CONTENT_TYPE = "application/x-ndjson; charset=utf-8"


class MessageType(StrEnum):
    HELLO = "hello"
    HELLO_ACK = "hello_ack"
    SOLVE = "solve"
    SOLVE_RESULT = "solve_result"
    CANCEL = "cancel"
    CANCEL_ACK = "cancel_ack"
    PING = "ping"
    PONG = "pong"
    SHUTDOWN = "shutdown"
    ERROR = "error"


class SidecarProtocolError(ValueError):
    """Malformed, version-mismatched, or otherwise illegal protocol payload."""


class FallbackPolicy(StrEnum):
    """Declared recovery when the sidecar worker dies or cannot complete a solve.

    Public fallback still runs the S2 verification gate before any release.
    """

    PUBLIC_CLARABEL = "public_clarabel"
    PUBLIC_SCS = "public_scs"
    FAIL_CLOSED = "fail_closed"


def _require_version(payload: dict[str, Any]) -> int:
    raw = payload.get("protocol_version")
    if raw is None:
        raise SidecarProtocolError("missing protocol_version")
    try:
        version = int(raw)
    except (TypeError, ValueError) as exc:
        raise SidecarProtocolError(f"invalid protocol_version: {raw!r}") from exc
    if version != PROTOCOL_VERSION:
        raise SidecarProtocolError(f"unsupported protocol_version={version}; this build speaks {PROTOCOL_VERSION}")
    return version


def encode_message(payload: dict[str, Any]) -> bytes:
    """Serialize a message dict to a single NDJSON line (includes trailing newline)."""
    if "protocol_version" not in payload:
        payload = {**payload, "protocol_version": PROTOCOL_VERSION}
    else:
        _require_version(payload)
    line = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, default=str)
    return (line + "\n").encode("utf-8")


def decode_message(raw: bytes | str) -> dict[str, Any]:
    """Parse one NDJSON line into a dict; enforce protocol version."""
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    text = text.strip()
    if not text:
        raise SidecarProtocolError("empty message")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SidecarProtocolError(f"invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SidecarProtocolError("message must be a JSON object")
    _require_version(payload)
    msg_type = payload.get("type")
    if not msg_type:
        raise SidecarProtocolError("missing message type")
    return payload


@dataclass(frozen=True, slots=True)
class SolveRequest:
    """Client → worker solve envelope.

    ``structural_fingerprint`` and ``numerical_parameters`` travel as opaque
    digests/maps so the worker can validate cache identity without re-deriving
    topology from free-form metadata alone.
    """

    trace_id: str
    spec: dict[str, Any]
    proposed_action: list[float]
    structural_fingerprint: str
    numerical_parameters: dict[str, Any] = field(default_factory=dict)
    previous_action: list[float] | None = None
    reference_action: list[float] | None = None
    policy_weight: float = 1.0
    reference_weight: float = 0.0
    row_ids: tuple[str, ...] = ()
    deadline_ms: int | None = None
    backend: str = "native_moreau"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_message(self) -> dict[str, Any]:
        return {
            "type": MessageType.SOLVE.value,
            "protocol_version": PROTOCOL_VERSION,
            "trace_id": self.trace_id,
            "spec": self.spec,
            "proposed_action": list(self.proposed_action),
            "structural_fingerprint": self.structural_fingerprint,
            "numerical_parameters": dict(self.numerical_parameters),
            "previous_action": None if self.previous_action is None else list(self.previous_action),
            "reference_action": None if self.reference_action is None else list(self.reference_action),
            "policy_weight": float(self.policy_weight),
            "reference_weight": float(self.reference_weight),
            "row_ids": list(self.row_ids),
            "deadline_ms": self.deadline_ms,
            "backend": self.backend,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_message(cls, payload: dict[str, Any]) -> SolveRequest:
        if payload.get("type") != MessageType.SOLVE.value:
            raise SidecarProtocolError(f"expected type=solve, got {payload.get('type')!r}")
        _require_version(payload)
        row_ids_raw = payload.get("row_ids") or []
        if not isinstance(row_ids_raw, list):
            raise SidecarProtocolError("row_ids must be a list")
        return cls(
            trace_id=str(payload["trace_id"]),
            spec=dict(payload["spec"]),
            proposed_action=[float(x) for x in payload["proposed_action"]],
            structural_fingerprint=str(payload["structural_fingerprint"]),
            numerical_parameters=dict(payload.get("numerical_parameters") or {}),
            previous_action=(
                None if payload.get("previous_action") is None else [float(x) for x in payload["previous_action"]]
            ),
            reference_action=(
                None if payload.get("reference_action") is None else [float(x) for x in payload["reference_action"]]
            ),
            policy_weight=float(payload.get("policy_weight", 1.0)),
            reference_weight=float(payload.get("reference_weight", 0.0)),
            row_ids=tuple(str(x) for x in row_ids_raw),
            deadline_ms=(None if payload.get("deadline_ms") is None else int(payload["deadline_ms"])),
            backend=str(payload.get("backend") or "native_moreau"),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class SolveResultMessage:
    """Worker → client solve outcome.

    When ``ok`` is false, ``result`` must be omitted/null and ``error`` set.
    Clients must never treat a non-ok or incomplete message as a releasable action.
    """

    trace_id: str
    ok: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    error_code: str | None = None
    overhead_ms: float | None = None
    worker_solve_ms: float | None = None
    verification_complete: bool = False
    row_ids: tuple[str, ...] = ()

    def to_message(self) -> dict[str, Any]:
        return {
            "type": MessageType.SOLVE_RESULT.value,
            "protocol_version": PROTOCOL_VERSION,
            "trace_id": self.trace_id,
            "ok": bool(self.ok),
            "result": self.result,
            "error": self.error,
            "error_code": self.error_code,
            "overhead_ms": self.overhead_ms,
            "worker_solve_ms": self.worker_solve_ms,
            "verification_complete": bool(self.verification_complete),
            "row_ids": list(self.row_ids),
        }

    @classmethod
    def from_message(cls, payload: dict[str, Any]) -> SolveResultMessage:
        if payload.get("type") != MessageType.SOLVE_RESULT.value:
            raise SidecarProtocolError(f"expected type=solve_result, got {payload.get('type')!r}")
        _require_version(payload)
        row_ids_raw = payload.get("row_ids") or []
        return cls(
            trace_id=str(payload["trace_id"]),
            ok=bool(payload.get("ok")),
            result=None if payload.get("result") is None else dict(payload["result"]),
            error=None if payload.get("error") is None else str(payload["error"]),
            error_code=None if payload.get("error_code") is None else str(payload["error_code"]),
            overhead_ms=(None if payload.get("overhead_ms") is None else float(payload["overhead_ms"])),
            worker_solve_ms=(None if payload.get("worker_solve_ms") is None else float(payload["worker_solve_ms"])),
            verification_complete=bool(payload.get("verification_complete", False)),
            row_ids=tuple(str(x) for x in row_ids_raw),
        )


def hello_message(*, client_id: str, fallback_policy: FallbackPolicy) -> dict[str, Any]:
    return {
        "type": MessageType.HELLO.value,
        "protocol_version": PROTOCOL_VERSION,
        "client_id": client_id,
        "fallback_policy": str(fallback_policy),
    }


def hello_ack_message(
    *,
    worker_id: str,
    moreau_available: bool,
    capabilities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": MessageType.HELLO_ACK.value,
        "protocol_version": PROTOCOL_VERSION,
        "worker_id": worker_id,
        "moreau_available": bool(moreau_available),
        "capabilities": dict(capabilities or {}),
    }


def error_message(
    *,
    code: str,
    message: str,
    trace_id: str | None = None,
) -> dict[str, Any]:
    return {
        "type": MessageType.ERROR.value,
        "protocol_version": PROTOCOL_VERSION,
        "error_code": code,
        "error": message,
        "trace_id": trace_id,
    }

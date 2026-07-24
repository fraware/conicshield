"""Persistent Moreau worker process (Linux / WSL2).

Speak the versioned NDJSON protocol on stdin/stdout. Performs vendor Moreau
solves with the S2 verification release pipeline. Never emits a releasable
action without ``verification_complete=true``.

Run under WSL2, not native Windows Python::

    python -m conicshield.workers.moreau_worker
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
import uuid
from collections.abc import Mapping
from typing import Any, TextIO

import numpy as np

from conicshield.backends.base import Backend, parse_backend
from conicshield.compilation.structural_fingerprint import (
    numerical_signature,
    structural_fingerprint,
)
from conicshield.core.solver_factory import create_projector
from conicshield.platform.sidecar_protocol import (
    PROTOCOL_VERSION,
    MessageType,
    SidecarProtocolError,
    SolveRequest,
    SolveResultMessage,
    decode_message,
    encode_message,
    error_message,
    hello_ack_message,
    worker_provenance_snapshot,
)
from conicshield.specs.schema import SafetySpec


def _moreau_available() -> bool:
    try:
        import moreau  # noqa: F401
    except Exception:
        return False
    return True


def _read_line(stdin: TextIO) -> str | None:
    line = stdin.readline()
    if line == "":
        return None
    return line


def _write_message(stdout: TextIO, payload: dict[str, Any]) -> None:
    raw = encode_message(payload)
    stdout.buffer.write(raw)
    stdout.buffer.flush()


def _spec_from_payload(raw: Mapping[str, Any]) -> SafetySpec:
    return SafetySpec.model_validate(dict(raw))


def _handle_solve(request: SolveRequest) -> SolveResultMessage:
    t0 = time.perf_counter()
    binding = request.request_binding_digest or request.binding_digest()
    if not _moreau_available():
        return SolveResultMessage(
            trace_id=request.trace_id,
            ok=False,
            error="moreau_unavailable_in_worker",
            error_code="moreau_unavailable",
            verification_complete=False,
            row_ids=request.row_ids,
            request_binding_digest=binding,
            overhead_ms=(time.perf_counter() - t0) * 1000.0,
        )

    try:
        backend = parse_backend(request.backend)
    except ValueError as exc:
        return SolveResultMessage(
            trace_id=request.trace_id,
            ok=False,
            error=str(exc),
            error_code="invalid_backend",
            verification_complete=False,
            row_ids=request.row_ids,
            request_binding_digest=binding,
            overhead_ms=(time.perf_counter() - t0) * 1000.0,
        )

    if backend not in {
        Backend.NATIVE_MOREAU,
        Backend.CVXPY_MOREAU,
        Backend.NATIVE_MOREAU_BATCH,
    }:
        return SolveResultMessage(
            trace_id=request.trace_id,
            ok=False,
            error=f"worker refuses non-vendor backend {backend!s}",
            error_code="backend_not_vendor",
            verification_complete=False,
            row_ids=request.row_ids,
            request_binding_digest=binding,
            overhead_ms=(time.perf_counter() - t0) * 1000.0,
        )

    # Batch backend is not exposed over single-row sidecar transport.
    if backend is Backend.NATIVE_MOREAU_BATCH:
        backend = Backend.NATIVE_MOREAU

    try:
        spec = _spec_from_payload(request.spec)
        expected_fp = structural_fingerprint(spec, backend=str(backend))
        if request.structural_fingerprint and request.structural_fingerprint != expected_fp.digest:
            return SolveResultMessage(
                trace_id=request.trace_id,
                ok=False,
                error=(
                    "structural_fingerprint mismatch: "
                    f"client={request.structural_fingerprint} worker={expected_fp.digest}"
                ),
                error_code="fingerprint_mismatch",
                verification_complete=False,
                row_ids=request.row_ids,
                request_binding_digest=binding,
                overhead_ms=(time.perf_counter() - t0) * 1000.0,
            )

        # v2: numerical signature mismatch is fail-closed (was advisory in v1).
        num_sig = numerical_signature(spec)
        meta = dict(request.metadata)
        client_num = request.numerical_parameters.get("digest")
        if client_num and client_num != num_sig.digest:
            return SolveResultMessage(
                trace_id=request.trace_id,
                ok=False,
                error=(
                    "numerical_parameters digest mismatch: "
                    f"client={client_num} worker={num_sig.digest}"
                ),
                error_code="numerical_digest_mismatch",
                verification_complete=False,
                row_ids=request.row_ids,
                request_binding_digest=binding,
                overhead_ms=(time.perf_counter() - t0) * 1000.0,
            )

        projector = create_projector(spec=spec, backend=backend)
        solve_t0 = time.perf_counter()
        result = projector.project(
            np.asarray(request.proposed_action, dtype=np.float64),
            None if request.previous_action is None else np.asarray(request.previous_action, dtype=np.float64),
            reference_action=(
                None if request.reference_action is None else np.asarray(request.reference_action, dtype=np.float64)
            ),
            policy_weight=request.policy_weight,
            reference_weight=request.reference_weight,
            metadata={
                **meta,
                "sidecar_trace_id": request.trace_id,
                "sidecar_row_ids": list(request.row_ids),
                "structural_fingerprint": expected_fp.digest,
                "numerical_signature": num_sig.digest,
                "client_numerical_parameters": dict(request.numerical_parameters),
                "request_binding_digest": binding,
            },
        )
        solve_ms = (time.perf_counter() - solve_t0) * 1000.0
        payload = result.as_dict()
        # Hard gate: refuse to mark complete unless S2 evidence is present.
        verification_complete = (
            result.verification is not None and result.release_decision is not None and bool(result.verification.passed)
        )
        prov: dict[str, Any] = {
            **worker_provenance_snapshot(moreau_available=_moreau_available()),
            "backend": str(backend),
        }
        if result.solver_provenance is not None and hasattr(result.solver_provenance, "as_dict"):
            prov["solver"] = result.solver_provenance.as_dict()
        if not verification_complete:
            return SolveResultMessage(
                trace_id=request.trace_id,
                ok=False,
                error="worker_refused_unverified_release",
                error_code="unverified",
                result=payload,
                verification_complete=False,
                row_ids=request.row_ids,
                request_binding_digest=binding,
                solver_provenance=prov,
                worker_solve_ms=solve_ms,
                overhead_ms=(time.perf_counter() - t0) * 1000.0,
            )
        return SolveResultMessage(
            trace_id=request.trace_id,
            ok=True,
            result=payload,
            verification_complete=True,
            row_ids=request.row_ids,
            request_binding_digest=binding,
            solver_provenance=prov,
            worker_solve_ms=solve_ms,
            overhead_ms=(time.perf_counter() - t0) * 1000.0,
        )
    except Exception as exc:  # noqa: BLE001 — fail closed with evidence
        return SolveResultMessage(
            trace_id=request.trace_id,
            ok=False,
            error=f"{type(exc).__name__}: {exc}",
            error_code="worker_exception",
            verification_complete=False,
            row_ids=request.row_ids,
            request_binding_digest=binding,
            overhead_ms=(time.perf_counter() - t0) * 1000.0,
            result={"traceback": traceback.format_exc()[-2000:]},
        )


def run_worker_loop(
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    """Serve until EOF or shutdown. Returns process exit code."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    worker_id = f"moreau-worker-{uuid.uuid4().hex[:12]}"
    moreau_ok = _moreau_available()
    hello_seen = False

    while True:
        line = _read_line(stdin)
        if line is None:
            return 0
        try:
            payload = decode_message(line)
        except SidecarProtocolError as exc:
            _write_message(
                stdout,
                error_message(code="protocol_error", message=str(exc)),
            )
            continue

        msg_type = payload.get("type")
        if msg_type == MessageType.HELLO.value:
            hello_seen = True
            client_supported = payload.get("supported_protocol_versions")
            try:
                ack = hello_ack_message(
                    worker_id=worker_id,
                    moreau_available=moreau_ok,
                    capabilities={
                        "protocol_version": PROTOCOL_VERSION,
                        "backends": ["native_moreau", "cvxpy_moreau"],
                        "transport": "persistent_subprocess_stdio",
                        "request_binding": True,
                    },
                    client_supported_versions=client_supported,
                )
            except SidecarProtocolError as exc:
                _write_message(
                    stdout,
                    error_message(code="protocol_negotiation_failed", message=str(exc)),
                )
                continue
            _write_message(stdout, ack)
            continue

        if not hello_seen:
            _write_message(
                stdout,
                error_message(code="hello_required", message="send hello before other messages"),
            )
            continue

        if msg_type == MessageType.PING.value:
            _write_message(
                stdout,
                {
                    "type": MessageType.PONG.value,
                    "protocol_version": PROTOCOL_VERSION,
                    "worker_id": worker_id,
                },
            )
            continue

        if msg_type == MessageType.SHUTDOWN.value:
            return 0

        if msg_type == MessageType.CANCEL.value:
            # Cancel is advisory; in-flight solve still completes
            # or fails closed — we never release a partial unverified action.
            _write_message(
                stdout,
                {
                    "type": MessageType.CANCEL_ACK.value,
                    "protocol_version": PROTOCOL_VERSION,
                    "trace_id": payload.get("trace_id"),
                    "accepted": True,
                    "note": "cancel_is_advisory_no_partial_release",
                },
            )
            continue

        if msg_type == MessageType.SOLVE.value:
            try:
                request = SolveRequest.from_message(payload)
            except (SidecarProtocolError, KeyError, TypeError, ValueError) as exc:
                _write_message(
                    stdout,
                    error_message(
                        code="bad_solve_request",
                        message=str(exc),
                        trace_id=None if not isinstance(payload, dict) else payload.get("trace_id"),
                    ),
                )
                continue
            # Deadline: if already expired, fail closed without solving.
            if request.deadline_ms is not None and request.deadline_ms <= 0:
                result = SolveResultMessage(
                    trace_id=request.trace_id,
                    ok=False,
                    error="deadline_exhausted_before_solve",
                    error_code="deadline",
                    verification_complete=False,
                    row_ids=request.row_ids,
                )
                _write_message(stdout, result.to_message())
                continue
            result = _handle_solve(request)
            _write_message(stdout, result.to_message())
            continue

        _write_message(
            stdout,
            error_message(
                code="unknown_type",
                message=f"unsupported message type: {msg_type!r}",
                trace_id=payload.get("trace_id"),
            ),
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ConicShield Moreau sidecar worker (stdio NDJSON)")
    parser.add_argument(
        "--require-moreau",
        action="store_true",
        help="Exit non-zero during hello if Moreau is unavailable",
    )
    args = parser.parse_args(argv)
    if args.require_moreau and not _moreau_available():
        sys.stderr.write("moreau unavailable; refusing to start (--require-moreau)\\n")
        return 2
    return run_worker_loop()


if __name__ == "__main__":
    raise SystemExit(main())

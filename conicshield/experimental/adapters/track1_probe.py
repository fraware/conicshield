"""Track 1 readiness probe for research adapters (S4 hetero-batch / S5 sidecar / S6).

Honest attestation only. Does **not** invent vendor success. Frontiers keep
``sequential_adapter`` watermarks unless S4 vendor hetero-batch is **live**-attested
(capability discovery alone is insufficient).
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.experimental.gradients.capability import CapabilityStatus

TRACK1_PROBE_SCHEMA_ID = "research.track1_readiness_probe.v0"
TRACK1_PROBE_VERSION = "t1-probe-v0.2.1"


@dataclass(slots=True)
class Track1CapabilityProbe:
    capability_id: str
    landed_in_track1: bool
    research_attested: bool
    capability_status: CapabilityStatus
    detail: str
    evidence_pointers: list[str] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)
    missing_evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "landed_in_track1": self.landed_in_track1,
            "research_attested": self.research_attested,
            "capability_status": str(self.capability_status),
            "detail": self.detail,
            "evidence_pointers": list(self.evidence_pointers),
            "extras": dict(self.extras),
            "missing_evidence": list(self.missing_evidence),
        }


@dataclass(slots=True)
class Track1ProbeReport:
    schema_id: str = TRACK1_PROBE_SCHEMA_ID
    probe_version: str = TRACK1_PROBE_VERSION
    probed_at_utc: str = ""
    platform: str = ""
    probes: list[Track1CapabilityProbe] = field(default_factory=list)
    frontiers_watermark_required: bool = True
    reduce_watermarks: bool = False
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "probe_version": self.probe_version,
            "probed_at_utc": self.probed_at_utc,
            "platform": self.platform,
            "probes": [p.as_dict() for p in self.probes],
            "frontiers_watermark_required": self.frontiers_watermark_required,
            "reduce_watermarks": self.reduce_watermarks,
            "notes": list(self.notes),
            "production_claim": False,
        }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inventory_s4_surfaces() -> dict[str, Any]:
    """What Track 1 batch surfaces exist as importable code vs vendor-executable."""

    surfaces: dict[str, Any] = {
        "Backend.NATIVE_MOREAU_BATCH": False,
        "create_batch_projector": False,
        "NativeMoreauCompiledBatchProjector": False,
        "CompiledShieldTemplate": False,
        "project_batch_method": False,
    }
    try:
        from conicshield.backends.base import Backend

        surfaces["Backend.NATIVE_MOREAU_BATCH"] = hasattr(Backend, "NATIVE_MOREAU_BATCH")
    except Exception as exc:  # noqa: BLE001
        surfaces["Backend_import_error"] = f"{type(exc).__name__}: {exc}"

    try:
        from conicshield.core.solver_factory import create_batch_projector

        surfaces["create_batch_projector"] = callable(create_batch_projector)
    except Exception as exc:  # noqa: BLE001
        surfaces["create_batch_projector_error"] = f"{type(exc).__name__}: {exc}"

    try:
        from conicshield.core.moreau_batched import NativeMoreauCompiledBatchProjector

        surfaces["NativeMoreauCompiledBatchProjector"] = True
        surfaces["project_batch_method"] = callable(getattr(NativeMoreauCompiledBatchProjector, "project_batch", None))
    except Exception as exc:  # noqa: BLE001
        surfaces["NativeMoreauCompiledBatchProjector_error"] = f"{type(exc).__name__}: {exc}"

    try:
        import conicshield.compilation.compiled_template as _cst

        surfaces["CompiledShieldTemplate"] = hasattr(_cst, "CompiledShieldTemplate")
        surfaces["CompiledShieldTemplate_module"] = "conicshield.compilation.compiled_template.CompiledShieldTemplate"
    except Exception as exc:  # noqa: BLE001
        surfaces["CompiledShieldTemplate_error"] = f"{type(exc).__name__}: {exc}"

    return surfaces


def _attempt_s4_live_batch_sample() -> dict[str, Any]:
    """Run a minimal same-topology batch solve; return attestation sample or failure reason.

    Capability discovery alone never counts as research attestation.
    On native Windows, Moreau is unsupported — fail closed without invoking the
    broken Windows stub import path (can AV under pytest + cvxpy solver discovery).
    """

    out: dict[str, Any] = {
        "attempted": False,
        "succeeded": False,
        "solver_version": None,
        "sample_hashes": {},
        "capability_flags": {},
        "error": None,
    }
    if sys.platform == "win32":
        out["capability_flags"] = {
            "package_importable": False,
            "native_compiled_api": False,
            "expected_api_available": False,
            "cpu_backend": False,
            "differentiation_api": False,
            "license_entitlement_valid": None,
            "windows_native_unsupported": True,
        }
        out["error"] = (
            "vendor_moreau_not_executable_on_this_host: native Windows unsupported "
            "(use WSL2/Linux for NATIVE_MOREAU_BATCH live attestation)"
        )
        out["import_error"] = out["error"]
        return out
    try:
        from conicshield.backends.base import Backend
        from conicshield.backends.capabilities import discover_moreau_family

        caps = discover_moreau_family(backend=Backend.NATIVE_MOREAU_BATCH, run_license_check=False)
        flags = {
            "package_importable": bool(getattr(caps, "package_importable", False)),
            "native_compiled_api": bool(getattr(caps, "native_compiled_api", False)),
            "expected_api_available": bool(getattr(caps, "expected_api_available", False)),
            "cpu_backend": bool(getattr(caps, "cpu_backend", False)),
            "differentiation_api": bool(getattr(caps, "differentiation_api", False)),
            "license_entitlement_valid": getattr(caps, "license_entitlement_valid", None),
        }
        out["capability_flags"] = flags
        identity = (getattr(caps, "details", {}) or {}).get("identity") or {}
        out["solver_version"] = identity.get("version")
        out["package_location"] = identity.get("location")
        out["import_error"] = identity.get("import_error")
        out["missing_api"] = list(identity.get("missing_api") or ())

        if not (flags["package_importable"] and flags["native_compiled_api"]):
            out["error"] = (
                "vendor_moreau_not_executable_on_this_host: "
                f"package_importable={flags['package_importable']} "
                f"native_compiled_api={flags['native_compiled_api']}"
            )
            return out

        # Live sample only after capability flags are green.
        from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
        from conicshield.core.solver_factory import create_batch_projector
        from conicshield.specs.schema import BoxConstraint, SafetySpec, SimplexConstraint

        spec = SafetySpec(
            spec_id="research/track1_s4_live_sample",
            version="0.1.0",
            action_dim=2,
            constraints=[
                SimplexConstraint(total=1.0),
                BoxConstraint(lower=[0.0, 0.0], upper=[1.0, 1.0]),
            ],
        )
        qs = np.asarray([[0.8, 0.2], [0.1, 0.9]], dtype=np.float64)
        out["attempted"] = True
        batch = create_batch_projector(
            spec=spec,
            backend=Backend.NATIVE_MOREAU_BATCH,
            native_options=NativeMoreauCompiledOptions(device="cpu", max_iter=200, verbose=False),
        )
        batch_result = batch.project_batch(qs)
        corrected = np.asarray(batch_result.corrected_actions, dtype=np.float64)
        out["succeeded"] = True
        out["sample_hashes"] = {
            "proposed_qs_sha256": _sha256_bytes(np.ascontiguousarray(qs).tobytes()),
            "corrected_batch_sha256": _sha256_bytes(np.ascontiguousarray(corrected).tobytes()),
            "n_rows": int(corrected.shape[0]),
        }
        return out
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out


def _probe_s4_hetero_batch() -> Track1CapabilityProbe:
    """S4: production ``project_batch`` / NATIVE_MOREAU_BATCH surface vs live vendor attestation."""

    pointers = [
        "conicshield.backends.base.Backend.NATIVE_MOREAU_BATCH",
        "conicshield.core.solver_factory.create_batch_projector",
        "conicshield.core.moreau_batched.NativeMoreauCompiledBatchProjector",
        "conicshield.compilation.compiled_template.CompiledShieldTemplate",
        "conicshield.experimental.frontiers.sweeps.probe_track1_hetero_batch_attestation",
        "docs/stabilization/TRACK1_COMPLETION_REPORT.md",
    ]
    surfaces = _inventory_s4_surfaces()
    landed = bool(
        surfaces.get("Backend.NATIVE_MOREAU_BATCH")
        and surfaces.get("create_batch_projector")
        and surfaces.get("NativeMoreauCompiledBatchProjector")
    )
    live = _attempt_s4_live_batch_sample()
    extras: dict[str, Any] = {
        "surfaces_present": surfaces,
        "live_sample": live,
        "attestation_bar": "live_batch_sample_required",
        "capability_discovery_alone_insufficient": True,
    }
    missing: list[str] = []
    if not landed:
        missing.append("Track 1 batch API surfaces incomplete or unimportable")
    flags = dict(live.get("capability_flags") or {})
    if not flags.get("package_importable"):
        missing.append("vendor moreau package_importable on this host")
    if not flags.get("native_compiled_api"):
        missing.append("vendor native_compiled_api (CompiledSolver/Settings)")
    if live.get("import_error"):
        missing.append(f"import_error: {live['import_error']}")
    if not live.get("succeeded"):
        missing.append("live NATIVE_MOREAU_BATCH project_batch sample with sample hashes")

    attested = bool(landed and live.get("succeeded") and live.get("sample_hashes"))
    if attested:
        detail = (
            "Track 1 S4 live hetero/same-topology batch sample succeeded; "
            f"solver_version={live.get('solver_version')}; "
            f"sample_hashes={live.get('sample_hashes')}"
        )
        status = CapabilityStatus.AVAILABLE
    else:
        detail = (
            "Track 1 S4 API/surfaces landed in-tree, but vendor live batch is UNATTESTED "
            f"on this host ({sys.platform}). "
            f"live_error={live.get('error')!r}. "
            "Research keeps sequential_adapter watermark."
        )
        status = CapabilityStatus.UNAVAILABLE

    return Track1CapabilityProbe(
        capability_id="S4_hetero_batch",
        landed_in_track1=landed,
        research_attested=attested,
        capability_status=status,
        detail=detail,
        evidence_pointers=pointers,
        extras=extras,
        missing_evidence=missing,
    )


def _research_sidecar_client_config() -> Any:
    """Delegate to research_sidecar env-aware config builder."""

    from conicshield.experimental.adapters.research_sidecar import (
        research_sidecar_client_config,
    )

    return research_sidecar_client_config()


def _probe_wsl_moreau_hint() -> dict[str, Any]:
    """Non-authoritative WSL Moreau presence hint (does not equal live sidecar attestation).

    Full WSL import probe is opt-in via ``CONICSHIELD_RESEARCH_PROBE_WSL_MOREAU=1``
    to keep default research probes fast on Windows.
    Uses ``CONICSHIELD_WSL_PYTHON`` when set (vendor Moreau often lives in a venv).
    """

    import os

    hint: dict[str, Any] = {
        "checked": False,
        "wsl_available": False,
        "moreau_importable": False,
        "full_probe": False,
    }
    try:
        from conicshield.platform.paths import detect_wsl_exe, is_windows_host, wsl_available

        hint["is_windows_host"] = is_windows_host()
        hint["wsl_available"] = bool(wsl_available())
        hint["wsl_exe"] = str(detect_wsl_exe() or "")
        hint["checked"] = True
        if not hint["wsl_available"]:
            return hint
        if os.environ.get("CONICSHIELD_RESEARCH_PROBE_WSL_MOREAU", "").lower() not in {
            "1",
            "true",
            "yes",
        }:
            hint["skipped_full_import"] = "set CONICSHIELD_RESEARCH_PROBE_WSL_MOREAU=1 for WSL moreau import probe"
            return hint
        import subprocess

        wsl = detect_wsl_exe()
        if wsl is None:
            return hint
        py = os.environ.get("CONICSHIELD_WSL_PYTHON", "python3").strip() or "python3"
        hint["wsl_python"] = py
        # Quote path safely for bash -lc; venv paths may contain spaces rarely.
        py_q = py.replace("'", "'\"'\"'")
        probe = subprocess.run(
            [
                str(wsl),
                "-e",
                "bash",
                "-lc",
                f"'{py_q}' -c 'import moreau; print(getattr(moreau, \"__version__\", \"ok\"))'",
            ],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        hint["full_probe"] = True
        hint["moreau_importable"] = probe.returncode == 0
        hint["stdout_tail"] = (probe.stdout or "")[-200:]
        hint["stderr_tail"] = (probe.stderr or "")[-200:]
        if not hint["moreau_importable"] and py == "python3":
            hint["hint"] = (
                "system WSL python3 lacks Moreau; set CONICSHIELD_WSL_PYTHON to a "
                "venv with CompiledSolver (e.g. .venv-wsl-moreau/bin/python)"
            )
    except Exception as exc:  # noqa: BLE001
        hint["error"] = f"{type(exc).__name__}: {exc}"
        hint["checked"] = True
    return hint


def _attempt_live_sidecar_hello() -> dict[str, Any]:
    """Opt-in live Windows sidecar hello; never fakes success."""

    import os

    out: dict[str, Any] = {
        "attempted": False,
        "succeeded": False,
        "worker_reachable": False,
        "error": None,
    }
    enable = os.environ.get("CONICSHIELD_RESEARCH_SIDECAR_ENABLE", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if not enable:
        out["error"] = "CONICSHIELD_RESEARCH_SIDECAR_ENABLE not set"
        return out
    if sys.platform != "win32":
        out["error"] = "live Windows sidecar hello requires win32"
        return out
    try:
        from conicshield.platform.windows_sidecar_client import WindowsSidecarClient

        out["attempted"] = True
        cfg = _research_sidecar_client_config()
        out["wsl_python"] = cfg.python_executable
        with WindowsSidecarClient(config=cfg) as client:
            running = bool(getattr(client, "is_running", False))
            worker_id = getattr(client, "_worker_id", None)
            out["worker_reachable"] = bool(running and worker_id)
            out["succeeded"] = out["worker_reachable"]
            out["worker_id_present"] = bool(worker_id)
            if not out["succeeded"]:
                out["error"] = "sidecar client started but Moreau worker not attested"
        return out
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out


def _probe_s5_sidecar() -> Track1CapabilityProbe:
    """S5: Windows / research sidecar — scaffolding vs live Moreau worker."""

    landed = False
    attested = False
    extras: dict[str, Any] = {}
    missing: list[str] = []
    pointers = [
        "conicshield.platform.sidecar_protocol",
        "conicshield.platform.windows_sidecar_client.WindowsSidecarClient",
        "conicshield.experimental.adapters.research_sidecar.probe_research_sidecar_capability",
        "docs/stabilization/TRACK1_COMPLETION_REPORT.md",
    ]
    try:
        import conicshield.platform.sidecar_protocol as sidecar_mod  # noqa: F401

        landed = True
        extras["production_sidecar_module"] = "conicshield.platform.sidecar_protocol"
    except Exception as exc:  # noqa: BLE001
        extras["production_sidecar_import_error"] = f"{type(exc).__name__}: {exc}"
        missing.append("production sidecar_protocol import")

    try:
        from conicshield.platform import windows_sidecar_client as wsc

        extras["has_windows_sidecar_client"] = hasattr(wsc, "WindowsSidecarClient")
        if not extras["has_windows_sidecar_client"]:
            missing.append("WindowsSidecarClient symbol")
    except Exception as exc:  # noqa: BLE001
        extras["windows_sidecar_client_error"] = f"{type(exc).__name__}: {exc}"
        missing.append("windows_sidecar_client import")

    extras["wsl_moreau_hint"] = _probe_wsl_moreau_hint()
    if extras["wsl_moreau_hint"].get("full_probe") and not extras["wsl_moreau_hint"].get("moreau_importable"):
        missing.append("WSL Moreau importable worker environment")
    elif not extras["wsl_moreau_hint"].get("wsl_available") and sys.platform == "win32":
        missing.append("WSL available for Moreau sidecar worker")
    else:
        missing.append(
            "live Moreau sidecar worker (optional WSL import probe via CONICSHIELD_RESEARCH_PROBE_WSL_MOREAU=1)"
        )
    live = _attempt_live_sidecar_hello()
    extras["live_sidecar_hello"] = live

    try:
        from conicshield.experimental.adapters.research_sidecar import (
            probe_research_sidecar_capability,
        )

        cap = probe_research_sidecar_capability()
        extras["research_sidecar"] = cap.as_dict()
        # Live worker attestation only — mock is not production / research attestation
        attested = bool(
            live.get("succeeded")
            and live.get("worker_reachable")
            and cap.worker_reachable
            and str(cap.status) == CapabilityStatus.AVAILABLE.value
        )
        if attested:
            detail = "Live research sidecar worker reachable and attested."
            status = CapabilityStatus.AVAILABLE
        else:
            detail = (
                "Track 1 sidecar scaffolding may be present, but live Moreau worker is "
                f"unattested (research outcome={cap.outcome}; "
                f"live_hello_error={live.get('error')!r}). Watermarks retained."
            )
            status = CapabilityStatus.UNAVAILABLE
            if not live.get("succeeded"):
                missing.append("live Moreau sidecar worker hello with require_moreau_on_hello")
    except Exception as exc:  # noqa: BLE001
        detail = f"S5 probe failed closed: {type(exc).__name__}: {exc}"
        status = CapabilityStatus.UNAVAILABLE
        missing.append(f"research_sidecar probe exception: {type(exc).__name__}")

    return Track1CapabilityProbe(
        capability_id="S5_sidecar",
        landed_in_track1=landed,
        research_attested=attested,
        capability_status=status,
        detail=detail,
        evidence_pointers=pointers,
        extras=extras,
        missing_evidence=missing,
    )


def _probe_s6_native_grads() -> Track1CapabilityProbe:
    """S6-adjacent: native exact/smoothed Moreau gradients (fail-closed until prod flag).

    Research attestation records ``CompiledSolver.backward`` + softplus smoothed
    backend as the live experimental surface. Production
    ``BackendCapabilities.differentiation_api`` stays false until identity symbols
    (``differentiate`` / ``DiffSettings`` / ``cvxpylayers``) exist — S6 Track-1
    clear still requires that production flag.
    """

    pointers = [
        "conicshield.experimental.gradients.exact_backend",
        "conicshield.experimental.gradients.smoothed_backend",
        "conicshield.experimental.gradients.kkt_research",
        "conicshield.experimental.gradients.smoothed_research",
        "conicshield.backends.capabilities.discover_moreau_family",
        "docs/stabilization/TRACK1_COMPLETION_REPORT.md",
    ]
    missing: list[str] = [
        "vendor differentiation_api productized (identity: differentiate|DiffSettings|cvxpylayers)",
    ]
    extras: dict[str, Any] = {
        "do_not_claim_native_grads": True,
        "research_modes_distinct": [
            "exact_research_kkt",
            "smoothed_research_projection",
        ],
        "gap_vs_research_kkt": {
            "research_kkt_covers": ("Public QP KKT linearization / smoothed projection adapters on Clarabel/SCS"),
            "native_exact_smoothed_covers": (
                "Vendor Moreau exact via CompiledSolver.backward+enable_grad; "
                "experimental softplus smoothed_backend_gradient on the Moreau shield QP "
                "(no vendor envelope API on Moreau 0.3.3)"
            ),
            "remaining_gap": (
                "S6 Track-1 clear requires production differentiation_api==True; "
                "experimental exact/smoothed backends alone do not clear S6"
            ),
        },
    }
    try:
        from conicshield.experimental.gradients.exact_backend import (
            _probe_vendor_compiled_backward,
            exact_backend_gradient,
        )
        from conicshield.experimental.gradients.smoothed_backend import (
            smoothed_backend_gradient,
        )

        vendor = _probe_vendor_compiled_backward()
        extras.update(
            {
                "differentiation_api": bool(vendor.get("differentiation_api")),
                "identity_differentiation_api": bool(vendor.get("identity_differentiation_api")),
                "vendor_compiled_backward_api": bool(vendor.get("vendor_compiled_backward_api")),
                "research_differentiation_surface": bool(vendor.get("research_differentiation_surface")),
                "package_importable": bool(vendor.get("package_importable")),
                "moreau_version": vendor.get("moreau_version"),
                "symbols_searched": vendor.get("symbols_searched"),
                "smoothed_mechanism": "softplus_inequality_softening_moreau_qp",
            }
        )
        if vendor.get("windows_native_unsupported"):
            extras["windows_native_unsupported"] = True
            missing.append("vendor Moreau CompiledSolver.backward executable on this host (Windows unsupported)")
        elif not vendor.get("vendor_compiled_backward_api"):
            missing.append("CompiledSolver.backward + Settings(enable_grad=True)")
        exact = exact_backend_gradient()
        smoothed = smoothed_backend_gradient()
        extras["exact_status"] = str(exact.status)
        extras["smoothed_status"] = str(smoothed.status)
        extras["exact_available"] = bool(exact.available)
        extras["smoothed_available"] = bool(smoothed.available)
        # Probe-without-data correctly reports UNAVAILABLE; surface readiness is
        # vendor_compiled_backward_api + smoothed implementation present.
        extras["experimental_exact_surface_ready"] = bool(vendor.get("vendor_compiled_backward_api"))
        extras["experimental_smoothed_surface_ready"] = bool(vendor.get("vendor_compiled_backward_api")) and not bool(
            vendor.get("windows_native_unsupported")
        )
        if (
            extras["differentiation_api"]
            and extras["experimental_exact_surface_ready"]
            and extras["experimental_smoothed_surface_ready"]
        ):
            return Track1CapabilityProbe(
                capability_id="S6_native_exact_smoothed_gradients",
                landed_in_track1=True,
                research_attested=True,
                capability_status=CapabilityStatus.AVAILABLE,
                detail="Native exact/smoothed Moreau gradients attested on this host.",
                evidence_pointers=pointers,
                extras=extras,
                missing_evidence=[],
            )
        if not extras["differentiation_api"]:
            missing.insert(0, "BackendCapabilities.differentiation_api == True")
        # Drop stale "smoothed unwired" once experimental surface is implemented.
        missing = [m for m in missing if "smoothed_backend_gradient live jacobian" not in m]
    except Exception as exc:  # noqa: BLE001
        return Track1CapabilityProbe(
            capability_id="S6_native_exact_smoothed_gradients",
            landed_in_track1=False,
            research_attested=False,
            capability_status=CapabilityStatus.UNAVAILABLE,
            detail=f"Native gradient probe failed: {type(exc).__name__}: {exc}",
            evidence_pointers=pointers,
            extras={"error": str(exc), **extras},
            missing_evidence=missing + [f"probe exception: {type(exc).__name__}"],
        )

    return Track1CapabilityProbe(
        capability_id="S6_native_exact_smoothed_gradients",
        landed_in_track1=False,
        research_attested=False,
        capability_status=CapabilityStatus.UNAVAILABLE,
        detail=(
            "S6 Track-1 not cleared: production differentiation_api false "
            "(identity symbols absent). Experimental research surface uses "
            "CompiledSolver.backward + softplus smoothed_backend_gradient. "
            f"research_differentiation_surface="
            f"{extras.get('research_differentiation_surface')} "
            f"vendor_compiled_backward_api={extras.get('vendor_compiled_backward_api')} "
            f"differentiation_api={extras.get('differentiation_api')}"
        ),
        evidence_pointers=pointers,
        extras=extras,
        missing_evidence=missing,
    )


def probe_track1_research_readiness() -> Track1ProbeReport:
    """Probe S4/S5/S6-relevant Track 1 surfaces; leave watermarks unless live-attested."""

    probes = [_probe_s4_hetero_batch(), _probe_s5_sidecar(), _probe_s6_native_grads()]
    s4 = next(p for p in probes if p.capability_id == "S4_hetero_batch")
    reduce = bool(s4.research_attested)
    notes = [
        "Probe is research attestation only; does not modify production APIs.",
        "Frontiers reduce_watermarks only when S4 live vendor batch sample is attested.",
        "Capability discovery (package_importable) alone never clears publication-grade watermark.",
        "Live S5 sidecar and native S6 gradients remain separate gates.",
        "Multi-host R4 real soak is tracked separately (see MULTI_HOST_SOAK_RUNBOOK.md).",
    ]
    if not reduce:
        notes.append(
            "S4 unattested on this host → frontiers retain sequential_adapter / NOT_PUBLICATION_GRADE watermark."
        )
    for p in probes:
        if p.missing_evidence:
            notes.append(f"{p.capability_id} missing: {'; '.join(p.missing_evidence[:4])}")
    return Track1ProbeReport(
        probed_at_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        platform=sys.platform,
        probes=probes,
        frontiers_watermark_required=not reduce,
        reduce_watermarks=reduce,
        notes=notes,
    )


def write_track1_probe_attestation(*, path: Path) -> Track1ProbeReport:
    report = probe_track1_research_readiness()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Track 1 research readiness probe")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/research/track1_probe/attestation.json"),
    )
    args = parser.parse_args()
    report = write_track1_probe_attestation(path=args.output)
    d = report.as_dict()
    print(
        f"wrote {args.output} reduce_watermarks={d['reduce_watermarks']} "
        f"probes={len(d['probes'])} version={d['probe_version']}"
    )


if __name__ == "__main__":
    main()

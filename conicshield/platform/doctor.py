"""Solver environment doctor for packaging / provenance evidence."""

from __future__ import annotations

import hashlib
import importlib.metadata
import os
import platform
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from conicshield.backends.base import (
    AUTO_PRODUCTION_ENV,
    Backend,
    configured_production_backend,
    resolve_backend,
)
from conicshield.backends.capabilities import discover_all_capabilities, evidence_subset
from conicshield.backends.identity import probe_moreau_package

_SECRET_ENV_KEYS = frozenset(
    {
        "MOREAU_LICENSE_KEY",
        "MOREAU_EXTRA_INDEX_URL",
        "MOREAU_PIP_EXTRA_INDEX_URL",
        "GEMFURY_TOKEN",
        "PIP_EXTRA_INDEX_URL",
        "UV_INDEX_URL",
        "TOKEN",
        "PASSWORD",
        "SECRET",
        "API_KEY",
    }
)


def _redact(text: str) -> str:
    out = text
    for key in _SECRET_ENV_KEYS:
        val = os.environ.get(key, "")
        if val and len(val) >= 4:
            out = out.replace(val, f"<{key}_REDACTED>")
    # Generic userinfo in URLs
    out = re.sub(r"(https?://)([^/@\s]+@)", r"\1<REDACTED>@", out)
    return out


def _env_type() -> str:
    if os.environ.get("VIRTUAL_ENV"):
        return "venv"
    if os.environ.get("CONDA_PREFIX"):
        return "conda"
    if sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        return "virtualenv_like"
    return "system"


def _git_commit(repo_root: Path | None = None) -> str | None:
    root = repo_root or Path(__file__).resolve().parents[2]
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if proc.returncode == 0:
            return (proc.stdout or "").strip() or None
    except Exception:  # noqa: BLE001
        return None
    return None


def _dist_record(name: str) -> dict[str, Any]:
    try:
        dist = importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        return {"name": name, "installed": False}
    loc = None
    try:
        loc = str(dist.locate_file(""))
    except Exception:  # noqa: BLE001
        loc = None
    digest = None
    try:
        record = Path(str(dist.locate_file("RECORD")))
        if record.is_file():
            digest = "sha256:" + hashlib.sha256(record.read_bytes()).hexdigest()
    except Exception:  # noqa: BLE001
        digest = None
    installer = None
    try:
        raw = dist.read_text("INSTALLER")
        installer = raw.strip() if raw else None
    except Exception:  # noqa: BLE001
        installer = None
    meta_name: str | None
    try:
        meta_name = str(dist.metadata["Name"])
    except Exception:  # noqa: BLE001
        meta_name = getattr(dist, "name", None) or name
    return {
        "name": meta_name,
        "installed": True,
        "version": dist.version,
        "location": loc,
        "wheel_or_dist_hash": digest,
        "installer": installer,
    }


def _cuda_runtime_info() -> dict[str, Any]:
    info: dict[str, Any] = {"nvidia_smi": None, "cuda_visible_devices_set": "CUDA_VISIBLE_DEVICES" in os.environ}
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version,name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if proc.returncode == 0:
            info["nvidia_smi"] = _redact((proc.stdout or "").strip()[:400])
        else:
            info["nvidia_smi_error"] = _redact((proc.stderr or proc.stdout or "")[:200])
    except FileNotFoundError:
        info["nvidia_smi"] = None
        info["reason"] = "nvidia-smi_not_found"
    except Exception as exc:  # noqa: BLE001
        info["error"] = _redact(f"{type(exc).__name__}: {exc}")[:200]
    return info


def _selected_solver_settings() -> dict[str, Any]:
    configured_value: str | None = None
    configured_error: str | None = None
    try:
        configured = configured_production_backend()
        configured_value = None if configured is None else configured.value
    except ValueError as exc:
        configured_error = str(exc)
    auto_resolved = resolve_backend(Backend.AUTO)
    return {
        "default_create_projector_backend": Backend.CVXPY_MOREAU.value,
        "auto_policy": {
            "env_var": AUTO_PRODUCTION_ENV,
            "configured_production_backend": configured_value,
            "configured_error": configured_error,
            "auto_resolves_to": auto_resolved.value,
            "never_selects_vendor_from_import": True,
        },
        "explicit_backends": [m.value for m in Backend if m is not Backend.AUTO],
    }


@dataclass(slots=True)
class SolverDoctorReport:
    """Full solver-doctor payload (secrets redacted)."""

    python_version: str
    os_name: str
    arch: str
    executable_path: str
    environment_type: str
    distributions: list[dict[str, Any]] = field(default_factory=list)
    moreau: dict[str, Any] = field(default_factory=dict)
    cvxpy_solver_registration: dict[str, Any] = field(default_factory=dict)
    available_devices: dict[str, Any] = field(default_factory=dict)
    license_check: dict[str, Any] = field(default_factory=dict)
    cuda: dict[str, Any] = field(default_factory=dict)
    conicshield_commit: str | None = None
    selected_solver_settings: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    capabilities_evidence_subset: dict[str, Any] = field(default_factory=dict)
    platform_notes: list[str] = field(default_factory=list)
    migration_warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_solver_doctor(
    *,
    run_license_check: bool = False,
    repo_root: Path | None = None,
) -> SolverDoctorReport:
    """Collect packaging / provenance / capability evidence for the active interpreter."""
    notes: list[str] = []
    if sys.platform.startswith("win"):
        notes.append(
            "Native Windows: vendor Moreau is unsupported; PUBLIC_CLARABEL / PUBLIC_SCS / AUTO "
            "remain the qualification path. Use WSL2 for Moreau capability probes."
        )

    caps = discover_all_capabilities(run_license_check=run_license_check)
    moreau = probe_moreau_package(run_license_check=run_license_check)

    cvxpy_reg: dict[str, Any] = {}
    try:
        import cvxpy as cp

        cvxpy_reg = {
            "cvxpy_version": getattr(cp, "__version__", None),
            "CLARABEL": hasattr(cp, "CLARABEL"),
            "SCS": hasattr(cp, "SCS"),
            "MOREAU": hasattr(cp, "MOREAU"),
        }
    except Exception as exc:  # noqa: BLE001
        cvxpy_reg = {"error": _redact(f"{type(exc).__name__}: {exc}")}

    devices: dict[str, Any] = {
        "cpu": True,
        "cuda": moreau.cuda_backend,
        "platform": sys.platform,
    }

    dist_names = [
        "conicshield",
        "numpy",
        "scipy",
        "cvxpy",
        "cvxpylayers",
        "clarabel",
        "scs",
        "moreau",
        "torch",
        "jax",
        "jaxlib",
    ]
    distributions = [_dist_record(n) for n in dist_names]

    return SolverDoctorReport(
        python_version=platform.python_version(),
        os_name=platform.system(),
        arch=platform.machine(),
        executable_path=sys.executable,
        environment_type=_env_type(),
        distributions=distributions,
        moreau=moreau.as_dict(),
        cvxpy_solver_registration=cvxpy_reg,
        available_devices=devices,
        license_check={
            "ran": bool(run_license_check),
            "valid": moreau.license_entitlement_valid,
            "error": moreau.license_check_error,
        },
        cuda=_cuda_runtime_info(),
        conicshield_commit=_git_commit(repo_root),
        selected_solver_settings=_selected_solver_settings(),
        capabilities={k: v.as_dict() for k, v in caps.items()},
        capabilities_evidence_subset=evidence_subset(caps),
        platform_notes=notes,
        migration_warnings=list(moreau.migration_warnings),
    )

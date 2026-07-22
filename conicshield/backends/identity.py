"""Package identity probes that do not trust ``import moreau`` alone.

A module named ``moreau`` on ``sys.path`` is insufficient: PyPI stubs and
incomplete installs can import while lacking the governed solver API.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import importlib.util
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Expected public symbols for Optimal Intellect Moreau (CPU/native path).
_EXPECTED_MOREAU_ATTRS: tuple[str, ...] = (
    "CompiledSolver",
    "Settings",
)

# Known distribution names for the approved vendor package channels.
_APPROVED_MOREAU_DIST_NAMES: frozenset[str] = frozenset(
    {
        "moreau",
        "moreau-cpu",
        "moreau-cuda",
    }
)

# Deprecated / mistaken install signals (migration warnings).
_DEPRECATED_INSTALL_HINTS: tuple[str, ...] = (
    "pip install moreau  # default PyPI index without vendor extra-index",
    "pip install -e '.[solver]' with moreau[cuda] for CPU-only hosts",
)


@dataclass(frozen=True, slots=True)
class DistributionIdentity:
    """Resolved packaging identity for an installed distribution."""

    import_name: str
    distribution_name: str | None
    version: str | None
    location: str | None
    wheel_or_dist_hash: str | None
    installer: str | None
    approved_channel: bool
    expected_api_present: bool
    missing_api: tuple[str, ...] = ()
    import_error: str | None = None
    notes: tuple[str, ...] = ()
    secrets_redacted: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PackageProbeResult:
    """Full probe for a candidate solver package."""

    identity: DistributionIdentity
    license_entitlement_valid: bool | None
    license_check_error: str | None = None
    cvxpy_solver_registered: bool | None = None
    cpu_backend: bool | None = None
    cuda_backend: bool | None = None
    native_compiled_api: bool | None = None
    differentiation_api: bool | None = None
    migration_warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["identity"] = self.identity.as_dict()
        return payload


def _safe_error(exc: BaseException, *, limit: int = 240) -> str:
    text = f"{type(exc).__name__}: {exc}"
    # Never echo credential-bearing env values that may appear in messages.
    for key in ("MOREAU_LICENSE_KEY", "MOREAU_EXTRA_INDEX_URL", "MOREAU_PIP_EXTRA_INDEX_URL", "TOKEN", "PASSWORD"):
        val = __import__("os").environ.get(key, "")
        if val and len(val) >= 8:
            text = text.replace(val, f"<{key}_REDACTED>")
    return text[:limit]


def _module_location(mod: Any) -> str | None:
    path = getattr(mod, "__file__", None)
    if path:
        return str(Path(path).resolve())
    spec = getattr(mod, "__spec__", None)
    origin = getattr(spec, "origin", None) if spec is not None else None
    return str(origin) if origin else None


def _dist_hash(dist: importlib.metadata.Distribution | None) -> str | None:
    if dist is None:
        return None
    try:
        locate = getattr(dist, "locate_file", None)
        if locate is None:
            return None
        # Hash RECORD when present (wheel installs); otherwise hash top-level path.
        record = locate("RECORD")
        record_path = Path(str(record))
        if record_path.is_file():
            digest = hashlib.sha256()
            digest.update(record_path.read_bytes())
            return f"sha256:{digest.hexdigest()}"
        files = list(getattr(dist, "files", None) or [])
        if not files:
            return None
        # Stable digest over RECORD-equivalent file list + hashes when available.
        digest = hashlib.sha256()
        for entry in sorted(str(f) for f in files):
            digest.update(entry.encode("utf-8", errors="replace"))
            digest.update(b"\0")
        return f"sha256-files:{digest.hexdigest()}"
    except Exception:  # noqa: BLE001 — best-effort provenance
        return None


def _installer_source(dist: importlib.metadata.Distribution | None) -> str | None:
    if dist is None:
        return None
    try:
        direct = dist.read_text("direct_url.json")
        if direct:
            # Avoid embedding tokens from direct_url; keep scheme/host only.
            import json

            data = json.loads(direct)
            url = str(data.get("url") or "")
            if "://" in url:
                scheme, rest = url.split("://", 1)
                host = rest.split("/", 1)[0]
                # Strip userinfo if present.
                if "@" in host:
                    host = host.rsplit("@", 1)[-1]
                return f"direct_url:{scheme}://{host}/…"
            return "direct_url"
        installer = dist.read_text("INSTALLER")
        if installer:
            return installer.strip()[:80] or None
    except Exception:  # noqa: BLE001
        return None
    return None


def _find_distribution(import_name: str) -> importlib.metadata.Distribution | None:
    candidates = [import_name, import_name.replace("_", "-")]
    for name in candidates:
        try:
            return importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            continue
    # Fall back: scan distributions providing the top-level module.
    try:
        for dist in importlib.metadata.distributions():
            try:
                top = dist.read_text("top_level.txt") or ""
            except Exception:  # noqa: BLE001
                continue
            names = {line.strip() for line in top.splitlines() if line.strip()}
            if import_name in names:
                return dist
    except Exception:  # noqa: BLE001
        return None
    return None


def probe_moreau_package(*, run_license_check: bool = False) -> PackageProbeResult:
    """Probe Moreau package identity and API completeness.

    Does **not** treat a successful ``import moreau`` as sufficient proof of the
    governed vendor stack.
    """
    notes: list[str] = []
    migration: list[str] = []
    spec = importlib.util.find_spec("moreau")
    if spec is None:
        identity = DistributionIdentity(
            import_name="moreau",
            distribution_name=None,
            version=None,
            location=None,
            wheel_or_dist_hash=None,
            installer=None,
            approved_channel=False,
            expected_api_present=False,
            missing_api=_EXPECTED_MOREAU_ATTRS,
            import_error=None,
            notes=("module_not_found",),
        )
        return PackageProbeResult(
            identity=identity,
            license_entitlement_valid=None,
            migration_warnings=tuple(_DEPRECATED_INSTALL_HINTS),
        )

    mod: Any | None = None
    import_error: str | None = None
    try:
        mod = importlib.import_module("moreau")
    except Exception as exc:  # noqa: BLE001
        import_error = _safe_error(exc)
        if sys.platform.startswith("win"):
            notes.append(
                "Native Windows is unsupported for vendor Moreau; use WSL2/Linux "
                "for Moreau capability probes and PUBLIC_* backends on Windows."
            )

    dist = _find_distribution("moreau")
    dist_name = None
    version = None
    if dist is not None:
        try:
            dist_name = str(dist.metadata["Name"])
        except Exception:  # noqa: BLE001
            dist_name = getattr(dist, "name", None)
        version = dist.version
    if mod is not None and version is None:
        version = getattr(mod, "__version__", None)
        version = str(version) if version is not None else None

    missing: list[str] = []
    if mod is not None:
        for attr in _EXPECTED_MOREAU_ATTRS:
            if not hasattr(mod, attr):
                missing.append(attr)
    else:
        missing = list(_EXPECTED_MOREAU_ATTRS)

    approved = bool(dist_name and dist_name.lower() in _APPROVED_MOREAU_DIST_NAMES)
    if mod is not None and missing:
        notes.append(
            "import succeeded but expected Moreau API is incomplete "
            "(possible wrong PyPI package or truncated install)"
        )
        migration.append(
            "Uninstall the stub: python -m pip uninstall -y moreau; "
            "reinstall via vendor extra-index with solver-moreau-cpu or solver-moreau-cuda."
        )
    if not approved and mod is not None:
        notes.append("distribution name not in approved Moreau channel set")
        migration.extend(_DEPRECATED_INSTALL_HINTS)

    identity = DistributionIdentity(
        import_name="moreau",
        distribution_name=None if dist_name is None else str(dist_name),
        version=version,
        location=_module_location(mod) if mod is not None else (spec.origin if spec else None),
        wheel_or_dist_hash=_dist_hash(dist),
        installer=_installer_source(dist),
        approved_channel=approved and not missing and import_error is None,
        expected_api_present=bool(mod is not None and not missing),
        missing_api=tuple(missing),
        import_error=import_error,
        notes=tuple(notes),
    )

    license_ok: bool | None = None
    license_err: str | None = None
    if run_license_check and mod is not None and not missing:
        try:
            check = getattr(mod, "check", None)
            if callable(check):
                check()
                license_ok = True
            else:
                license_ok = None
                notes.append("license_check_api_unavailable")
                identity = DistributionIdentity(
                    import_name=identity.import_name,
                    distribution_name=identity.distribution_name,
                    version=identity.version,
                    location=identity.location,
                    wheel_or_dist_hash=identity.wheel_or_dist_hash,
                    installer=identity.installer,
                    approved_channel=identity.approved_channel,
                    expected_api_present=identity.expected_api_present,
                    missing_api=identity.missing_api,
                    import_error=identity.import_error,
                    notes=tuple(notes),
                )
        except Exception as exc:  # noqa: BLE001
            license_ok = False
            license_err = _safe_error(exc)

    cvxpy_reg: bool | None = None
    try:
        import cvxpy as cp

        cvxpy_reg = hasattr(cp, "MOREAU")
    except Exception:  # noqa: BLE001
        cvxpy_reg = None

    cpu = None
    cuda = None
    if mod is not None and hasattr(mod, "device_available"):
        try:
            cpu = bool(mod.device_available("cpu"))
        except Exception:  # noqa: BLE001
            cpu = None
        try:
            cuda = bool(mod.device_available("cuda"))
        except Exception:  # noqa: BLE001
            cuda = None

    native = bool(mod is not None and hasattr(mod, "CompiledSolver"))
    diff_api = bool(
        mod is not None
        and (
            hasattr(mod, "differentiate")
            or hasattr(mod, "DiffSettings")
            or hasattr(mod, "cvxpylayers")
        )
    )

    return PackageProbeResult(
        identity=identity,
        license_entitlement_valid=license_ok,
        license_check_error=license_err,
        cvxpy_solver_registered=cvxpy_reg,
        cpu_backend=cpu,
        cuda_backend=cuda,
        native_compiled_api=native,
        differentiation_api=diff_api,
        migration_warnings=tuple(dict.fromkeys(migration)),
    )


def assert_supported_runtime(
    *,
    require_moreau: bool = False,
    python_min: tuple[int, int] = (3, 11),
    python_max_exclusive: tuple[int, int] = (3, 13),
) -> None:
    """Raise ``RuntimeError`` with an actionable message on unsupported combos."""
    ver = sys.version_info[:2]
    if ver < python_min or ver >= python_max_exclusive:
        raise RuntimeError(
            f"Unsupported Python {ver[0]}.{ver[1]}. "
            f"Governed builds require >={python_min[0]}.{python_min[1]}, "
            f"<{python_max_exclusive[0]}.{python_max_exclusive[1]}. "
            "Use a supported interpreter or see docs/DEVENV.md."
        )
    if require_moreau and sys.platform.startswith("win"):
        raise RuntimeError(
            "Vendor Moreau is not supported on native Windows. "
            "Use WSL2/Ubuntu for solver-moreau-cpu / solver-moreau-cuda, "
            "or use PUBLIC_CLARABEL / PUBLIC_SCS / AUTO on Windows."
        )

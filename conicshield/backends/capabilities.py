"""Backend capability discovery for packaging and solver-doctor evidence."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import asdict, dataclass, field
from typing import Any

from conicshield.backends.base import Backend
from conicshield.backends.identity import PackageProbeResult, probe_moreau_package


@dataclass(frozen=True, slots=True)
class CapabilityFlag:
    """Single capability bit with optional reason."""

    name: str
    available: bool
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BackendCapabilities:
    """Structured capability report for one logical backend."""

    backend: str
    package_importable: bool
    expected_api_available: bool
    license_entitlement_valid: bool | None
    cpu_backend: bool | None
    cuda_backend: bool | None
    cvxpy_integration_registered: bool | None
    native_compiled_api: bool | None
    differentiation_api: bool | None
    flags: tuple[CapabilityFlag, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["flags"] = [f.as_dict() for f in self.flags]
        return payload


def _cvxpy_solver_available(name: str) -> tuple[bool, str | None]:
    if importlib.util.find_spec("cvxpy") is None:
        return False, "cvxpy_not_installed"
    try:
        import cvxpy as cp

        solver = getattr(cp, name, None)
        if solver is None:
            return False, f"cvxpy_missing_{name}"
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"[:200]


def discover_public_clarabel() -> BackendCapabilities:
    ok, reason = _cvxpy_solver_available("CLARABEL")
    clarabel_spec = importlib.util.find_spec("clarabel") is not None
    return BackendCapabilities(
        backend=Backend.PUBLIC_CLARABEL.value,
        package_importable=clarabel_spec or ok,
        expected_api_available=ok,
        license_entitlement_valid=True if ok else None,
        cpu_backend=ok,
        cuda_backend=False,
        cvxpy_integration_registered=ok,
        native_compiled_api=False,
        differentiation_api=None,
        flags=(
            CapabilityFlag("package_importable", clarabel_spec or ok, reason),
            CapabilityFlag("expected_api_available", ok, reason),
            CapabilityFlag("cpu_backend", ok, reason),
            CapabilityFlag("cuda_backend", False, "public_clarabel_is_cpu"),
            CapabilityFlag("cvxpy_integration_registered", ok, reason),
            CapabilityFlag("native_compiled_api", False, "not_applicable"),
            CapabilityFlag("differentiation_api", False, "not_probed"),
            CapabilityFlag("license_entitlement_valid", bool(ok), "open_source"),
        ),
        details={"solver_name": "CLARABEL", "platform": sys.platform},
    )


def discover_public_scs() -> BackendCapabilities:
    ok, reason = _cvxpy_solver_available("SCS")
    scs_spec = importlib.util.find_spec("scs") is not None
    return BackendCapabilities(
        backend=Backend.PUBLIC_SCS.value,
        package_importable=scs_spec or ok,
        expected_api_available=ok,
        license_entitlement_valid=True if ok else None,
        cpu_backend=ok,
        cuda_backend=False,
        cvxpy_integration_registered=ok,
        native_compiled_api=False,
        differentiation_api=None,
        flags=(
            CapabilityFlag("package_importable", scs_spec or ok, reason),
            CapabilityFlag("expected_api_available", ok, reason),
            CapabilityFlag("cpu_backend", ok, reason),
            CapabilityFlag("cuda_backend", False, "public_scs_is_cpu"),
            CapabilityFlag("cvxpy_integration_registered", ok, reason),
            CapabilityFlag("native_compiled_api", False, "not_applicable"),
            CapabilityFlag("differentiation_api", False, "not_probed"),
            CapabilityFlag("license_entitlement_valid", bool(ok), "open_source"),
        ),
        details={"solver_name": "SCS", "platform": sys.platform},
    )


def discover_moreau_family(
    *,
    backend: Backend,
    probe: PackageProbeResult | None = None,
    run_license_check: bool = False,
) -> BackendCapabilities:
    result = probe if probe is not None else probe_moreau_package(run_license_check=run_license_check)
    ident = result.identity
    importable = ident.import_error is None and (importlib.util.find_spec("moreau") is not None)
    api_ok = bool(ident.expected_api_present)
    windows_unsupported = sys.platform.startswith("win")
    reason = ident.import_error
    if windows_unsupported:
        reason = reason or "moreau_unsupported_on_native_windows"

    return BackendCapabilities(
        backend=backend.value,
        package_importable=bool(importable and not windows_unsupported),
        expected_api_available=api_ok and not windows_unsupported,
        license_entitlement_valid=result.license_entitlement_valid,
        cpu_backend=False if windows_unsupported else result.cpu_backend,
        cuda_backend=False if windows_unsupported else result.cuda_backend,
        cvxpy_integration_registered=result.cvxpy_solver_registered,
        native_compiled_api=False if windows_unsupported else result.native_compiled_api,
        differentiation_api=result.differentiation_api,
        flags=(
            CapabilityFlag("package_importable", bool(importable and not windows_unsupported), reason),
            CapabilityFlag("expected_api_available", api_ok and not windows_unsupported, reason),
            CapabilityFlag(
                "license_entitlement_valid",
                bool(result.license_entitlement_valid)
                if result.license_entitlement_valid is not None
                else False,
                result.license_check_error,
            ),
            CapabilityFlag("cpu_backend", bool(result.cpu_backend), reason),
            CapabilityFlag("cuda_backend", bool(result.cuda_backend), reason),
            CapabilityFlag(
                "cvxpy_integration_registered",
                bool(result.cvxpy_solver_registered),
                None if result.cvxpy_solver_registered else "cp.MOREAU not registered",
            ),
            CapabilityFlag("native_compiled_api", bool(result.native_compiled_api), reason),
            CapabilityFlag("differentiation_api", bool(result.differentiation_api), reason),
        ),
        details={
            "identity": ident.as_dict(),
            "migration_warnings": list(result.migration_warnings),
            "platform": sys.platform,
        },
    )


def discover_all_capabilities(*, run_license_check: bool = False) -> dict[str, BackendCapabilities]:
    """Discover capabilities for every production :class:`Backend` (except AUTO)."""
    moreau_probe = probe_moreau_package(run_license_check=run_license_check)
    return {
        Backend.PUBLIC_CLARABEL.value: discover_public_clarabel(),
        Backend.PUBLIC_SCS.value: discover_public_scs(),
        Backend.CVXPY_MOREAU.value: discover_moreau_family(
            backend=Backend.CVXPY_MOREAU, probe=moreau_probe, run_license_check=run_license_check
        ),
        Backend.NATIVE_MOREAU.value: discover_moreau_family(
            backend=Backend.NATIVE_MOREAU, probe=moreau_probe, run_license_check=run_license_check
        ),
        Backend.NATIVE_MOREAU_BATCH.value: discover_moreau_family(
            backend=Backend.NATIVE_MOREAU_BATCH, probe=moreau_probe, run_license_check=run_license_check
        ),
    }


def evidence_subset(capabilities: dict[str, BackendCapabilities]) -> dict[str, Any]:
    """Normalized subset suitable for production projection evidence."""
    subset: dict[str, Any] = {}
    for key, caps in capabilities.items():
        subset[key] = {
            "package_importable": caps.package_importable,
            "expected_api_available": caps.expected_api_available,
            "cpu_backend": caps.cpu_backend,
            "cuda_backend": caps.cuda_backend,
            "cvxpy_integration_registered": caps.cvxpy_integration_registered,
            "native_compiled_api": caps.native_compiled_api,
        }
    return subset

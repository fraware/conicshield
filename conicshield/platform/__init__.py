"""Platform diagnostics, Windows modes, and Moreau sidecar client helpers."""

from conicshield.platform.doctor import SolverDoctorReport, run_solver_doctor
from conicshield.platform.sidecar_protocol import PROTOCOL_VERSION, FallbackPolicy
from conicshield.platform.windows_modes import WindowsOperatingMode, describe_modes
from conicshield.platform.windows_sidecar_client import (
    SidecarClientConfig,
    WindowsSidecarClient,
    start_sidecar_from_env,
)

__all__ = [
    "PROTOCOL_VERSION",
    "FallbackPolicy",
    "SidecarClientConfig",
    "SolverDoctorReport",
    "WindowsOperatingMode",
    "WindowsSidecarClient",
    "describe_modes",
    "run_solver_doctor",
    "start_sidecar_from_env",
]

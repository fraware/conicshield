"""Windows operating-mode qualification identifiers.

Three distinct modes are documented and tested. Native Moreau-on-Windows is
**not** a mode and must not be claimed.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from conicshield.platform.paths import is_windows_host, is_wsl_environment, wsl_available


class WindowsOperatingMode(StrEnum):
    """Qualified Windows-related operating modes (S6)."""

    WINDOWS_PUBLIC = "windows_public"
    WINDOWS_WSL_NATIVE_REPO = "windows_wsl_native_repo"
    WINDOWS_MOREAU_SIDECAR = "windows_moreau_sidecar"


MODE_SUMMARIES: dict[WindowsOperatingMode, str] = {
    WindowsOperatingMode.WINDOWS_PUBLIC: (
        "Native Windows Python with PUBLIC_CLARABEL / PUBLIC_SCS / AUTO→public. "
        "Schema, evidence, replay, CLI, and governance as far as publicly testable. "
        "Required in windows-ci."
    ),
    WindowsOperatingMode.WINDOWS_WSL_NATIVE_REPO: (
        "Repository and Python live inside WSL2. Path translation and artifact "
        "portability are qualified; vendor Moreau may be installed in that Linux env."
    ),
    WindowsOperatingMode.WINDOWS_MOREAU_SIDECAR: (
        "Native Windows app process + persistent WSL2 Moreau worker over stdio NDJSON. "
        "Not production-ready until qualification notes say what passed. "
        "Does not claim native Moreau-on-Windows."
    ),
}


def describe_modes() -> list[dict[str, Any]]:
    return [
        {
            "mode": mode.value,
            "summary": MODE_SUMMARIES[mode],
            "claims_native_moreau_on_windows": False,
        }
        for mode in WindowsOperatingMode
    ]


def detect_current_mode_hints() -> dict[str, Any]:
    """Best-effort environment hints — not a qualification certificate."""
    return {
        "is_windows_host": is_windows_host(),
        "is_wsl_environment": is_wsl_environment(),
        "wsl_exe_available": wsl_available(),
        "native_moreau_on_windows_supported": False,
        "modes": describe_modes(),
    }

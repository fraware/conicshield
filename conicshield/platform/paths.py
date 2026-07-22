"""Windows / WSL path and artifact portability helpers.

These utilities support two qualified modes:

* **Windows Public** — native Windows Python; artifact paths stay on NTFS.
* **WSL-native repository** — repo and Python live inside WSL2; paths are POSIX.

They intentionally do **not** claim native Moreau-on-Windows support.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

_DRIVE_PATH = re.compile(r"^([A-Za-z]):[\\/](.*)$")
_WSL_MNT = re.compile(r"^/mnt/([a-z])/(.*)$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class PathTranslation:
    """Result of translating a path between Windows and WSL forms."""

    source: str
    windows: str | None
    wsl: str | None
    portable_key: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "windows": self.windows,
            "wsl": self.wsl,
            "portable_key": self.portable_key,
        }


def is_windows_host() -> bool:
    return sys.platform == "win32"


def is_wsl_environment() -> bool:
    """Best-effort detection of a WSL2 Linux userspace."""
    if sys.platform != "linux":
        return False
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        return True
    try:
        release = Path("/proc/version").read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return False
    return "microsoft" in release or "wsl" in release


def windows_path_to_wsl(path: str | Path) -> str:
    """Convert ``C:\\Users\\...`` / ``C:/Users/...`` to ``/mnt/c/Users/...``."""
    text = str(path).strip().strip('"')
    if not text:
        raise ValueError("empty path")
    # Already a WSL mount path.
    mnt = _WSL_MNT.match(text.replace("\\", "/"))
    if mnt:
        drive, rest = mnt.group(1).lower(), mnt.group(2)
        return str(PurePosixPath("/mnt") / drive / PurePosixPath(rest))

    normalized = text.replace("/", "\\")
    match = _DRIVE_PATH.match(normalized)
    if not match:
        # Relative or UNC — not representable as /mnt/<drive>/...
        raise ValueError(f"cannot translate non-drive Windows path to WSL: {path!r}")
    drive = match.group(1).lower()
    rest = match.group(2).replace("\\", "/")
    return str(PurePosixPath("/mnt") / drive / PurePosixPath(rest))


def wsl_path_to_windows(path: str | Path) -> str:
    """Convert ``/mnt/c/Users/...`` to ``C:\\Users\\...``."""
    text = str(path).strip().strip('"').replace("\\", "/")
    if not text:
        raise ValueError("empty path")
    match = _WSL_MNT.match(text)
    if not match:
        raise ValueError(f"cannot translate non-/mnt/<drive> WSL path to Windows: {path!r}")
    drive = match.group(1).upper()
    rest = match.group(2).replace("/", "\\")
    return str(PureWindowsPath(f"{drive}:\\") / PureWindowsPath(rest))


def portable_artifact_key(path: str | Path) -> str:
    """Stable relative-ish key for comparing Windows and WSL artifact locations.

    Uses forward slashes and lower-cased drive letters when present so the same
    on-disk file yields one key from either host view.
    """
    text = str(path).strip().strip('"')
    try:
        wsl = windows_path_to_wsl(text) if _DRIVE_PATH.match(text.replace("/", "\\")) else text
    except ValueError:
        wsl = text.replace("\\", "/")
    try:
        if _WSL_MNT.match(wsl.replace("\\", "/")):
            wsl = wsl.replace("\\", "/")
        elif _DRIVE_PATH.match(text.replace("/", "\\")):
            wsl = windows_path_to_wsl(text)
    except ValueError:
        wsl = text.replace("\\", "/")
    # Prefer WSL form as the portable key when convertible.
    try:
        if _DRIVE_PATH.match(text.replace("/", "\\")):
            return windows_path_to_wsl(text)
        if _WSL_MNT.match(text.replace("\\", "/")):
            return text.replace("\\", "/")
    except ValueError:
        pass
    return text.replace("\\", "/")


def translate_path(path: str | Path) -> PathTranslation:
    text = str(path)
    windows: str | None = None
    wsl: str | None = None
    try:
        if _DRIVE_PATH.match(text.replace("/", "\\")):
            windows = str(PureWindowsPath(text.replace("/", "\\")))
            wsl = windows_path_to_wsl(windows)
        elif _WSL_MNT.match(text.replace("\\", "/")):
            wsl = text.replace("\\", "/")
            windows = wsl_path_to_windows(wsl)
        else:
            # Relative path — same lexical form both sides when repo-rooted.
            windows = text.replace("/", "\\") if is_windows_host() else None
            wsl = text.replace("\\", "/")
    except ValueError:
        windows = text if is_windows_host() else None
        wsl = text if not is_windows_host() else None
    return PathTranslation(
        source=text,
        windows=windows,
        wsl=wsl,
        portable_key=portable_artifact_key(text),
    )


def repo_root_candidates() -> list[Path]:
    """Likely repository roots from this package location."""
    here = Path(__file__).resolve()
    # conicshield/platform/paths.py → repo root is parents[2]
    return [here.parents[2]]


def detect_wsl_exe() -> str | None:
    """Return path to ``wsl.exe`` on a Windows host, else ``None``."""
    if not is_windows_host():
        return None
    system_root = os.environ.get("SYSTEMROOT", r"C:\Windows")
    candidate = Path(system_root) / "System32" / "wsl.exe"
    if candidate.is_file():
        return str(candidate)
    # PATH fallback
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        probe = Path(entry) / "wsl.exe"
        if probe.is_file():
            return str(probe)
    return None


def wsl_available() -> bool:
    """True when ``wsl.exe`` exists (does not prove a distro is installed)."""
    return detect_wsl_exe() is not None

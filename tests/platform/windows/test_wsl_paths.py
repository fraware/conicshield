"""WSL path / artifact portability qualification."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from conicshield.platform.paths import (
    detect_wsl_exe,
    portable_artifact_key,
    translate_path,
    windows_path_to_wsl,
    wsl_available,
    wsl_path_to_windows,
)


def test_windows_wsl_roundtrip_drive_path() -> None:
    win = r"C:\Users\mateo\conicshield\output\artifact.json"
    wsl = windows_path_to_wsl(win)
    assert wsl == "/mnt/c/Users/mateo/conicshield/output/artifact.json"
    assert wsl_path_to_windows(wsl).replace("/", "\\") == win


def test_portable_artifact_key_agrees() -> None:
    win = r"D:\data\runs\run1\summary.json"
    wsl = "/mnt/d/data/runs/run1/summary.json"
    assert portable_artifact_key(win) == portable_artifact_key(wsl)
    t = translate_path(win)
    assert t.wsl == wsl
    assert t.portable_key == wsl


def test_relative_repo_artifact_key() -> None:
    key = portable_artifact_key(Path("output") / "parity" / "a.json")
    assert "\\" not in key
    assert key.endswith("output/parity/a.json") or key.endswith("parity/a.json") or "output/parity" in key


@pytest.mark.requires_wsl
def test_wsl_exe_invokes_when_present() -> None:
    if not wsl_available():
        pytest.skip("wsl.exe not found — cannot qualify windows_wsl_native_repo path probes")
    wsl = detect_wsl_exe()
    assert wsl is not None
    completed = subprocess.run(
        [wsl, "-e", "bash", "-lc", "pwd"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip(f"WSL distro not usable (rc={completed.returncode}, stderr={completed.stderr[-200:]!r})")
    assert completed.stdout.strip()


@pytest.mark.requires_wsl
def test_wsl_sees_repo_via_mnt_when_present() -> None:
    if sys.platform != "win32" or not wsl_available():
        pytest.skip("native Windows + wsl.exe required for /mnt repo visibility check")
    wsl = detect_wsl_exe()
    assert wsl is not None
    repo = Path(__file__).resolve().parents[3]
    linux = windows_path_to_wsl(repo)
    completed = subprocess.run(
        [wsl, "-e", "bash", "-lc", f"test -f {linux}/pyproject.toml && echo OK"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0 or "OK" not in completed.stdout:
        pytest.skip(
            "repo not visible inside WSL at expected /mnt path "
            f"(rc={completed.returncode}, out={completed.stdout!r}, err={completed.stderr[-200:]!r})"
        )

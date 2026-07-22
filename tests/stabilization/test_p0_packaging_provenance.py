"""Packaging identity, wrong-package detection, and capability discovery."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

from conicshield.backends.capabilities import discover_all_capabilities, discover_public_clarabel
from conicshield.backends.identity import assert_supported_runtime, probe_moreau_package
from conicshield.cli import main as cli_main
from conicshield.platform.doctor import run_solver_doctor


def test_probe_moreau_missing_module(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    result = probe_moreau_package()
    assert result.identity.expected_api_present is False
    assert "CompiledSolver" in result.identity.missing_api


def test_wrong_package_import_without_compiled_solver(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = types.ModuleType("moreau")
    fake.__version__ = "0.0.0-stub"
    fake.__file__ = str(Path.cwd() / "fake_moreau.py")

    def _find_spec(name: str):
        if name == "moreau":
            return types.SimpleNamespace(origin=fake.__file__)
        return None

    monkeypatch.setattr(importlib.util, "find_spec", _find_spec)
    monkeypatch.setitem(sys.modules, "moreau", fake)
    # Bypass distribution scan noise
    import importlib.metadata as md

    def _no_dist(_name: str):
        raise md.PackageNotFoundError(_name)

    monkeypatch.setattr(md, "distribution", _no_dist)
    monkeypatch.setattr(md, "distributions", lambda: [])

    result = probe_moreau_package()
    assert result.identity.expected_api_present is False
    assert "CompiledSolver" in result.identity.missing_api
    assert result.native_compiled_api is False
    assert any("incomplete" in n or "wrong" in n.lower() for n in result.identity.notes) or result.migration_warnings


def test_complete_api_marks_native_compiled(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = types.ModuleType("moreau")
    fake.__version__ = "9.9.9"
    fake.__file__ = str(Path.cwd() / "real_moreau.py")
    fake.CompiledSolver = object
    fake.Settings = object

    def _find_spec(name: str):
        if name == "moreau":
            return types.SimpleNamespace(origin=fake.__file__)
        return None

    monkeypatch.setattr(importlib.util, "find_spec", _find_spec)
    monkeypatch.setitem(sys.modules, "moreau", fake)
    import importlib.metadata as md

    monkeypatch.setattr(md, "distribution", lambda _n: (_ for _ in ()).throw(md.PackageNotFoundError(_n)))
    monkeypatch.setattr(md, "distributions", lambda: [])

    result = probe_moreau_package()
    assert result.identity.expected_api_present is True
    assert result.native_compiled_api is True


def test_assert_supported_runtime_rejects_windows_moreau(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "version_info", (3, 11, 0, "final", 0))
    with pytest.raises(RuntimeError, match="not supported on native Windows"):
        assert_supported_runtime(require_moreau=True)


def test_public_capabilities_do_not_claim_cuda() -> None:
    caps = discover_public_clarabel()
    assert caps.cuda_backend is False


def test_discover_all_includes_public_and_vendor_keys() -> None:
    caps = discover_all_capabilities()
    assert "public_clarabel" in caps
    assert "cvxpy_moreau" in caps


def test_solver_doctor_json_cli(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli_main(["solver-doctor", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"python_version"' in out
    assert "MOREAU_LICENSE_KEY" not in out or "<MOREAU_LICENSE_KEY_REDACTED>" in out
    assert "auto_resolves_to" in out


def test_solver_doctor_report_fields() -> None:
    report = run_solver_doctor()
    payload = report.as_dict()
    for key in (
        "python_version",
        "os_name",
        "arch",
        "executable_path",
        "environment_type",
        "distributions",
        "moreau",
        "cvxpy_solver_registration",
        "available_devices",
        "cuda",
        "conicshield_commit",
        "selected_solver_settings",
        "capabilities",
        "capabilities_evidence_subset",
    ):
        assert key in payload
    auto = payload["selected_solver_settings"]["auto_policy"]
    assert auto["never_selects_vendor_from_import"] is True
    assert auto["auto_resolves_to"] == "public_clarabel"


def test_install_matrix_declares_no_cuda_for_public_and_cpu() -> None:
    import json
    import re
    from pathlib import Path

    matrix = json.loads(Path("packaging/install_matrix.json").read_text(encoding="utf-8"))
    assert matrix["profiles"]["solver-public"]["includes_cuda"] is False
    assert matrix["profiles"]["solver-moreau-cpu"]["includes_cuda"] is False
    assert matrix["profiles"]["solver-moreau-cuda"]["includes_cuda"] is True
    public_extra = Path("pyproject.toml").read_text(encoding="utf-8")
    match = re.search(
        r"solver-public\s*=\s*\[(.*?)\]",
        public_extra,
        flags=re.DOTALL,
    )
    assert match is not None
    block = match.group(1).lower()
    assert "cuda" not in block
    assert "moreau" not in block


def test_solver_public_constraints_exclude_cuda_tokens() -> None:
    lines = [
        ln.strip().lower()
        for ln in Path("packaging/constraints/solver-public.txt").read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    joined = "\n".join(lines)
    assert "cuda" not in joined
    assert "moreau" not in joined
    assert "clarabel==0.11.1" in joined
    assert "scs==3.2.11" in joined

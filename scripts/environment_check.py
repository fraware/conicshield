#!/usr/bin/env python3
"""Layer A: collect environment diagnostics and write output/environment_check.{json,md}."""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _try_import(name: str) -> dict[str, Any]:
    try:
        __import__(name)
    except Exception as exc:
        return {"name": name, "ok": False, "error": str(exc)[:300]}
    ver: str | None
    try:
        ver = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        mod = __import__(name)
        v2 = getattr(mod, "__version__", None)
        ver = str(v2) if v2 is not None else None
    return {"name": name, "ok": True, "version": ver}


def _moreau_probe() -> dict[str, Any]:
    out: dict[str, Any] = {"importable": False}
    spec = importlib.util.find_spec("moreau")
    if spec is None:
        return out
    out["importable"] = True
    try:
        import moreau

        out["version"] = getattr(moreau, "__version__", None)
        for fn in ("available_devices", "default_device"):
            if hasattr(moreau, fn):
                try:
                    out[fn] = str(getattr(moreau, fn)())
                except Exception as exc:  # noqa: BLE001
                    out[f"{fn}_error"] = str(exc)[:200]
        for dev in ("cpu", "cuda"):
            fn = "device_available"
            if hasattr(moreau, fn):
                try:
                    out[f"device_available_{dev}"] = bool(getattr(moreau, fn)(dev))
                except Exception as exc:  # noqa: BLE001
                    out[f"device_available_{dev}_error"] = str(exc)[:200]
    except Exception as exc:  # noqa: BLE001
        out["import_error"] = str(exc)[:300]
    return out


def _cvxpy_moreau_probe() -> dict[str, Any]:
    out: dict[str, Any] = {"cp_moreau": False}
    try:
        import cvxpy as cp

        out["cvxpy_version"] = getattr(cp, "__version__", None)
        out["cp_moreau"] = hasattr(cp, "MOREAU")
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:300]
    return out


def _moreau_check_subprocess() -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "moreau", "check"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        return {
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-800:],
            "stderr_tail": (proc.stderr or "")[-800:],
        }
    except FileNotFoundError:
        return {"skipped": True, "reason": "moreau module not runnable"}
    except subprocess.TimeoutExpired:
        return {"error": "timeout"}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)[:300]}


def _venv_hint() -> dict[str, Any]:
    """Best-effort signal that a dedicated env is active (not system Python)."""
    prefix = sys.prefix
    base = getattr(sys, "base_prefix", prefix)
    return {
        "virtual_env": os.environ.get("VIRTUAL_ENV"),
        "conda_prefix": os.environ.get("CONDA_PREFIX"),
        "prefix": prefix,
        "base_prefix": base,
        "prefix_differs_from_base": prefix != base,
    }


def _framework_imports() -> dict[str, Any]:
    """Optional learning-framework probes (Layer A5)."""
    out: dict[str, Any] = {}
    for name in ("torch", "jax"):
        out[name] = _try_import(name)
    return out


def _collect() -> dict[str, Any]:
    imports_required = [
        "numpy",
        "scipy",
        "cvxpy",
        "cvxpylayers",
        "jsonschema",
        "pytest",
        "pydantic",
    ]
    import_results = [_try_import(n) for n in imports_required]
    ok_all = all(r.get("ok") for r in import_results)

    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "executable": sys.executable,
        "venv": _venv_hint(),
        "imports": import_results,
        "imports_all_ok": ok_all,
        "frameworks_optional": _framework_imports(),
        "moreau": _moreau_probe(),
        "cvxpy": _cvxpy_moreau_probe(),
    }
    if payload["moreau"].get("importable"):
        payload["moreau_check"] = _moreau_check_subprocess()
    return payload


def _write_md(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# Environment check",
        "",
        f"Generated: {data.get('generated_at_utc', '')}",
        "",
        "## Imports",
        "",
        "| Package | OK | Version / error |",
        "|---------|----|-----------------|",
    ]
    for row in data.get("imports", []):
        ok = "yes" if row.get("ok") else "no"
        detail = row.get("version") or row.get("error") or ""
        lines.append(f"| {row.get('name')} | {ok} | {detail} |")
    lines.extend(
        [
            "",
            f"**All required imports OK:** {data.get('imports_all_ok')}",
            "",
            "## Python environment (venv / prefix)",
            "",
            "```json",
            json.dumps(data.get("venv"), indent=2),
            "```",
            "",
            "## Optional frameworks (PyTorch / JAX)",
            "",
            "```json",
            json.dumps(data.get("frameworks_optional"), indent=2),
            "```",
            "",
            "## Moreau",
            "",
            "```json",
            json.dumps(data.get("moreau"), indent=2),
            "```",
            "",
            "## CVXPY",
            "",
            "```json",
            json.dumps(data.get("cvxpy"), indent=2),
            "```",
        ]
    )
    if "moreau_check" in data:
        mc_json = json.dumps(data["moreau_check"], indent=2)
        lines.extend(["", "## python -m moreau check", "", "```json", mc_json, "```"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Write environment_check artifacts under output/.")
    p.add_argument("--out-dir", type=Path, default=None, help="Default: repo output/")
    args = p.parse_args()
    out_dir = args.out_dir or (_repo_root() / "output")
    out_dir.mkdir(parents=True, exist_ok=True)
    data = _collect()
    (out_dir / "environment_check.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    _write_md(out_dir / "environment_check.md", data)
    print(out_dir / "environment_check.json")
    return 0 if data.get("imports_all_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

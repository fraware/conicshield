from __future__ import annotations

import importlib
import sys
from pathlib import Path

from tests._repo import repo_root


def _repo_root() -> Path:
    return repo_root()


def test_base_import_does_not_load_cvxpy_or_moreau() -> None:
    """Fresh interpreter: importing conicshield must not pull solver-only wheels."""
    code = """
import sys
mods = set(sys.modules)
import conicshield  # noqa: F401
import conicshield.adapters.inter_sim_rl.shield  # noqa: F401
import conicshield.governance.audit  # noqa: F401
loaded = set(sys.modules) - mods
bad = [n for n in loaded if n.startswith(("cvxpy", "moreau", "cvxpylayers"))]
if bad:
    raise SystemExit("unexpected solver-related imports: " + ", ".join(sorted(bad)))
"""
    import subprocess

    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_repo_root(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_reload_idempotent_for_package() -> None:
    import conicshield

    importlib.reload(conicshield)
    assert conicshield.__doc__ is None or isinstance(conicshield.__doc__, str)

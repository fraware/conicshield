#!/usr/bin/env python3
"""Run vendor / licensed-host tests: loads repo ``.env``, then pytest with solver markers enabled.

Default CI excludes ``solver``, ``requires_moreau``, and ``inter_sim_rl`` (see ``pyproject.toml``).
Use this script locally when ``.env`` contains ``MOREAU_LICENSE_KEY`` / GemFury settings and optional
``INTERSIM_RL_ROOT``.

Optional: set ``CONICSHIELD_WRITE_MOREAU_KEY=1`` to write ``MOREAU_LICENSE_KEY`` to ``~/.moreau/key``
(Unix) or ``%USERPROFILE%\\.moreau\\key`` (Windows) before running tests — same behavior as CI secrets.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_dotenv(repo: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise SystemExit(
            "python-dotenv is required. Install dev deps: pip install -e \".[dev]\""
        ) from exc
    env_path = repo / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)


def _bootstrap_editable(repo: Path) -> int:
    """Install editable ``.[dev]`` and ``.[solver]`` into the current interpreter (needs network)."""
    print("Bootstrapping: pip install -e .[dev] ...", file=sys.stderr)
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", f"{repo}[dev]"],
        cwd=str(repo),
    )
    if r.returncode != 0:
        return r.returncode
    extra = os.environ.get("MOREAU_PIP_EXTRA_INDEX_URL", "").strip()
    if not extra:
        print(
            "MOREAU_PIP_EXTRA_INDEX_URL is not set (add to .env). "
            "Cannot install moreau; only base+dev were installed.",
            file=sys.stderr,
        )
        return 1
    print("Bootstrapping: pip install -e .[solver] (vendor index) ...", file=sys.stderr)
    r2 = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-e",
            f"{repo}[solver]",
            "--extra-index-url",
            extra,
        ],
        cwd=str(repo),
    )
    return r2.returncode


def _preflight_vendor_imports_or_exit() -> None:
    """Fail fast before pytest when the live lane cannot possibly exercise vendor code."""
    exe = sys.executable
    try:
        import cvxpy as cp  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            f"cvxpy is not installed for this interpreter:\n  {exe}\n"
            "Install the project into THIS environment (same command you use to run this script):\n"
            f'  "{exe}" -m pip install -e ".[dev]"\n'
            "Or from the repo root: python scripts/run_live_vendor_tests.py --bootstrap"
        ) from exc
    try:
        import moreau  # noqa: F401
    except ImportError as exc:
        err = str(exc).lower()
        if sys.platform == "win32" or "windows" in err or "wsl" in err:
            raise SystemExit(
                "Optimal Intellect Moreau is not supported on native Microsoft Windows.\n"
                "Use WSL2 (Ubuntu recommended), install Python 3.11+ there, clone the repo, copy .env, then:\n"
                "  python scripts/run_live_vendor_tests.py --bootstrap\n"
                "  python scripts/run_live_vendor_tests.py\n\n"
                "If pip previously installed a wrong PyPI stub named ``moreau``, remove it in WSL:\n"
                "  python -m pip uninstall -y moreau && python scripts/run_live_vendor_tests.py --bootstrap\n\n"
                "On Windows only, you may run a subset with:\n"
                "  python scripts/run_live_vendor_tests.py --skip-preflight\n"
                "(many tests will still skip without a real Moreau stack.)\n\n"
                f"Original error: {exc!r}"
            ) from exc
        raise SystemExit(
            f"moreau is not installed for this interpreter:\n  {exe}\n"
            "Ensure .env sets MOREAU_PIP_EXTRA_INDEX_URL, then run:\n"
            f'  "{exe}" -m pip install -e ".[solver]" --extra-index-url <URL from .env>\n'
            "Or: python scripts/run_live_vendor_tests.py --bootstrap"
        ) from exc

    # pip can fall back to an unrelated PyPI package named ``moreau`` on Windows; real solver has CompiledSolver.
    if not hasattr(moreau, "CompiledSolver"):
        raise SystemExit(
            "The installed ``moreau`` package does not look like Optimal Intellect Moreau "
            "(missing ``CompiledSolver``). On Windows this is usually a PyPI stub or an unsupported install.\n"
            "Use WSL2 + Linux wheels from your GemFury index, or uninstall the wrong package:\n"
            f'  "{exe}" -m pip uninstall -y moreau\n'
            "Then install again under WSL per README / docs/MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md."
        )

    try:
        if hasattr(cp, "MOREAU"):
            _ = cp.MOREAU
    except Exception as exc:
        err = str(exc).lower()
        if "windows" in err or "wsl" in err or sys.platform == "win32":
            raise SystemExit(
                "CVXPY could not load the MOREAU solver (vendor stack not usable on this OS).\n"
                "Run the live vendor suite under WSL2 / Linux. See error above.\n"
                f"Detail: {exc!r}"
            ) from exc
        raise


def _ensure_moreau_key_file() -> None:
    if os.environ.get("CONICSHIELD_WRITE_MOREAU_KEY", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    ):
        return
    key = os.environ.get("MOREAU_LICENSE_KEY", "").strip()
    if not key:
        return
    home = Path.home()
    d = home / ".moreau"
    d.mkdir(parents=True, exist_ok=True)
    key_path = d / "key"
    key_path.write_text(key, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run pytest with vendor markers (requires Moreau license / optional inter-sim-rl checkout). "
            "Loads .env from the repository root when present."
        )
    )
    parser.add_argument(
        "--include-slow",
        action="store_true",
        help="Include tests marked slow (e.g. doubled conic stress profile).",
    )
    parser.add_argument(
        "--no-dotenv",
        action="store_true",
        help="Do not load .env (use only the current process environment).",
    )
    parser.add_argument(
        "--parallel",
        type=str,
        default="",
        metavar="N",
        help="If pytest-xdist is installed, pass ``-n N`` (e.g. auto or 4). Default: run tests in-process.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the pytest command and exit 0 without running tests.",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help=(
            "Run pip install -e .[dev] and -e .[solver] (solver needs "
            "MOREAU_PIP_EXTRA_INDEX_URL in .env), then continue to pytest."
        ),
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Do not require cvxpy/moreau to be importable before pytest (not recommended).",
    )
    args, pytest_rest = parser.parse_known_args()

    repo = _repo_root()
    if not args.no_dotenv:
        _load_dotenv(repo)
    _ensure_moreau_key_file()

    if args.bootstrap:
        rc = _bootstrap_editable(repo)
        if rc != 0:
            return rc

    if not args.skip_preflight and not args.dry_run:
        _preflight_vendor_imports_or_exit()

    marker_expr = (
        "(vendor_moreau or requires_moreau or solver or inter_sim_rl)"
        + ("" if args.include_slow else " and not slow")
    )

    cmd: list[str] = [
        sys.executable,
        "-m",
        "pytest",
        str(repo / "tests"),
        "-m",
        marker_expr,
        "--override-ini",
        "addopts=-q -ra --tb=short --durations=40",
    ]

    if args.parallel:
        try:
            import importlib.util

            if importlib.util.find_spec("xdist") is not None:
                cmd.extend(["-n", args.parallel])
        except Exception:
            pass

    cmd.extend(pytest_rest)

    print("Live vendor pytest:", " ".join(cmd), file=sys.stderr)
    if args.dry_run:
        return 0
    return subprocess.call(cmd, cwd=str(repo), env=os.environ.copy())


if __name__ == "__main__":
    raise SystemExit(main())

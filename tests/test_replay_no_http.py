from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tests._repo import repo_root


def _repo_root() -> Path:
    return repo_root()


def test_replay_import_chain_has_no_third_party_http_clients() -> None:
    code = """
import sys
import conicshield.bench.replay_graph_env  # noqa: F401
import conicshield.bench.transition_bank  # noqa: F401
import conicshield.bench.episode_runner  # noqa: F401

BLOCKED_PREFIXES = ("requests", "httpx", "aiohttp", "urllib3", "http.client")
loaded = [name for name in sys.modules if name.startswith(BLOCKED_PREFIXES) or name == "urllib.request"]
if loaded:
    raise SystemExit("unexpected http client modules: " + ", ".join(sorted(loaded)))
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

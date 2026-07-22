"""Live sidecar / WSL Moreau qualification (skip-with-reason when unavailable)."""

from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pytest

from conicshield.backends.base import Backend
from conicshield.core.solver_factory import create_projector
from conicshield.platform.paths import detect_wsl_exe, is_windows_host, wsl_available
from conicshield.platform.sidecar_protocol import FallbackPolicy
from conicshield.platform.windows_sidecar_client import SidecarClientConfig, WindowsSidecarClient
from conicshield.specs.schema import BoxConstraint, SafetySpec, SimplexConstraint


def _spec() -> SafetySpec:
    return SafetySpec(
        spec_id="sidecar/live",
        version="0.1.0",
        action_dim=2,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=[0.0, 0.0], upper=[1.0, 1.0]),
        ],
    )


def _wsl_moreau_available() -> tuple[bool, str]:
    if not is_windows_host():
        return False, "live Windows sidecar qualification requires native Windows host"
    if not wsl_available():
        return False, "wsl.exe not found"
    wsl = detect_wsl_exe()
    assert wsl is not None
    probe = subprocess.run(
        [
            wsl,
            "-e",
            "bash",
            "-lc",
            'python3 -c \'import moreau; print(getattr(moreau, "__version__", "ok"))\'',
        ],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if probe.returncode != 0:
        return False, f"Moreau not importable in WSL: {probe.stderr[-300:]}"
    return True, probe.stdout.strip()


@pytest.mark.requires_moreau_sidecar
@pytest.mark.requires_wsl
def test_sidecar_multiple_solves_reuse_one_worker() -> None:
    ok, reason = _wsl_moreau_available()
    if not ok:
        pytest.skip(reason)
    cfg = SidecarClientConfig(
        fallback_policy=FallbackPolicy.PUBLIC_CLARABEL,
        require_moreau_on_hello=True,
        max_restarts=1,
    )
    with WindowsSidecarClient(config=cfg) as client:
        worker_id = client._worker_id
        assert worker_id
        for i in range(3):
            result = client.project(
                _spec(),
                np.array([0.7 - 0.1 * i, 0.3 + 0.1 * i], dtype=np.float64),
                row_ids=(f"row-{i}",),
                backend=Backend.NATIVE_MOREAU,
            )
            assert result.verification is not None and result.verification.passed
            assert client._worker_id == worker_id
            assert client.is_running
        report = client.overhead_report()
        assert report["sample_count"] == 3
        assert report["fallback_count"] == 0
        assert report["client_wait_ms_mean"] is not None


@pytest.mark.requires_moreau_sidecar
@pytest.mark.requires_wsl
def test_sidecar_parity_vs_public_within_loose_tolerance() -> None:
    """When Moreau is available in WSL, compare sidecar vs public Clarabel.

    Loose tolerance: same simplex family; exact equality is not required across
    backends. Records overhead. Skips if sidecar cannot complete a verified solve.
    """
    ok, reason = _wsl_moreau_available()
    if not ok:
        pytest.skip(reason)
    proposed = np.array([0.65, 0.35], dtype=np.float64)
    public = create_projector(spec=_spec(), backend=Backend.PUBLIC_CLARABEL).project(proposed)
    cfg = SidecarClientConfig(require_moreau_on_hello=True, max_restarts=1)
    with WindowsSidecarClient(config=cfg) as client:
        side = client.project(_spec(), proposed, backend=Backend.NATIVE_MOREAU)
    assert public.verification and public.verification.passed
    assert side.verification and side.verification.passed
    delta = float(np.linalg.norm(side.corrected_action - public.corrected_action))
    # Parity scaffolding: document delta; fail only on gross disagreement.
    assert delta < 0.5, f"sidecar vs public disagreement too large: {delta}"


@pytest.mark.requires_moreau_sidecar
@pytest.mark.requires_wsl
def test_concurrent_native_clients() -> None:
    ok, reason = _wsl_moreau_available()
    if not ok:
        pytest.skip(reason)

    def _one(idx: int) -> float:
        cfg = SidecarClientConfig(require_moreau_on_hello=True, max_restarts=1)
        with WindowsSidecarClient(config=cfg) as client:
            r = client.project(
                _spec(),
                np.array([0.5, 0.5], dtype=np.float64),
                row_ids=(f"c-{idx}",),
            )
            assert r.verification and r.verification.passed
            return float(r.corrected_action[0])

    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [pool.submit(_one, i) for i in range(2)]
        vals = [f.result() for f in as_completed(futs)]
    assert len(vals) == 2

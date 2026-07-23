"""Experiment provenance recording (directive section 7)."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from conicshield.experimental.provenance.audit import (
    SECTION7_REQUIRED_FIELDS,
    audit_provenance_completeness,
)

__all__ = [
    "ExperimentProvenance",
    "SECTION7_REQUIRED_FIELDS",
    "audit_provenance_completeness",
    "begin_experiment_provenance",
    "detect_platform_info",
    "finalize_experiment_provenance",
]


def _safe_git(*args: str) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", *args],
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=str(Path(__file__).resolve().parents[3]),
        )
        return out.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _package_meta(name: str) -> dict[str, str | None]:
    try:
        from importlib.metadata import distribution

        dist = distribution(name)
        return {
            "distribution": name,
            "version": dist.version,
            "source": None,
            "hash": None,
        }
    except Exception:
        return {"distribution": name, "version": None, "source": None, "hash": None}


@dataclass(slots=True)
class ExperimentProvenance:
    """Full provenance record required by Track 2 section 7."""

    repository_commit: str | None
    dirty_worktree: bool
    scenario_corpus_version: str
    solver_distribution: str | None
    solver_version: str | None
    package_source: str | None
    package_hash: str | None
    python_version: str
    operating_system: str
    cpu_info: str | None
    gpu_info: str | None
    cuda_runtime: str | None
    cuda_driver: str | None
    backend: str
    algorithm: str | None
    solver_settings: dict[str, Any]
    random_seeds: dict[str, int]
    batch_size: int | None
    warm_start_policy: str | None
    tolerances: dict[str, float]
    fallback_policy: str | None
    exact_command: str
    start_time_utc: str
    completion_time_utc: str | None = None
    output_artifact_hashes: dict[str, str] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def detect_platform_info() -> dict[str, str | None]:
    cpu = platform.processor() or platform.machine() or None
    gpu = os.environ.get("CONICSHIELD_GPU_INFO")
    cuda_runtime = os.environ.get("CUDA_VERSION") or os.environ.get("CUDA_HOME")
    cuda_driver = os.environ.get("NVIDIA_DRIVER_VERSION")
    return {
        "cpu_info": cpu,
        "gpu_info": gpu,
        "cuda_runtime": cuda_runtime,
        "cuda_driver": cuda_driver,
        "operating_system": f"{platform.system()} {platform.release()}",
        "python_version": sys.version.split()[0],
    }


def begin_experiment_provenance(
    *,
    scenario_corpus_version: str,
    backend: str,
    exact_command: str,
    random_seeds: dict[str, int] | None = None,
    solver_settings: dict[str, Any] | None = None,
    tolerances: dict[str, float] | None = None,
    algorithm: str | None = None,
    batch_size: int | None = None,
    warm_start_policy: str | None = None,
    fallback_policy: str | None = None,
    solver_distribution: str | None = None,
) -> ExperimentProvenance:
    """Start a provenance record at experiment begin."""

    commit = _safe_git("rev-parse", "HEAD")
    dirty = bool(_safe_git("status", "--porcelain"))
    plat = detect_platform_info()
    pkg = (
        _package_meta(solver_distribution)
        if solver_distribution
        else {
            "distribution": None,
            "version": None,
            "source": None,
            "hash": None,
        }
    )
    return ExperimentProvenance(
        repository_commit=commit,
        dirty_worktree=dirty,
        scenario_corpus_version=scenario_corpus_version,
        solver_distribution=pkg["distribution"],
        solver_version=pkg["version"],
        package_source=pkg["source"],
        package_hash=pkg["hash"],
        python_version=str(plat["python_version"]),
        operating_system=str(plat["operating_system"]),
        cpu_info=plat["cpu_info"],
        gpu_info=plat["gpu_info"],
        cuda_runtime=plat["cuda_runtime"],
        cuda_driver=plat["cuda_driver"],
        backend=backend,
        algorithm=algorithm,
        solver_settings=dict(solver_settings or {}),
        random_seeds=dict(random_seeds or {}),
        batch_size=batch_size,
        warm_start_policy=warm_start_policy,
        tolerances=dict(tolerances or {}),
        fallback_policy=fallback_policy,
        exact_command=exact_command,
        start_time_utc=datetime.now(UTC).isoformat(),
    )


def finalize_experiment_provenance(
    provenance: ExperimentProvenance,
    *,
    artifact_paths: list[Path] | None = None,
) -> ExperimentProvenance:
    """Stamp completion time and optional artifact hashes."""

    hashes: dict[str, str] = dict(provenance.output_artifact_hashes)
    for path in artifact_paths or []:
        if path.is_file():
            hashes[str(path)] = _sha256_file(path)
    provenance.completion_time_utc = datetime.now(UTC).isoformat()
    provenance.output_artifact_hashes = hashes
    return provenance

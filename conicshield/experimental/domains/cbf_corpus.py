"""Held-out CBF validation corpus (separate from R0 solver-assurance corpus).

Versioned under ``cbf-v0.1.0``. Reproducible generator writes committed scenarios
used by the stage-4 gate held-out criterion. Does not bump ``r0-v0.3.0``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np

from conicshield.experimental.corpus.paths import RESEARCH_ROOT
from conicshield.experimental.domains.cbf_2d import (
    AgentState2D,
    CircularObstacle,
    apply_cbf_filter,
    apply_cbf_filter_soc_robust,
)

CBF_CORPUS_VERSION = "cbf-v0.1.0"
CBF_CORPUS_FAMILY_ID = "research.cbf_2d.held_out"
CBF_CORPUS_SCHEMA_ID = "research.cbf_held_out_corpus.v0"
CBF_CORPUS_ROOT = RESEARCH_ROOT / "corpus" / "cbf"
CBF_SCENARIOS_DIR = CBF_CORPUS_ROOT / "scenarios"
CBF_MANIFEST_PATH = CBF_CORPUS_ROOT / "manifest.json"
CBF_VERSION_PATH = CBF_CORPUS_ROOT / "VERSION"

# Minimum held-out nominal count required before stage-4 margin criterion can pass.
MIN_HELD_OUT_NOMINAL = 12

Regime = Literal[
    "held_out_nominal",
    "near_boundary",
    "stress_tight_u_max",
    "declared_infeasible_geometry",
]


@dataclass(slots=True)
class CBFCorpusCase:
    case_id: str
    regime: Regime
    seed: int
    agent: dict[str, Any]
    obstacle: dict[str, Any]
    alpha: float = 1.0
    u_max: float = 1.0
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "regime": self.regime,
            "seed": self.seed,
            "agent": dict(self.agent),
            "obstacle": dict(self.obstacle),
            "alpha": float(self.alpha),
            "u_max": float(self.u_max),
            "notes": self.notes,
            "corpus_version": CBF_CORPUS_VERSION,
            "corpus_family_id": CBF_CORPUS_FAMILY_ID,
        }

    def to_agent_obstacle(self) -> tuple[AgentState2D, CircularObstacle]:
        ag = self.agent
        ob = self.obstacle
        return (
            AgentState2D(
                position=np.asarray(ag["position"], dtype=np.float64),
                u_desired=np.asarray(ag["u_desired"], dtype=np.float64),
                agent_id=str(ag.get("agent_id", self.case_id)),
            ),
            CircularObstacle(
                center=np.asarray(ob["center"], dtype=np.float64),
                radius=float(ob["radius"]),
                obstacle_id=str(ob.get("obstacle_id", f"obs_{self.case_id}")),
            ),
        )


@dataclass(slots=True)
class CBFCorpusManifest:
    schema_id: str = CBF_CORPUS_SCHEMA_ID
    corpus_version: str = CBF_CORPUS_VERSION
    corpus_family_id: str = CBF_CORPUS_FAMILY_ID
    generation_commit: str = ""
    case_count: int = 0
    regimes: dict[str, list[str]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "corpus_version": self.corpus_version,
            "corpus_family_id": self.corpus_family_id,
            "generation_commit": self.generation_commit,
            "case_count": self.case_count,
            "regimes": {k: sorted(v) for k, v in self.regimes.items()},
            "notes": list(self.notes),
            "min_held_out_nominal": MIN_HELD_OUT_NOMINAL,
        }


def _generation_commit_token() -> str:
    payload = f"{CBF_CORPUS_VERSION}|{CBF_CORPUS_FAMILY_ID}|cbf_corpus.py:v1|{MIN_HELD_OUT_NOMINAL}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _case(
    *,
    case_id: str,
    regime: Regime,
    seed: int,
    position: np.ndarray,
    u_desired: np.ndarray,
    center: np.ndarray,
    radius: float,
    alpha: float = 1.0,
    u_max: float = 1.0,
    notes: str = "",
) -> CBFCorpusCase:
    return CBFCorpusCase(
        case_id=case_id,
        regime=regime,
        seed=seed,
        agent={
            "agent_id": case_id,
            "position": np.asarray(position, dtype=np.float64).reshape(2).tolist(),
            "u_desired": np.asarray(u_desired, dtype=np.float64).reshape(2).tolist(),
        },
        obstacle={
            "obstacle_id": f"obs_{case_id}",
            "center": np.asarray(center, dtype=np.float64).reshape(2).tolist(),
            "radius": float(radius),
        },
        alpha=float(alpha),
        u_max=float(u_max),
        notes=notes,
    )


def generate_cbf_held_out_cases(*, seed: int = 0) -> list[CBFCorpusCase]:
    """Deterministic held-out + stress cases (distinct from demo_stage1 defaults)."""

    rng = np.random.default_rng(seed)
    cases: list[CBFCorpusCase] = []

    # --- held_out_nominal: safe geometries with moderate desired controls ---
    for i in range(MIN_HELD_OUT_NOMINAL):
        # Place agent outside obstacle with clearance; desired control toward/away
        angle = float(rng.uniform(0.0, 2.0 * np.pi))
        dist = float(rng.uniform(0.9, 1.8))
        radius = float(rng.uniform(0.25, 0.45))
        center = np.array([float(rng.uniform(-0.5, 0.5)), float(rng.uniform(-0.5, 0.5))])
        direction = np.array([np.cos(angle), np.sin(angle)])
        position = center + dist * direction
        # Desired velocity with bounded magnitude
        u_des = float(rng.uniform(0.3, 0.9)) * np.array(
            [np.cos(angle + float(rng.uniform(-0.4, 0.4))), np.sin(angle + float(rng.uniform(-0.4, 0.4)))]
        )
        cases.append(
            _case(
                case_id=f"cbf_held_nominal_{i:03d}",
                regime="held_out_nominal",
                seed=seed + i,
                position=position,
                u_desired=u_des,
                center=center,
                radius=radius,
                notes="held-out nominal; expected nonnegative CBF margin when solvable",
            )
        )

    # --- near_boundary: agent close to obstacle surface ---
    for i in range(4):
        angle = float(rng.uniform(0.0, 2.0 * np.pi))
        radius = 0.4
        center = np.zeros(2)
        position = center + (radius + 0.05 + 0.02 * i) * np.array([np.cos(angle), np.sin(angle)])
        u_des = -0.8 * np.array([np.cos(angle), np.sin(angle)])  # toward obstacle
        cases.append(
            _case(
                case_id=f"cbf_near_boundary_{i:03d}",
                regime="near_boundary",
                seed=seed + 100 + i,
                position=position,
                u_desired=u_des,
                center=center,
                radius=radius,
                notes="near-boundary stress; intervention expected",
            )
        )

    # --- stress_tight_u_max: feasible but tight control budget ---
    for i in range(3):
        cases.append(
            _case(
                case_id=f"cbf_tight_umax_{i:03d}",
                regime="stress_tight_u_max",
                seed=seed + 200 + i,
                position=np.array([0.0, 0.0]),
                u_desired=np.array([0.9, 0.0]),
                center=np.array([1.0 + 0.1 * i, 0.0]),
                radius=0.45,
                u_max=0.35 + 0.05 * i,
                notes="tight u_max stress; may be infeasible under aggressive desired control",
            )
        )

    # --- declared_infeasible_geometry: agent inside obstacle (h < 0) with tiny u_max ---
    for i in range(3):
        cases.append(
            _case(
                case_id=f"cbf_declared_infeas_{i:03d}",
                regime="declared_infeasible_geometry",
                seed=seed + 300 + i,
                position=np.array([0.05 * i, 0.0]),
                u_desired=np.array([1.0, 0.0]),
                center=np.array([0.0, 0.0]),
                radius=0.5,
                u_max=0.05,
                notes="agent inside obstacle + tiny u_max; expect infeasible or fallback",
            )
        )

    return cases


def generate_cbf_corpus(*, root: Path | None = None, seed: int = 0) -> dict[str, Any]:
    """Write versioned CBF held-out corpus to disk and return manifest dict."""

    corpus_root = root or CBF_CORPUS_ROOT
    scenarios_dir = corpus_root / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    for path in scenarios_dir.glob("*.json"):
        path.unlink()

    gen_commit = _generation_commit_token()
    cases = generate_cbf_held_out_cases(seed=seed)
    by_regime: dict[str, list[str]] = {}
    for case in cases:
        path = scenarios_dir / f"{case.case_id}.json"
        path.write_text(json.dumps(case.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        by_regime.setdefault(case.regime, []).append(case.case_id)

    manifest = CBFCorpusManifest(
        generation_commit=gen_commit,
        case_count=len(cases),
        regimes=by_regime,
        notes=[
            "Separate from R0 solver-assurance corpus (r0-v0.3.0 unchanged).",
            "Seeds and generator reproduce every case.",
            "Used by stage-4 gate held-out and infeasibility taxonomy probes.",
        ],
    )
    (corpus_root / "manifest.json").write_text(
        json.dumps(manifest.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (corpus_root / "VERSION").write_text(CBF_CORPUS_VERSION + "\n", encoding="utf-8")
    return manifest.as_dict()


def load_cbf_manifest(*, root: Path | None = None) -> dict[str, Any]:
    path = (root / "manifest.json") if root is not None else CBF_MANIFEST_PATH
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"cbf manifest must be an object: {path}")
    return cast(dict[str, Any], raw)


def load_cbf_cases(*, root: Path | None = None) -> list[CBFCorpusCase]:
    corpus_root = root or CBF_CORPUS_ROOT
    scenarios_dir = corpus_root / "scenarios"
    out: list[CBFCorpusCase] = []
    for path in sorted(scenarios_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        out.append(
            CBFCorpusCase(
                case_id=str(raw["case_id"]),
                regime=cast(Regime, str(raw["regime"])),
                seed=int(raw["seed"]),
                agent=dict(raw["agent"]),
                obstacle=dict(raw["obstacle"]),
                alpha=float(raw.get("alpha", 1.0)),
                u_max=float(raw.get("u_max", 1.0)),
                notes=str(raw.get("notes") or ""),
            )
        )
    return out


def held_out_nominal_cases(*, root: Path | None = None) -> list[CBFCorpusCase]:
    return [c for c in load_cbf_cases(root=root) if c.regime == "held_out_nominal"]


def evaluate_held_out_nominal(*, root: Path | None = None) -> dict[str, Any]:
    """Run nominal CBF filter on held-out cases; return margins + feasibility stats."""

    cases = held_out_nominal_cases(root=root)
    margins: list[float] = []
    infeas = 0
    results: list[dict[str, Any]] = []
    for case in cases:
        agent, obs = case.to_agent_obstacle()
        r = apply_cbf_filter(agent, obs, alpha=case.alpha, u_max=case.u_max)
        margins.append(float(r.safety_margin))
        bad = r.solver_status not in {"optimal", "optimal_inaccurate"} or not np.all(np.isfinite(r.u_safe))
        if bad:
            infeas += 1
        results.append(
            {
                "case_id": case.case_id,
                "solver_status": r.solver_status,
                "safety_margin": float(r.safety_margin),
                "barrier_value": float(r.barrier_value),
                "feasible": not bad,
            }
        )
    return {
        "corpus_version": CBF_CORPUS_VERSION,
        "n_held_out": len(cases),
        "min_safety_margin": float(min(margins)) if margins else float("nan"),
        "infeasible_count": infeas,
        "results": results,
    }


def probe_cbf_filter_bank(*, root: Path | None = None) -> list[Any]:
    """Diverse filter results for infeasibility taxonomy (nominal + robust + stress)."""

    from conicshield.experimental.domains.cbf_2d import (
        demo_stage1_scenario,
        demo_stage2_batch,
        demo_stage3_soc_robust,
    )

    probes: list[Any] = []
    probes.append(demo_stage1_scenario())
    probes.extend(demo_stage2_batch())
    probes.append(demo_stage3_soc_robust())
    for case in load_cbf_cases(root=root):
        agent, obs = case.to_agent_obstacle()
        probes.append(apply_cbf_filter(agent, obs, alpha=case.alpha, u_max=case.u_max))
        if case.regime in {"held_out_nominal", "near_boundary"}:
            probes.append(apply_cbf_filter_soc_robust(agent, obs, alpha=case.alpha, u_max=case.u_max, epsilon=0.05))
    return probes


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate CBF held-out corpus")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    manifest = generate_cbf_corpus(root=args.root, seed=args.seed)
    print(
        f"cbf corpus {manifest['corpus_version']} cases={manifest['case_count']} regimes={sorted(manifest['regimes'])}"
    )


if __name__ == "__main__":
    main()

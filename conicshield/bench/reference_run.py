from __future__ import annotations

import argparse
import json
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np

from conicshield.adapters.inter_sim_rl.policy import InterSimKerasDQNPolicy
from conicshield.adapters.inter_sim_rl.shield import InterSimConicShield
from conicshield.artifacts.summary_builder import build_summary_records
from conicshield.artifacts.validator import validate_run_bundle
from conicshield.bench.episode_runner import InterSimEpisodeRunner
from conicshield.bench.passthrough_projector import PassthroughProjector
from conicshield.bench.replay_graph_env import ReplayGraphEnvironment
from conicshield.bench.transition_bank import TransitionBank
from conicshield.core.interfaces import ProjectorProtocol
from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.solver_factory import Backend, create_projector
from conicshield.specs.compiler import SolverOptions
from conicshield.specs.schema import SafetySpec


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _copy_schema_templates(dest: Path) -> None:
    schemas = _repo_root() / "schemas"
    for name in ("config.schema.json", "summary.schema.json", "episodes.schema.json"):
        shutil.copy2(schemas / name, dest / name)


def _fixture_config_template() -> dict[str, Any]:
    path = _repo_root() / "tests" / "fixtures" / "parity_reference" / "config.json"
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _constant_q_policy() -> InterSimKerasDQNPolicy:
    class _Model:
        q = np.array([0.1, 3.0, 0.0, -1.0], dtype=float)

        class _Inner:
            @staticmethod
            def predict(x: Any, verbose: int = 0) -> np.ndarray:
                return np.array([_Model.q], dtype=float)

        model = _Inner()

    return InterSimKerasDQNPolicy(dqn_model=_Model())


def _live_projector_factory() -> Callable[..., ProjectorProtocol]:
    def factory(
        spec: SafetySpec,
        backend: Backend,
        solver_options: SolverOptions | None,
        native_options: Any,
    ) -> ProjectorProtocol:
        return create_projector(
            spec=spec,
            backend=backend,
            cvxpy_options=solver_options,
            native_options=native_options,
        )

    return factory


def run_benchmark_bundle(
    *,
    out_dir: Path,
    bank: TransitionBank,
    use_passthrough_projector: bool,
    seed: int = 7,
    include_native_arm: bool = False,
    benchmark_name: str | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    policy = _constant_q_policy()
    bank.to_json(out_dir / "transition_bank.json")

    cfg = _fixture_config_template()
    if benchmark_name is not None:
        cfg["benchmark_name"] = benchmark_name
    bank_id = "generated_bank"
    cfg["transition_bank"]["bank_id"] = bank_id
    cfg["created_at_utc"] = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _passthrough_factory(
        _spec: SafetySpec,
        _backend: Backend,
        _solver_options: SolverOptions | None,
        _native_options: NativeMoreauCompiledOptions | None,
    ) -> ProjectorProtocol:
        return PassthroughProjector()

    projector_factory: Callable[..., ProjectorProtocol] = (
        _passthrough_factory if use_passthrough_projector else _live_projector_factory()
    )

    arms_spec: list[tuple[str, str, InterSimConicShield | None]] = [
        ("baseline-unshielded", "none", None),
        (
            "shielded-rules-only",
            "cvxpy_moreau",
            InterSimConicShield(
                backend=Backend.CVXPY_MOREAU,
                use_geometry_prior=False,
                projector_factory=projector_factory,
            ),
        ),
        (
            "shielded-rules-plus-geometry",
            "cvxpy_moreau",
            InterSimConicShield(
                backend=Backend.CVXPY_MOREAU,
                use_geometry_prior=True,
                projector_factory=projector_factory,
            ),
        ),
    ]

    if include_native_arm:
        if use_passthrough_projector:
            raise ValueError("include_native_arm is not supported with passthrough_projector")
        arms_spec.append(
            (
                "shielded-native-moreau",
                "native_moreau",
                InterSimConicShield(
                    backend=Backend.NATIVE_MOREAU,
                    use_geometry_prior=True,
                    projector_factory=projector_factory,
                ),
            )
        )

    episodes_out: list[dict[str, Any]] = []

    for arm_label, backend_str, shield in arms_spec:

        def env_factory(b: TransitionBank = bank) -> ReplayGraphEnvironment:
            return ReplayGraphEnvironment(bank=b, rule_choice="right", max_intersections=1)

        runner = InterSimEpisodeRunner(
            env_factory=env_factory,
            policy=policy,
            shield=shield,
            epsilon=0.0,
            seed=seed,
            arm_label=arm_label,
            backend=backend_str,
            bank_id=bank_id,
            policy_id=cfg["policy"]["policy_id"],
            policy_checkpoint=cfg["policy"].get("checkpoint"),
        )
        ep = runner.run_episode(f"{arm_label}-001")
        episodes_out.append(ep.as_dict())

    summary = build_summary_records(episodes_out)

    _copy_schema_templates(out_dir)
    (out_dir / "episodes.jsonl").write_text(
        "\n".join(json.dumps(ep, separators=(",", ":")) for ep in episodes_out) + "\n",
        encoding="utf-8",
    )
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    validate_run_bundle(out_dir)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run governed benchmark episodes and write a validate_run_bundle directory.",
    )
    parser.add_argument("--out", type=Path, required=True, help="Output directory (created).")
    parser.add_argument("--bank", type=Path, required=True, help="Transition bank JSON path.")
    parser.add_argument(
        "--passthrough-projector",
        action="store_true",
        help="Use PassthroughProjector instead of real CVXPY/Moreau (for CI without a license).",
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--include-native-arm",
        action="store_true",
        help="Include native_moreau arm (requires solver).",
    )
    parser.add_argument("--benchmark-name", type=str, default=None)
    args = parser.parse_args()

    bank = TransitionBank.from_json(args.bank)
    run_benchmark_bundle(
        out_dir=args.out,
        bank=bank,
        use_passthrough_projector=bool(args.passthrough_projector),
        seed=args.seed,
        include_native_arm=bool(args.include_native_arm),
        benchmark_name=args.benchmark_name,
    )
    print(f"Wrote validated bundle: {args.out}")


if __name__ == "__main__":
    main()

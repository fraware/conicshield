from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class ArtifactValidationError(RuntimeError):
    pass


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _iter_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ArtifactValidationError(
                    f"Invalid JSONL in {path} at line {line_no}: {exc}"
                ) from exc
            if not isinstance(payload, dict):
                raise ArtifactValidationError(
                    f"Expected JSON object in {path} at line {line_no}"
                )
            records.append(payload)
    return records


def _validate_schema(payload: Any, schema: dict[str, Any], *, name: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    if not errors:
        return

    formatted: list[str] = []
    for err in errors[:20]:
        path = ".".join(str(x) for x in err.absolute_path) or "<root>"
        formatted.append(f"{name}: {path}: {err.message}")

    raise ArtifactValidationError("\n".join(formatted))


def _assert_close(a: float, b: float, *, tol: float = 1e-8, msg: str = "") -> None:
    if abs(a - b) > tol:
        raise ArtifactValidationError(msg or f"Expected {a} ~= {b}")


def validate_episode_record(ep: dict[str, Any]) -> None:
    steps = ep["steps"]

    if ep["num_steps"] != len(steps):
        raise ArtifactValidationError(
            f"{ep['episode_id']}: num_steps != len(steps)"
        )

    if ep["num_interventions"] != sum(int(s["intervened"]) for s in steps):
        raise ArtifactValidationError(
            f"{ep['episode_id']}: num_interventions inconsistent with steps"
        )

    total_reward = sum(float(s["reward"]) for s in steps)
    _assert_close(
        float(ep["total_reward"]),
        total_reward,
        msg=f"{ep['episode_id']}: total_reward inconsistent with step rewards",
    )

    rule_violations = 0
    matched_action_steps = 0
    fallback_steps = 0

    for idx, s in enumerate(steps):
        proposed = s.get("proposed_distribution")
        corrected = s.get("corrected_distribution")

        if proposed is not None:
            if len(proposed) != 4:
                raise ArtifactValidationError(
                    f"{ep['episode_id']} step {idx}: proposed_distribution length != 4"
                )
            _assert_close(
                float(sum(proposed)),
                1.0,
                tol=1e-6,
                msg=f"{ep['episode_id']} step {idx}: proposed_distribution not normalized",
            )

        if corrected is not None:
            if len(corrected) != 4:
                raise ArtifactValidationError(
                    f"{ep['episode_id']} step {idx}: corrected_distribution length != 4"
                )
            if min(float(x) for x in corrected) < -1e-8:
                raise ArtifactValidationError(
                    f"{ep['episode_id']} step {idx}: corrected_distribution has negative mass"
                )
            _assert_close(
                float(sum(corrected)),
                1.0,
                tol=1e-6,
                msg=f"{ep['episode_id']} step {idx}: corrected_distribution not normalized",
            )

        if s["matched_action"]:
            matched_action_steps += 1
        if s["fallback_used"]:
            fallback_steps += 1

        prev = s.get("previous_instruction")
        act = s["chosen_action"]
        rule = ep["rule_choice"]

        if prev is not None:
            prev_l = str(prev).lower()
            if rule == "right" and "right" in prev_l and act != "turn_right":
                rule_violations += 1
            elif rule == "left" and "left" in prev_l and act != "turn_left":
                rule_violations += 1
            elif rule == "alternate":
                if "left" in prev_l and act != "turn_right":
                    rule_violations += 1
                elif "right" in prev_l and act != "turn_left":
                    rule_violations += 1

    if ep.get("rule_violations") is not None and ep["rule_violations"] != rule_violations:
        raise ArtifactValidationError(
            f"{ep['episode_id']}: rule_violations inconsistent with step data"
        )

    if ep.get("matched_action_steps") is not None and ep["matched_action_steps"] != matched_action_steps:
        raise ArtifactValidationError(
            f"{ep['episode_id']}: matched_action_steps inconsistent with step data"
        )

    if ep.get("fallback_steps") is not None and ep["fallback_steps"] != fallback_steps:
        raise ArtifactValidationError(
            f"{ep['episode_id']}: fallback_steps inconsistent with step data"
        )


def validate_summary_records(
    summaries: list[dict[str, Any]],
    episodes: list[dict[str, Any]],
) -> None:
    episodes_by_label: dict[str, list[dict[str, Any]]] = {}
    for ep in episodes:
        episodes_by_label.setdefault(ep["arm_label"], []).append(ep)

    seen_labels: set[str] = set()

    for summary in summaries:
        label = summary["label"]
        seen_labels.add(label)

        eps = episodes_by_label.get(label, [])
        if len(eps) != summary["episodes"]:
            raise ArtifactValidationError(
                f"Summary {label}: episodes count mismatch"
            )

        if not eps:
            continue

        avg_reward = sum(float(ep["total_reward"]) for ep in eps) / len(eps)
        avg_steps = sum(int(ep["num_steps"]) for ep in eps) / len(eps)
        avg_interventions = sum(int(ep["num_interventions"]) for ep in eps) / len(eps)

        _assert_close(float(summary["avg_reward"]), avg_reward, tol=1e-8, msg=f"Summary {label}: avg_reward mismatch")
        _assert_close(float(summary["avg_steps"]), avg_steps, tol=1e-8, msg=f"Summary {label}: avg_steps mismatch")
        _assert_close(float(summary["avg_interventions_per_episode"]), avg_interventions, tol=1e-8, msg=f"Summary {label}: avg_interventions_per_episode mismatch")

        total_steps = sum(int(ep["num_steps"]) for ep in eps)
        total_intervened = sum(sum(int(step["intervened"]) for step in ep["steps"]) for ep in eps)
        expected_intervention_rate = total_intervened / total_steps if total_steps else 0.0
        _assert_close(float(summary["intervention_rate"]), expected_intervention_rate, tol=1e-8, msg=f"Summary {label}: intervention_rate mismatch")

        total_rule_violations = sum(int(ep.get("rule_violations", 0)) for ep in eps)
        total_rule_opportunities = 0
        for ep in eps:
            for step in ep["steps"]:
                if step.get("previous_instruction") is not None:
                    total_rule_opportunities += 1
        expected_rule_violation_rate = total_rule_violations / total_rule_opportunities if total_rule_opportunities else 0.0
        _assert_close(float(summary["rule_violation_rate"]), expected_rule_violation_rate, tol=1e-8, msg=f"Summary {label}: rule_violation_rate mismatch")

        total_matched = sum(int(ep.get("matched_action_steps", 0)) for ep in eps)
        total_fallback = sum(int(ep.get("fallback_steps", 0)) for ep in eps)

        expected_matched = total_matched / total_steps if total_steps else 0.0
        expected_fallback = total_fallback / total_steps if total_steps else 0.0

        _assert_close(float(summary["matched_action_rate"]), expected_matched, tol=1e-8, msg=f"Summary {label}: matched_action_rate mismatch")
        _assert_close(float(summary["fallback_rate"]), expected_fallback, tol=1e-8, msg=f"Summary {label}: fallback_rate mismatch")

    missing = set(episodes_by_label) - seen_labels
    if missing:
        raise ArtifactValidationError(
            f"Missing summaries for labels: {sorted(missing)}"
        )


def validate_run_bundle(run_dir: str | Path) -> None:
    run_dir = Path(run_dir)

    required = [
        "config.json",
        "config.schema.json",
        "summary.json",
        "summary.schema.json",
        "episodes.jsonl",
        "episodes.schema.json",
        "transition_bank.json",
    ]
    missing = [name for name in required if not (run_dir / name).exists()]
    if missing:
        raise ArtifactValidationError(f"Missing required files: {missing}")

    config = _load_json(run_dir / "config.json")
    config_schema = _load_json(run_dir / "config.schema.json")
    summary = _load_json(run_dir / "summary.json")
    summary_schema = _load_json(run_dir / "summary.schema.json")
    episodes = _iter_jsonl(run_dir / "episodes.jsonl")
    episodes_schema = _load_json(run_dir / "episodes.schema.json")
    _load_json(run_dir / "transition_bank.json")

    _validate_schema(config, config_schema, name="config.json")
    _validate_schema(summary, summary_schema, name="summary.json")
    episode_record_schema = {
        "$ref": "#/$defs/episodeRecord",
        "$defs": episodes_schema["$defs"],
    }
    for i, ep in enumerate(episodes):
        _validate_schema(ep, episode_record_schema, name=f"episodes.jsonl[{i}]")

    for ep in episodes:
        validate_episode_record(ep)

    validate_summary_records(summary, episodes)

    optional_governance = run_dir / "governance_status.json"
    optional_governance_schema = run_dir / "governance_status.schema.json"
    if optional_governance.exists() and optional_governance_schema.exists():
        governance_status = _load_json(optional_governance)
        governance_schema = _load_json(optional_governance_schema)
        _validate_schema(governance_status, governance_schema, name="governance_status.json")

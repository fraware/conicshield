from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from conicshield.bench.offline_graph_export import load_offline_graph_export, transition_bank_from_offline_graph_export
from conicshield.bench.transition_bank import TransitionBank, build_transition_bank


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _bank_file_schema() -> dict[str, Any]:
    path = _repo_root() / "schemas" / "transition_bank_file.schema.json"
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _validate_bank_payload(payload: dict[str, Any]) -> None:
    Draft202012Validator(_bank_file_schema()).validate(payload)


def _demo_callbacks() -> tuple[Any, Any]:
    graph: dict[str, list[dict[str, Any]]] = {
        "Root": [
            {
                "destination_address": "A",
                "destination_coords": [1.0, 0.0],
                "first_instruction": "Turn right",
                "action_class": "turn_right",
                "duration_sec": 10.0,
                "distance_m": 100.0,
            }
        ],
        "A": [],
    }

    coords: dict[str, tuple[float, float]] = {"Root": (0.0, 0.0), "A": (1.0, 0.0)}

    def candidate_builder(address: str) -> list[dict[str, Any]]:
        return list(graph.get(address, []))

    def coord_lookup(address: str) -> tuple[float, float] | None:
        return coords.get(address)

    return candidate_builder, coord_lookup


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline transition-bank builder (demo graph or custom hooks via Python API).",
    )
    parser.add_argument("--out", type=Path, required=True, help="Output JSON path.")
    parser.add_argument("--demo", action="store_true", help="Emit a small two-node demo bank.")
    parser.add_argument(
        "--from-json",
        type=Path,
        help="Load TransitionBank-compatible JSON (root_address + nodes) and re-write with new provenance.",
    )
    parser.add_argument(
        "--from-offline-graph-export",
        type=Path,
        help=(
            "Load offline_transition_graph_export/v1 JSON (from inter-sim-rl RLEnvironment.offline_transition_graph "
            "plus coords_by_address) and build a transition bank."
        ),
    )
    parser.add_argument("--bank-id", type=str, default=None, help="Provenance bank_id (default: random).")
    parser.add_argument("--generator", type=str, default="conicshield.bench.build_transition_bank")
    args = parser.parse_args()

    notes: str
    modes = sum(
        1 for flag in (args.from_json is not None, args.from_offline_graph_export is not None, args.demo) if flag
    )
    if modes != 1:
        raise SystemExit("Specify exactly one of --demo, --from-json, or --from-offline-graph-export.")
    if args.from_json is not None:
        bank = TransitionBank.from_json(args.from_json)
        notes = f"from-json source={args.from_json}"
    elif args.from_offline_graph_export is not None:
        export_payload = load_offline_graph_export(args.from_offline_graph_export)
        bank = transition_bank_from_offline_graph_export(export_payload)
        notes = f"from-offline-graph-export source={args.from_offline_graph_export}"
    elif args.demo:
        cb, cl = _demo_callbacks()
        bank = build_transition_bank(
            root_address="Root",
            candidate_builder=cb,
            coord_lookup=cl,
            max_depth=2,
            max_nodes=8,
        )
        notes = "demo graph: Root -> A (turn_right)"
    else:
        raise SystemExit("Specify --demo, --from-json, or --from-offline-graph-export.")

    bank_id = args.bank_id or f"bank_{uuid.uuid4().hex[:12]}"
    provenance = {
        "bank_id": bank_id,
        "created_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "generator": args.generator,
        "generator_version": "0.1.0",
        "schema_version": "transition_bank_file/v1",
        "notes": notes,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bank.to_json(args.out, provenance=provenance)

    payload = json.loads(args.out.read_text(encoding="utf-8"))
    _validate_bank_payload(payload)
    print(f"Wrote {args.out} (validated)")


if __name__ == "__main__":
    main()

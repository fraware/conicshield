from conicshield.bench.transition_bank import build_transition_bank


def test_transition_bank_builds_bfs_graph() -> None:
    graph = {
        "Root": [
            {
                "destination_address": "A",
                "destination_coords": [1.0, 0.0],
                "first_instruction": "Turn right",
                "action_class": "turn_right",
            }
        ],
        "A": [
            {
                "destination_address": "B",
                "destination_coords": [2.0, 0.0],
                "first_instruction": "Turn left",
                "action_class": "turn_left",
            }
        ],
        "B": [],
    }

    bank = build_transition_bank(
        root_address="Root",
        candidate_builder=lambda address: graph[address],
        coord_lookup=lambda address: {"Root": (0.0, 0.0), "A": (1.0, 0.0), "B": (2.0, 0.0)}[address],
        max_depth=2,
        max_nodes=10,
    )
    assert bank.root_address == "Root"
    assert set(bank.nodes) == {"Root", "A", "B"}
    assert bank.nodes["Root"].allowed_actions() == ["turn_right"]

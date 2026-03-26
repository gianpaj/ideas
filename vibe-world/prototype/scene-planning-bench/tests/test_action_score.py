from scene_planning_bench.registry import load_task, project_root
from scene_planning_bench.scoring import (
    aggregate_score,
    compute_action_type_score,
    compute_argument_match_score,
)


def test_action_and_argument_score_for_gold_response() -> None:
    task = load_task(
        project_root()
        / "tasks"
        / "v1_core"
        / "single_turn"
        / "add_pine_tree_left_of_cabin_001.json"
    )
    expected = task.gold_response
    actual = task.gold_response

    assert compute_action_type_score(expected, actual) == 1.0
    assert compute_argument_match_score(expected, actual) == 1.0
    assert (
        aggregate_score(
            task.scoring_profile,
            schema_validity=1.0,
            action_type=1.0,
            argument_match=1.0,
            spatial_match=1.0,
        )
        == 1.0
    )

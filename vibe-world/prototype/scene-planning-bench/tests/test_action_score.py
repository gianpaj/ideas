from scene_planning_bench.registry import load_task, project_root
from scene_planning_bench.scoring import (
    aggregate_score,
    compute_action_type_score,
    compute_argument_match_score,
    compute_spatial_match_score,
)
from scene_runtime.models import Relation


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
    assert compute_spatial_match_score(expected, actual) == 1.0
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


def test_spatial_score_allows_small_offset_drift() -> None:
    task = load_task(
        project_root()
        / "tasks"
        / "v1_core"
        / "single_turn"
        / "add_pine_tree_left_of_cabin_001.json"
    )
    actual = task.gold_response.model_copy(deep=True)
    assert actual.actions is not None
    assert actual.actions[0].transform is not None
    assert actual.actions[0].transform.position is not None
    actual.actions[0].transform.position.offset_meters = 3.4

    assert compute_spatial_match_score(task.gold_response, actual) == 1.0


def test_spatial_score_penalizes_relation_count_layout_and_constraints() -> None:
    task = load_task(
        project_root()
        / "tasks"
        / "v1_core"
        / "constraints"
        / "three_red_barrels_around_campfire_001.json"
    )
    actual = task.gold_response.model_copy(deep=True)
    assert actual.actions is not None
    action = actual.actions[0]
    assert action.transform is not None
    assert action.transform.position is not None
    assert action.attributes is not None
    assert action.constraints is not None

    action.transform.position.relation = Relation.LEFT_OF
    action.attributes.count = 2
    action.attributes.layout = "row"
    action.constraints.non_overlapping = False

    assert compute_spatial_match_score(task.gold_response, actual) == 0.5

from __future__ import annotations

from scene_runtime.models import ScenePlanningResponse


def compute_action_type_score(
    expected: ScenePlanningResponse, actual: ScenePlanningResponse | None
) -> float:
    if actual is None:
        return 0.0
    if expected.response_type != actual.response_type:
        return 0.0
    if expected.response_type.value != "scene_actions":
        return 1.0
    if not expected.actions or not actual.actions:
        return 0.0
    expected_types = [action.action_type for action in expected.actions]
    actual_types = [action.action_type for action in actual.actions]
    matches = sum(
        1 for expected_type, actual_type in zip(expected_types, actual_types)
        if expected_type == actual_type
    )
    return matches / max(len(expected_types), len(actual_types))


def compute_argument_match_score(
    expected: ScenePlanningResponse, actual: ScenePlanningResponse | None
) -> float:
    if actual is None:
        return 0.0
    if expected.response_type != actual.response_type:
        return 0.0
    if expected.response_type.value != "scene_actions":
        return 1.0
    if not expected.actions or not actual.actions:
        return 0.0

    total_checks = 0
    matched_checks = 0

    for expected_action, actual_action in zip(expected.actions, actual.actions):
        if expected_action.object_spec:
            total_checks += 1
            if actual_action.object_spec == expected_action.object_spec:
                matched_checks += 1
        if expected_action.attributes:
            total_checks += 1
            if actual_action.attributes == expected_action.attributes:
                matched_checks += 1
        if expected_action.transform and expected_action.transform.position:
            total_checks += 1
            if (
                actual_action.transform is not None
                and actual_action.transform.position == expected_action.transform.position
            ):
                matched_checks += 1

    if total_checks == 0:
        return 1.0
    return matched_checks / total_checks

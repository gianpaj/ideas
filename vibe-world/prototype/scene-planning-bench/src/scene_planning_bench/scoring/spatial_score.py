from __future__ import annotations

import math

from scene_runtime.models import Action, PositionSpec, ScenePlanningResponse

OFFSET_TOLERANCE_METERS = 0.5


def compute_spatial_match_score(
    expected: ScenePlanningResponse,
    actual: ScenePlanningResponse | None,
    *,
    offset_tolerance_meters: float = OFFSET_TOLERANCE_METERS,
) -> float:
    if actual is None:
        return 0.0
    if expected.response_type != actual.response_type:
        return 0.0
    if expected.response_type.value != "scene_actions":
        return 1.0
    if not expected.actions:
        return 1.0 if not actual.actions else 0.0

    total_checks = 0
    matched_checks = 0

    actual_actions = actual.actions or []
    for index, expected_action in enumerate(expected.actions):
        actual_action = actual_actions[index] if index < len(actual_actions) else None
        matched, total = _score_action_spatial_fields(
            expected_action,
            actual_action,
            offset_tolerance_meters=offset_tolerance_meters,
        )
        matched_checks += matched
        total_checks += total

    if total_checks == 0:
        return 1.0
    return matched_checks / total_checks


def _score_action_spatial_fields(
    expected: Action,
    actual: Action | None,
    *,
    offset_tolerance_meters: float,
) -> tuple[int, int]:
    checks: list[bool] = []

    expected_position = (
        expected.transform.position
        if expected.transform is not None and expected.transform.position is not None
        else None
    )
    actual_position = (
        actual.transform.position
        if actual is not None
        and actual.transform is not None
        and actual.transform.position is not None
        else None
    )
    checks.extend(
        _position_checks(
            expected_position,
            actual_position,
            offset_tolerance_meters=offset_tolerance_meters,
        )
    )

    if expected.attributes is not None:
        if expected.attributes.count is not None:
            checks.append(
                actual is not None
                and actual.attributes is not None
                and actual.attributes.count == expected.attributes.count
            )
        if expected.attributes.layout is not None:
            checks.append(
                actual is not None
                and actual.attributes is not None
                and actual.attributes.layout == expected.attributes.layout
            )

    if expected.constraints is not None:
        for field_name in ("grounded", "non_overlapping", "preserve_paths_clear"):
            expected_value = getattr(expected.constraints, field_name)
            if expected_value is None:
                continue
            checks.append(
                actual is not None
                and actual.constraints is not None
                and getattr(actual.constraints, field_name) == expected_value
            )

    return sum(1 for check in checks if check), len(checks)


def _position_checks(
    expected: PositionSpec | None,
    actual: PositionSpec | None,
    *,
    offset_tolerance_meters: float,
) -> list[bool]:
    if expected is None:
        return []

    checks: list[bool] = []
    if expected.relation is not None:
        checks.append(actual is not None and actual.relation == expected.relation)
    if expected.reference_object is not None:
        checks.append(
            actual is not None and actual.reference_object == expected.reference_object
        )
    if expected.offset_meters is not None:
        checks.append(
            actual is not None
            and actual.offset_meters is not None
            and abs(actual.offset_meters - expected.offset_meters)
            <= offset_tolerance_meters
        )
    if expected.absolute is not None:
        checks.append(
            actual is not None
            and actual.absolute is not None
            and len(actual.absolute) == len(expected.absolute)
            and _euclidean_distance(actual.absolute, expected.absolute)
            <= offset_tolerance_meters
        )
    return checks


def _euclidean_distance(left: list[float], right: list[float]) -> float:
    return math.sqrt(
        sum(
            (left_value - right_value) ** 2
            for left_value, right_value in zip(left, right)
        )
    )

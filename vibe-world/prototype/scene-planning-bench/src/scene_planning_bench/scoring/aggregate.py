from __future__ import annotations

from scene_planning_bench.types import ScoringProfile


def aggregate_score(
    profile: ScoringProfile,
    schema_validity: float,
    action_type: float,
    argument_match: float,
    spatial_match: float,
) -> float:
    if profile.hard_fail_on_schema_invalid and schema_validity == 0.0:
        return 0.0

    weights = profile.weights
    return round(
        schema_validity * weights.schema_validity
        + action_type * weights.action_type
        + argument_match * weights.argument_match
        + spatial_match * weights.spatial_match,
        6,
    )

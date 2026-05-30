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


def aggregate_artifact_score(
    profile: ScoringProfile,
    schema_validity: float,
    subscores: dict[str, float],
) -> float:
    """Aggregate non-scene_actions artifact scores via uniform averaging.

    Keeps the same schema-validity hard-fail semantics as aggregate_score so
    that schema-invalid outputs are treated consistently across artifact types.
    """

    if profile.hard_fail_on_schema_invalid and schema_validity == 0.0:
        return 0.0

    weights = profile.weights
    non_schema_total = (
        weights.action_type + weights.argument_match + weights.spatial_match
    )
    if not subscores or non_schema_total == 0:
        mean_subscore = 0.0
    else:
        mean_subscore = sum(subscores.values()) / len(subscores)

    return round(
        schema_validity * weights.schema_validity + mean_subscore * non_schema_total,
        6,
    )

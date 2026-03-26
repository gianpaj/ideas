from __future__ import annotations

from typing import Any

from scene_planning_bench.scoring import (
    aggregate_score,
    compute_action_type_score,
    compute_argument_match_score,
    compute_schema_score,
)
from scene_planning_bench.types import BenchmarkTask, RunResult
from scene_planning_bench.validation import parse_response_json, validate_with_schema


def _safe_ratio(numerator: float, denominator: float | None) -> float | None:
    if denominator is None or denominator <= 0:
        return None
    return round(numerator / denominator, 6)


def evaluate_output(
    task: BenchmarkTask,
    raw_output: str,
    adapter_name: str,
    response_schema: dict[str, Any],
    *,
    sample_id: str,
    prompt_index: int | None = None,
    prompt_text: str | None = None,
    prompt_bundle: list[dict[str, Any]] | None = None,
    inspect_log_location: str | None = None,
    total_time_seconds: float | None = None,
    working_time_seconds: float | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    total_cost_usd: float | None = None,
) -> RunResult:
    schema_valid = False
    response_type_match = False
    action_type_score = 0.0
    argument_match_score = 0.0
    spatial_match_score = 1.0
    parsed_payload = None
    errors: list[str] = []
    schema_errors: list[str] = []

    try:
        parsed = parse_response_json(raw_output)
        parsed_payload = parsed.model_dump(mode="json", exclude_none=True)
        schema_errors = validate_with_schema(parsed_payload, response_schema)
        schema_valid = not schema_errors
        response_type_match = parsed.response_type == task.gold_response.response_type
        action_type_score = compute_action_type_score(task.gold_response, parsed)
        argument_match_score = compute_argument_match_score(task.gold_response, parsed)
        errors.extend(schema_errors)
    except ValueError as exc:
        errors.append(str(exc))
        schema_errors = errors.copy()

    total_score = aggregate_score(
        task.scoring_profile,
        schema_validity=compute_schema_score(schema_errors),
        action_type=action_type_score,
        argument_match=argument_match_score,
        spatial_match=spatial_match_score,
    )

    return RunResult(
        sample_id=sample_id,
        task_id=task.task_id,
        paraphrase_group=task.metadata.get("paraphrase_group"),
        prompt_index=prompt_index,
        prompt_text=prompt_text,
        adapter_name=adapter_name,
        schema_valid=schema_valid,
        response_type_match=response_type_match,
        action_type_score=action_type_score,
        argument_match_score=argument_match_score,
        spatial_match_score=spatial_match_score,
        total_score=total_score,
        total_time_seconds=total_time_seconds,
        working_time_seconds=working_time_seconds,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        total_cost_usd=total_cost_usd,
        score_per_total_second=_safe_ratio(total_score, total_time_seconds),
        score_per_working_second=_safe_ratio(total_score, working_time_seconds),
        score_per_1k_tokens=(
            round(total_score / (total_tokens / 1000), 6)
            if total_tokens is not None and total_tokens > 0
            else None
        ),
        score_per_dollar=_safe_ratio(total_score, total_cost_usd),
        raw_output=raw_output,
        parsed_response=parsed_payload,
        prompt_bundle=prompt_bundle,
        inspect_log_location=inspect_log_location,
        errors=errors,
    )

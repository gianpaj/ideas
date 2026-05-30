from __future__ import annotations

from typing import Any

from scene_planning_bench.scoring import (
    aggregate_artifact_score,
    aggregate_score,
    compute_action_type_score,
    compute_argument_match_score,
    compute_builder_scores,
    compute_schema_score,
    compute_spatial_match_score,
    compute_voxel_scores,
)
from scene_planning_bench.types import BenchmarkTask, RunResult
from scene_runtime import (
    ArtifactType,
    BuilderSpec,
    PlanningRequest,
    SceneDefinition,
    ScenePlanningResponse,
    VoxelBuilderSpec,
    parse_artifact_json,
    process_planning_request,
    validate_with_schema,
)


def _safe_ratio(numerator: float, denominator: float | None) -> float | None:
    if denominator is None or denominator <= 0:
        return None
    return round(numerator / denominator, 6)


def _extract_system_prompt(prompt_bundle: list[dict[str, Any]] | None) -> str:
    if not prompt_bundle:
        return ""
    for message in prompt_bundle:
        if message.get("role") == "system":
            return str(message.get("content", ""))
    return ""


def evaluate_output(
    task: BenchmarkTask,
    scene: SceneDefinition,
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
    repeat_index: int | None = None,
    artifact_schema: dict[str, Any] | None = None,
) -> RunResult:
    if task.target_artifact is ArtifactType.SCENE_ACTIONS:
        return _evaluate_scene_actions(
            task,
            scene,
            raw_output,
            adapter_name,
            response_schema,
            sample_id=sample_id,
            prompt_index=prompt_index,
            prompt_text=prompt_text,
            prompt_bundle=prompt_bundle,
            inspect_log_location=inspect_log_location,
            total_time_seconds=total_time_seconds,
            working_time_seconds=working_time_seconds,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            total_cost_usd=total_cost_usd,
            repeat_index=repeat_index,
        )

    if artifact_schema is None:
        raise ValueError(
            f"artifact_schema is required for target_artifact={task.target_artifact.value}"
        )

    return _evaluate_artifact(
        task,
        raw_output,
        adapter_name,
        artifact_schema,
        sample_id=sample_id,
        prompt_index=prompt_index,
        prompt_text=prompt_text,
        prompt_bundle=prompt_bundle,
        inspect_log_location=inspect_log_location,
        total_time_seconds=total_time_seconds,
        working_time_seconds=working_time_seconds,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        total_cost_usd=total_cost_usd,
        repeat_index=repeat_index,
    )


def _evaluate_scene_actions(
    task: BenchmarkTask,
    scene: SceneDefinition,
    raw_output: str,
    adapter_name: str,
    response_schema: dict[str, Any],
    *,
    sample_id: str,
    prompt_index: int | None,
    prompt_text: str | None,
    prompt_bundle: list[dict[str, Any]] | None,
    inspect_log_location: str | None,
    total_time_seconds: float | None,
    working_time_seconds: float | None,
    input_tokens: int | None,
    output_tokens: int | None,
    total_tokens: int | None,
    total_cost_usd: float | None,
    repeat_index: int | None,
) -> RunResult:
    schema_valid = False
    response_type_match = False
    action_type_score = 0.0
    argument_match_score = 0.0
    spatial_match_score = 0.0
    parsed_payload = None
    normalized_plan = None
    render_drafts: list[dict[str, Any]] = []
    errors: list[str] = []
    schema_errors: list[str] = []
    diagnostics: list[str] = []

    planning_request = PlanningRequest(
        request_id=sample_id,
        scene=scene,
        user_prompt=prompt_text or task.prompts[0],
        system_prompt=_extract_system_prompt(prompt_bundle),
        response_schema=response_schema,
        metadata={
            "task_id": task.task_id,
            "prompt_index": prompt_index,
        },
    )

    outcome = process_planning_request(planning_request, raw_output)
    diagnostics = list(outcome.diagnostics)
    errors.extend(diagnostics)

    try:
        parsed = outcome.parsed_response
        if parsed is not None:
            parsed_payload = parsed.model_dump(mode="json", exclude_none=True)
        schema_errors = list(outcome.schema_errors)
        normalized_plan = (
            outcome.normalized_plan.model_dump(mode="json", exclude_none=True)
            if outcome.normalized_plan is not None
            else None
        )
        render_drafts = [
            draft.model_dump(mode="json", exclude_none=True)
            for draft in outcome.render_drafts
        ]
        schema_valid = parsed is not None and not schema_errors
        assert task.gold_response is not None
        response_type_match = (
            parsed is not None
            and parsed.response_type == task.gold_response.response_type
        )
        action_type_score = compute_action_type_score(task.gold_response, parsed)
        argument_match_score = compute_argument_match_score(task.gold_response, parsed)
        spatial_match_score = compute_spatial_match_score(task.gold_response, parsed)
        errors.extend(schema_errors)
    except Exception:
        if not schema_errors:
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
        repeat_index=repeat_index,
        prompt_text=prompt_text,
        adapter_name=adapter_name,
        target_artifact=task.target_artifact,
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
        parsed_artifact=parsed_payload,
        normalized_plan=normalized_plan,
        render_drafts=render_drafts,
        prompt_bundle=prompt_bundle,
        inspect_log_location=inspect_log_location,
        errors=errors,
        diagnostics=diagnostics,
    )


def _evaluate_artifact(
    task: BenchmarkTask,
    raw_output: str,
    adapter_name: str,
    artifact_schema: dict[str, Any],
    *,
    sample_id: str,
    prompt_index: int | None,
    prompt_text: str | None,
    prompt_bundle: list[dict[str, Any]] | None,
    inspect_log_location: str | None,
    total_time_seconds: float | None,
    working_time_seconds: float | None,
    input_tokens: int | None,
    output_tokens: int | None,
    total_tokens: int | None,
    total_cost_usd: float | None,
    repeat_index: int | None,
) -> RunResult:
    errors: list[str] = []
    schema_errors: list[str] = []
    diagnostics: list[str] = []
    parsed_payload: dict[str, Any] | None = None
    parsed: ScenePlanningResponse | BuilderSpec | VoxelBuilderSpec | None = None
    subscores: dict[str, float] = {}

    try:
        parsed = parse_artifact_json(raw_output, task.target_artifact)
        parsed_payload = parsed.model_dump(
            mode="json", exclude_none=True, by_alias=True
        )
    except ValueError as exc:
        errors.append(str(exc))
        diagnostics.append(f"parse_error: {exc}")

    if parsed_payload is not None:
        schema_errors = validate_with_schema(parsed_payload, artifact_schema)
        errors.extend(schema_errors)

    schema_valid = parsed is not None and not schema_errors

    if task.target_artifact is ArtifactType.BUILDER and isinstance(parsed, BuilderSpec):
        assert task.gold_builder is not None
        subscores = compute_builder_scores(task.gold_builder, parsed)
    elif task.target_artifact is ArtifactType.VOXEL_BUILDER and isinstance(
        parsed, VoxelBuilderSpec
    ):
        assert task.gold_voxel_builder is not None
        subscores = compute_voxel_scores(task.gold_voxel_builder, parsed)

    total_score = aggregate_artifact_score(
        task.scoring_profile,
        schema_validity=compute_schema_score(schema_errors) if parsed is not None else 0.0,
        subscores=subscores,
    )

    placement_match_score = subscores.get("placement_match", 0.0)
    operation_match_score = subscores.get(
        "operation_match", subscores.get("op_kind_match", 0.0)
    )
    non_placement = {
        key: value
        for key, value in subscores.items()
        if key not in {"placement_match", "operation_match", "op_kind_match"}
    }
    argument_match_score = (
        sum(non_placement.values()) / len(non_placement) if non_placement else 0.0
    )

    return RunResult(
        sample_id=sample_id,
        task_id=task.task_id,
        paraphrase_group=task.metadata.get("paraphrase_group"),
        prompt_index=prompt_index,
        repeat_index=repeat_index,
        prompt_text=prompt_text,
        adapter_name=adapter_name,
        target_artifact=task.target_artifact,
        schema_valid=schema_valid,
        response_type_match=schema_valid,
        action_type_score=operation_match_score,
        argument_match_score=argument_match_score,
        spatial_match_score=placement_match_score,
        artifact_subscores=subscores,
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
        parsed_response=None,
        parsed_artifact=parsed_payload,
        normalized_plan=None,
        render_drafts=[],
        prompt_bundle=prompt_bundle,
        inspect_log_location=inspect_log_location,
        errors=errors,
        diagnostics=diagnostics,
    )

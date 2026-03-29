from __future__ import annotations

from typing import Any

from scene_builder_bench.adapters.base import BuilderAdapter
from scene_builder_bench.validation.schema_validate import validate_with_schema
from scene_builder_runtime import (
    BuilderSpec,
    LoadedTask,
    RunResult,
    canonicalize_payload,
    hash_payload,
    validate_builder_spec_semantics,
)


def evaluate_loaded_task(
    loaded_task: LoadedTask,
    adapter: BuilderAdapter,
    builder_schema: dict[str, Any],
) -> RunResult:
    first_spec = adapter.build(
        loaded_task.normalized_plan,
        target_intent_id=loaded_task.task.target_intent_id,
        world_settings=loaded_task.task.world_settings,
        object_context=loaded_task.object_context,
    )
    second_spec = adapter.build(
        loaded_task.normalized_plan,
        target_intent_id=loaded_task.task.target_intent_id,
        world_settings=loaded_task.task.world_settings,
        object_context=loaded_task.object_context,
    )

    first_payload = first_spec.model_dump(mode="json", exclude_none=True)
    second_payload = second_spec.model_dump(mode="json", exclude_none=True)
    schema_errors = validate_with_schema(first_payload, builder_schema)
    semantic_errors = validate_builder_spec_semantics(
        first_spec,
        loaded_task.task.world_settings,
    )
    expectation_errors = validate_expected_checks(
        first_spec,
        loaded_task.task.expected_checks,
    )
    deterministic = canonicalize_payload(first_payload) == canonicalize_payload(second_payload)

    schema_valid = len(schema_errors) == 0
    semantic_valid = len(semantic_errors) == 0
    expected_checks_passed = len(expectation_errors) == 0
    total_score = round(
        (
            (1.0 if schema_valid else 0.0) * 0.25
            + (1.0 if semantic_valid else 0.0) * 0.25
            + (1.0 if deterministic else 0.0) * 0.25
            + (1.0 if expected_checks_passed else 0.0) * 0.25
        ),
        6,
    )

    diagnostics = list(first_spec.diagnostics)
    if loaded_task.object_context is not None:
        diagnostics.append(
            f"object_context_parts={len(loaded_task.object_context.parts)}"
        )

    return RunResult(
        task_id=loaded_task.task.task_id,
        operation=loaded_task.task.operation,
        schema_valid=schema_valid,
        semantic_valid=semantic_valid,
        deterministic=deterministic,
        expected_checks_passed=expected_checks_passed,
        schema_errors=schema_errors,
        semantic_errors=semantic_errors,
        expectation_errors=expectation_errors,
        diagnostics=diagnostics,
        canonical_hash=hash_payload(first_payload),
        total_score=total_score,
        builder_spec=first_payload,
    )


def validate_expected_checks(
    spec: BuilderSpec,
    expected_checks: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    category = expected_checks.get("category")
    if category is not None and spec.object_category != category:
        errors.append(
            f"expected category {category}, got {spec.object_category}"
        )

    instance_count = expected_checks.get("instance_count")
    if instance_count is not None and spec.complexity.instance_count != instance_count:
        errors.append(
            "expected instance_count "
            f"{instance_count}, got {spec.complexity.instance_count}"
        )

    part_count_min = expected_checks.get("part_count_min")
    if part_count_min is not None and spec.complexity.part_count < part_count_min:
        errors.append(
            f"expected at least {part_count_min} parts, got {spec.complexity.part_count}"
        )

    required_materials = expected_checks.get("required_materials", [])
    for material in required_materials:
        if material not in spec.materials:
            errors.append(f"required material missing: {material}")

    required_behaviors = expected_checks.get("required_behaviors", [])
    for behavior in required_behaviors:
        if behavior not in spec.behaviors:
            errors.append(f"required behavior missing: {behavior}")

    return errors

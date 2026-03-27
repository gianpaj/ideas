from __future__ import annotations

import json
from typing import Any

from scene_runtime.contracts import (
    IntentOperation,
    LayoutHint,
    NormalizedScenePlan,
    ObjectIntent,
    PlanKind,
    PlanningRequest,
)
from scene_runtime.models import Action, ActionType, ScenePlanningResponse

_CREATE_ACTIONS = {
    ActionType.ADD_OBJECT,
    ActionType.SPAWN_LAYOUT,
}
_REFINE_ACTIONS = {
    ActionType.MOVE_OBJECT,
    ActionType.REPLACE_OBJECT,
    ActionType.SET_COLOR,
    ActionType.SET_MATERIAL,
}
_SIZE_BY_CATEGORY = {
    "barrel": "small",
    "campfire": "small",
    "tree": "medium",
    "house": "large",
    "cabin": "large",
}
_PRIMITIVE_BY_CATEGORY = {
    "barrel": "column",
    "campfire": "blob",
    "house": "cube",
    "cabin": "cube",
    "tree": "column",
}


def normalize_response(
    request: PlanningRequest,
    response: ScenePlanningResponse,
) -> NormalizedScenePlan:
    if response.response_type.value == "clarification_request":
        return NormalizedScenePlan(
            request_id=request.request_id,
            plan_kind=PlanKind.CLARIFICATION,
            source_response_type=response.response_type,
            uncertainty=response.uncertainty,
            clarification=response.clarification,
        )

    if response.response_type.value == "refusal":
        return NormalizedScenePlan(
            request_id=request.request_id,
            plan_kind=PlanKind.REFUSAL,
            source_response_type=response.response_type,
            uncertainty=response.uncertainty,
            refusal=response.refusal,
        )

    diagnostics: list[str] = []
    intents: list[ObjectIntent] = []
    for index, action in enumerate(response.actions or []):
        normalized = _normalize_action(request, action, index, diagnostics)
        if normalized is not None:
            intents.append(normalized)

    intents = _merge_repeated_create_intents(intents, diagnostics)

    return NormalizedScenePlan(
        request_id=request.request_id,
        plan_kind=PlanKind.OBJECT_INTENT,
        source_response_type=response.response_type,
        uncertainty=response.uncertainty,
        intents=intents,
        diagnostics=diagnostics,
    )


def _normalize_action(
    request: PlanningRequest,
    action: Action,
    index: int,
    diagnostics: list[str],
) -> ObjectIntent | None:
    operation = _map_action_to_operation(action.action_type)
    if operation is None:
        diagnostics.append(
            f"unsupported action_type for normalization: {action.action_type.value}"
        )
        return None

    category = _resolve_category(action)
    if category == "unknown":
        diagnostics.append(
            f"action {index} missing object category; normalized as unknown"
        )

    layout_hint = _build_layout_hint(action)
    if action.action_type == ActionType.SPAWN_LAYOUT and layout_hint is None:
        diagnostics.append(
            f"action {index} is spawn_layout but no layout metadata was provided"
        )

    style_tags = [
        value
        for value in (
            action.object_spec.style if action.object_spec else None,
            action.object_spec.variant if action.object_spec else None,
        )
        if value
    ]

    parts = []
    if operation == IntentOperation.CREATE:
        parts.append(
            {
                "part_id": "main",
                "primitive": _PRIMITIVE_BY_CATEGORY.get(category, "cube"),
                "category": category,
                "variant": action.object_spec.variant if action.object_spec else None,
            }
        )

    return ObjectIntent(
        intent_id=f"{request.request_id}::intent_{index}",
        operation=operation,
        target_object_id=_resolve_target_object_id(request, action, operation),
        base_object_version=(
            request.base_object_version
            if operation in {IntentOperation.REFINE, IntentOperation.REMIX}
            else None
        ),
        category=category,
        size_tier=_SIZE_BY_CATEGORY.get(category),
        parts=parts,
        material_palette=_build_material_palette(action),
        behavior_presets=[],
        transform_hints=(
            action.transform.model_dump(mode="json", exclude_none=True)
            if action.transform is not None
            else None
        ),
        style_tags=style_tags,
        instance_count=_resolve_instance_count(layout_hint),
        layout_hint=layout_hint,
        source_actions=[action.action_type],
    )


def _map_action_to_operation(action_type: ActionType) -> IntentOperation | None:
    if action_type in _CREATE_ACTIONS:
        return IntentOperation.CREATE
    if action_type in _REFINE_ACTIONS:
        return IntentOperation.REFINE
    return None


def _resolve_category(action: Action) -> str:
    if action.object_spec is not None and action.object_spec.category:
        return action.object_spec.category
    return "unknown"


def _resolve_target_object_id(
    request: PlanningRequest,
    action: Action,
    operation: IntentOperation,
) -> str | None:
    if operation == IntentOperation.CREATE:
        return None
    return request.target_object_id or action.target


def _build_material_palette(action: Action) -> dict[str, Any] | None:
    if action.attributes is None:
        return None

    dominant = action.attributes.material or action.attributes.color
    palette: dict[str, Any] = {}
    if dominant is not None:
        palette["dominant"] = dominant
    if action.attributes.color is not None and action.attributes.material is not None:
        palette["color"] = action.attributes.color
    return palette or None


def _build_layout_hint(action: Action) -> LayoutHint | None:
    attributes = action.attributes
    if attributes is None:
        return None
    if attributes.layout is None and attributes.count in (None, 1):
        return None

    return LayoutHint(
        layout_type=attributes.layout,
        count=attributes.count,
        reference_object=(
            action.transform.position.reference_object
            if action.transform is not None and action.transform.position is not None
            else None
        ),
        relation=(
            action.transform.position.relation
            if action.transform is not None and action.transform.position is not None
            else None
        ),
        metadata={
            "offset_meters": (
                action.transform.position.offset_meters
                if action.transform is not None and action.transform.position is not None
                else None
            )
        },
    )


def _resolve_instance_count(layout_hint: LayoutHint | None) -> int:
    if layout_hint is None or layout_hint.count is None or layout_hint.count < 1:
        return 1
    return layout_hint.count


def _merge_repeated_create_intents(
    intents: list[ObjectIntent],
    diagnostics: list[str],
) -> list[ObjectIntent]:
    merged: list[ObjectIntent] = []
    grouped_indexes: dict[str, int] = {}

    for intent in intents:
        if not _is_mergeable_repeated_create(intent):
            merged.append(intent)
            continue

        key = _merge_key(intent)
        existing_index = grouped_indexes.get(key)
        if existing_index is None:
            grouped_indexes[key] = len(merged)
            merged.append(intent)
            continue

        existing = merged[existing_index]
        existing.instance_count += intent.instance_count
        existing.source_actions.extend(intent.source_actions)
        diagnostics.append(
            f"merged repeated create intent {intent.intent_id} into {existing.intent_id}"
        )

    return merged


def _is_mergeable_repeated_create(intent: ObjectIntent) -> bool:
    return (
        intent.operation == IntentOperation.CREATE
        and intent.target_object_id is None
        and intent.layout_hint is None
    )


def _merge_key(intent: ObjectIntent) -> str:
    payload = intent.model_dump(
        mode="json",
        exclude={
            "intent_id",
            "instance_count",
            "source_actions",
        },
        exclude_none=True,
    )
    return json.dumps(payload, sort_keys=True)

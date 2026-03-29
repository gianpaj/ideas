from __future__ import annotations

from scene_builder_runtime.contracts import (
    BuilderInstance,
    BuilderPart,
    BuilderSpec,
    ComplexitySpec,
    NormalizedScenePlan,
    ObjectIntent,
    PlacementSpec,
    WorldSettings,
)

SIZE_DIMENSIONS = {
    "tiny": [0.5, 0.5, 0.5],
    "small": [1.0, 1.0, 1.0],
    "medium": [2.0, 2.0, 2.0],
    "large": [4.0, 3.0, 4.0],
    "huge": [6.0, 6.0, 6.0],
}

CATEGORY_PRIMITIVES = {
    "barrel": "column",
    "tree": "column",
    "house": "cube",
    "cabin": "cube",
    "campfire": "blob",
}


def build_builder_spec(
    plan: NormalizedScenePlan,
    *,
    target_intent_id: str | None = None,
    world_settings: WorldSettings | None = None,
    object_context: BuilderSpec | None = None,
) -> BuilderSpec:
    if plan.plan_kind.value != "object_intent":
        raise ValueError(f"builder can only process object_intent plans, got {plan.plan_kind.value}")

    settings = world_settings or WorldSettings()
    intent = _select_intent(plan, target_intent_id)
    size_tier = intent.size_tier or "medium"
    parts = _build_parts(intent, size_tier, object_context)
    instances = _build_instances(intent)
    materials = _dedupe_preserve(
        [part.material for part in parts]
        + _material_palette_values(intent.material_palette)
    )
    behaviors = _dedupe_preserve(intent.behavior_presets)
    placement = _build_placement(intent)
    diagnostics = list(plan.diagnostics)
    if object_context is not None and intent.operation.value in {"refine", "remix"}:
        diagnostics.append(
            f"inherited {len(object_context.parts)} prior parts from object context"
        )

    spec = BuilderSpec(
        request_id=plan.request_id,
        intent_id=intent.intent_id,
        operation=intent.operation,
        target_object_id=intent.target_object_id,
        base_object_version=intent.base_object_version,
        object_category=intent.category,
        size_tier=size_tier,
        parts=parts,
        instances=instances,
        attachments=[],
        materials=materials,
        behaviors=behaviors,
        placement=placement,
        complexity=ComplexitySpec(
            part_count=len(parts),
            instance_count=len(instances),
            behavior_count=len(behaviors),
        ),
        diagnostics=diagnostics,
    )

    # Keep deterministic ordering before hashing/validation.
    spec.parts = sorted(spec.parts, key=lambda part: part.part_id)
    spec.instances = sorted(spec.instances, key=lambda instance: instance.instance_id)
    spec.materials = _dedupe_preserve(sorted(spec.materials))
    spec.behaviors = _dedupe_preserve(sorted(spec.behaviors))
    _enforce_caps(spec, settings)
    return spec


def _select_intent(plan: NormalizedScenePlan, target_intent_id: str | None) -> ObjectIntent:
    if not plan.intents:
        raise ValueError("normalized plan has no intents")
    if target_intent_id is None:
        return plan.intents[0]
    for intent in plan.intents:
        if intent.intent_id == target_intent_id:
            return intent
    raise ValueError(f"intent not found in plan: {target_intent_id}")


def _build_parts(
    intent: ObjectIntent,
    size_tier: str,
    object_context: BuilderSpec | None,
) -> list[BuilderPart]:
    if intent.parts:
        parts = [
            BuilderPart(
                part_id=str(raw_part.get("part_id", f"part_{index}")),
                primitive=str(
                    raw_part.get("primitive")
                    or CATEGORY_PRIMITIVES.get(intent.category, "cube")
                ),
                material=_resolve_primary_material(intent, raw_part.get("material")),
                dimensions=_dimensions_for_part(size_tier, intent.category, raw_part),
                modifiers=_part_modifiers(intent, raw_part),
            )
            for index, raw_part in enumerate(intent.parts)
        ]
    elif object_context is not None and intent.operation.value in {"refine", "remix"}:
        parts = [
            BuilderPart.model_validate(part.model_dump(mode="python"))
            for part in object_context.parts
        ]
    else:
        parts = [
            BuilderPart(
                part_id="main",
                primitive=CATEGORY_PRIMITIVES.get(intent.category, "cube"),
                material=_resolve_primary_material(intent, None),
                dimensions=SIZE_DIMENSIONS.get(size_tier, SIZE_DIMENSIONS["medium"]),
                modifiers=sorted(intent.style_tags),
            )
        ]

    if intent.category == "tree" and len(parts) == 1:
        parts.append(
            BuilderPart(
                part_id="canopy",
                primitive="blob",
                material=_resolve_secondary_material(intent, fallback="moss_stone"),
                dimensions=SIZE_DIMENSIONS.get(size_tier, SIZE_DIMENSIONS["medium"]),
                modifiers=sorted(_dedupe_preserve(intent.style_tags)),
            )
        )

    return parts


def _build_instances(intent: ObjectIntent) -> list[BuilderInstance]:
    count = intent.layout_hint.count if intent.layout_hint and intent.layout_hint.count else intent.instance_count
    count = max(count, 1)
    relation = _position_value(intent, "relation")
    reference_object = _position_value(intent, "reference_object")
    offset_meters = _position_value(intent, "offset_meters") or 0.0

    if intent.layout_hint and intent.layout_hint.layout_type == "triangle":
        offsets = [
            [offset_meters, 0.0, 0.0],
            [-offset_meters / 2, 0.0, offset_meters * 0.866],
            [-offset_meters / 2, 0.0, -offset_meters * 0.866],
        ]
    else:
        offsets = [[float(index) * 1.5, 0.0, 0.0] for index in range(count)]

    return [
        BuilderInstance(
            instance_id=f"instance_{index}",
            anchor_mode=str(_position_value(intent, "mode") or "absolute"),
            reference_object=reference_object,
            relation=relation,
            offset=offsets[index] if index < len(offsets) else [0.0, 0.0, 0.0],
        )
        for index in range(count)
    ]


def _build_placement(intent: ObjectIntent) -> PlacementSpec:
    return PlacementSpec(
        mode=str(_position_value(intent, "mode") or "absolute"),
        reference_object=_position_value(intent, "reference_object"),
        relation=_position_value(intent, "relation"),
        offset_meters=_position_value(intent, "offset_meters"),
    )


def _position_value(intent: ObjectIntent, key: str):
    position = intent.transform_hints.get("position") if intent.transform_hints else None
    if isinstance(position, dict):
        return position.get(key)
    return None


def _dimensions_for_part(size_tier: str, category: str, raw_part: dict) -> list[float]:
    if "dimensions" in raw_part and isinstance(raw_part["dimensions"], list):
        return [float(value) for value in raw_part["dimensions"][:3]]

    base = SIZE_DIMENSIONS.get(size_tier, SIZE_DIMENSIONS["medium"])
    if category == "barrel":
        return [1.0, 1.25, 1.0]
    if category == "tree":
        primitive = raw_part.get("primitive")
        if primitive == "column":
            return [1.0, 2.0, 1.0]
        return [2.0, 2.0, 2.0]
    return base


def _part_modifiers(intent: ObjectIntent, raw_part: dict) -> list[str]:
    modifiers = []
    raw_modifiers = raw_part.get("modifiers")
    if isinstance(raw_modifiers, list):
        modifiers.extend(str(value) for value in raw_modifiers)
    variant = raw_part.get("variant")
    if variant:
        modifiers.append(str(variant))
    modifiers.extend(intent.style_tags)
    return sorted(_dedupe_preserve(modifiers))


def _resolve_primary_material(intent: ObjectIntent, fallback) -> str:
    if isinstance(fallback, str):
        return fallback
    if intent.material_palette:
        dominant = intent.material_palette.get("dominant")
        if isinstance(dominant, str):
            return dominant
    return "wood"


def _resolve_secondary_material(intent: ObjectIntent, fallback: str) -> str:
    if intent.material_palette:
        accent = intent.material_palette.get("accent")
        if isinstance(accent, str):
            return accent
    return fallback


def _material_palette_values(material_palette: dict | None) -> list[str]:
    if not material_palette:
        return []
    return [str(value) for value in material_palette.values() if isinstance(value, str)]


def _dedupe_preserve(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _enforce_caps(spec: BuilderSpec, world_settings: WorldSettings) -> None:
    if len(spec.parts) > world_settings.max_part_count:
        spec.parts = spec.parts[: world_settings.max_part_count]
    if len(spec.behaviors) > world_settings.max_behavior_count:
        spec.behaviors = spec.behaviors[: world_settings.max_behavior_count]
    if len(spec.instances) > world_settings.max_instances:
        spec.instances = spec.instances[: world_settings.max_instances]
    spec.complexity = ComplexitySpec(
        part_count=len(spec.parts),
        instance_count=len(spec.instances),
        behavior_count=len(spec.behaviors),
    )

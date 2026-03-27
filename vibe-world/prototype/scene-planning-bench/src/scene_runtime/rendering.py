from __future__ import annotations

from scene_runtime.contracts import (
    BoundsHint,
    NormalizedScenePlan,
    PlanKind,
    PrimitiveNode,
    RenderDraftSpec,
    WorldAnchor,
)
from scene_runtime.models import Relation

_BOUNDS_BY_SIZE_TIER = {
    "tiny": [0.5, 0.5, 0.5],
    "small": [1.0, 1.0, 1.0],
    "medium": [2.0, 2.0, 2.0],
    "large": [4.0, 3.0, 4.0],
    "huge": [6.0, 6.0, 6.0],
}


def build_render_drafts(plan: NormalizedScenePlan) -> list[RenderDraftSpec]:
    if plan.plan_kind != PlanKind.OBJECT_INTENT:
        return []

    drafts: list[RenderDraftSpec] = []
    for intent in plan.intents:
        warnings: list[str] = []
        anchor = _build_world_anchor(intent.transform_hints, warnings)
        primitive_nodes = _build_primitive_nodes(intent, warnings)
        if not primitive_nodes:
            warnings.append("intent did not produce any primitive nodes")
        drafts.append(
            RenderDraftSpec(
                draft_id=f"{intent.intent_id}::draft",
                request_id=plan.request_id,
                intent_id=intent.intent_id,
                display_name=_display_name(intent.category, len(primitive_nodes)),
                primitive_nodes=primitive_nodes,
                world_anchor=anchor,
                bounds_hint=BoundsHint(size=_BOUNDS_BY_SIZE_TIER.get(intent.size_tier)),
                preview_materials=_preview_materials(intent.material_palette),
                animation_presets=intent.behavior_presets,
                warnings=warnings,
            )
        )
    return drafts


def _build_world_anchor(
    transform_hints: dict | None,
    warnings: list[str],
) -> WorldAnchor:
    if transform_hints is None or "position" not in transform_hints:
        warnings.append("missing position transform hints; defaulting to origin anchor")
        return WorldAnchor(mode="absolute", absolute=[0.0, 0.0, 0.0])

    position = transform_hints["position"]
    relation = position.get("relation")
    return WorldAnchor(
        mode=position.get("mode", "absolute"),
        reference_object=position.get("reference_object"),
        relation=Relation(relation) if relation else None,
        offset_meters=position.get("offset_meters"),
        absolute=position.get("absolute"),
    )


def _build_primitive_nodes(intent, warnings: list[str]) -> list[PrimitiveNode]:
    count = intent.instance_count or 1
    layout_type = None
    if intent.layout_hint is not None:
        count = max(count, intent.layout_hint.count or 1)
        layout_type = intent.layout_hint.layout_type

    primitive = "cube"
    if intent.parts:
        primitive = intent.parts[0].get("primitive", "cube")

    material = None
    if intent.material_palette is not None:
        material = intent.material_palette.get("dominant")

    if count > 1 and layout_type is None:
        warnings.append(
            "grouped instances have no explicit layout; preview uses indexed placeholders"
        )

    nodes: list[PrimitiveNode] = []
    for index in range(count):
        transform = {"instance_index": index}
        if layout_type == "triangle":
            transform["polar_angle_degrees"] = index * 120
        nodes.append(
            PrimitiveNode(
                primitive=primitive,
                transform=transform,
                material=material,
                metadata={"category": intent.category},
            )
        )
    return nodes


def _preview_materials(material_palette: dict | None) -> list[str]:
    if material_palette is None:
        return []
    return [str(value) for value in material_palette.values() if value is not None]


def _display_name(category: str, node_count: int) -> str:
    if node_count <= 1:
        return category.replace("_", " ").title()
    return f"{node_count} {category.replace('_', ' ').title()}s"

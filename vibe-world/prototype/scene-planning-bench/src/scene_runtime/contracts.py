from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from scene_runtime.models import (
    ActionType,
    Clarification,
    Refusal,
    Relation,
    ResponseType,
    SceneDefinition,
    ScenePlanningResponse,
    Uncertainty,
)


class PlanKind(str, Enum):
    OBJECT_INTENT = "object_intent"
    CLARIFICATION = "clarification"
    REFUSAL = "refusal"


class IntentOperation(str, Enum):
    CREATE = "create"
    REFINE = "refine"
    REMIX = "remix"


class PlanningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    scene: SceneDefinition
    user_prompt: str
    system_prompt: str
    target_world_id: str | None = None
    target_object_id: str | None = None
    base_object_version: int | None = None
    response_schema: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class LayoutHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout_type: str | None = None
    count: int | None = None
    reference_object: str | None = None
    relation: Relation | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ObjectIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str
    operation: IntentOperation
    target_object_id: str | None = None
    base_object_version: int | None = None
    category: str
    size_tier: str | None = None
    parts: list[dict[str, Any]] = Field(default_factory=list)
    material_palette: dict[str, Any] | None = None
    behavior_presets: list[str] = Field(default_factory=list)
    transform_hints: dict[str, Any] | None = None
    style_tags: list[str] = Field(default_factory=list)
    layout_hint: LayoutHint | None = None
    source_actions: list[ActionType] = Field(default_factory=list)


class NormalizedScenePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_version: str = "0.1"
    request_id: str
    plan_kind: PlanKind
    source_response_type: ResponseType
    uncertainty: Uncertainty
    intents: list[ObjectIntent] = Field(default_factory=list)
    clarification: Clarification | None = None
    refusal: Refusal | None = None
    diagnostics: list[str] = Field(default_factory=list)


class PrimitiveNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primitive: str
    transform: dict[str, Any] = Field(default_factory=dict)
    material: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorldAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str
    reference_object: str | None = None
    relation: Relation | None = None
    offset_meters: float | None = None
    absolute: list[float] | None = None


class BoundsHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    size: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RenderDraftSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: str
    request_id: str
    intent_id: str
    display_name: str
    primitive_nodes: list[PrimitiveNode] = Field(default_factory=list)
    world_anchor: WorldAnchor
    bounds_hint: BoundsHint | None = None
    preview_materials: list[str] = Field(default_factory=list)
    animation_presets: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PlanningOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    raw_output: str
    parsed_response: ScenePlanningResponse | None = None
    schema_errors: list[str] = Field(default_factory=list)
    normalized_plan: NormalizedScenePlan | None = None
    render_drafts: list[RenderDraftSpec] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)

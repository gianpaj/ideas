from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlanKind(str, Enum):
    OBJECT_INTENT = "object_intent"
    CLARIFICATION = "clarification"
    REFUSAL = "refusal"


class IntentOperation(str, Enum):
    CREATE = "create"
    REFINE = "refine"
    REMIX = "remix"


class LayoutHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout_type: str | None = None
    count: int | None = None
    reference_object: str | None = None
    relation: str | None = None
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
    instance_count: int = 1
    layout_hint: LayoutHint | None = None
    source_actions: list[str] = Field(default_factory=list)


class Uncertainty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    has_ambiguity: bool
    fields: list[str] = Field(default_factory=list)


class NormalizedScenePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_version: str = "0.1"
    request_id: str
    plan_kind: PlanKind
    source_response_type: str
    uncertainty: Uncertainty
    intents: list[ObjectIntent] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class BuilderPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_id: str
    primitive: str
    material: str
    dimensions: list[float]
    modifiers: list[str] = Field(default_factory=list)


class BuilderInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance_id: str
    anchor_mode: str
    reference_object: str | None = None
    relation: str | None = None
    offset: list[float]


class PlacementSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str
    reference_object: str | None = None
    relation: str | None = None
    offset_meters: float | None = None


class ComplexitySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_count: int
    instance_count: int
    behavior_count: int


class BuilderSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    builder_version: str = "0.1"
    request_id: str
    intent_id: str
    operation: IntentOperation
    target_object_id: str | None = None
    base_object_version: int | None = None
    object_category: str
    size_tier: str
    parts: list[BuilderPart] = Field(default_factory=list)
    instances: list[BuilderInstance] = Field(default_factory=list)
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    behaviors: list[str] = Field(default_factory=list)
    placement: PlacementSpec
    complexity: ComplexitySpec
    diagnostics: list[str] = Field(default_factory=list)


class WorldSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destructive_edits_enabled: bool = False
    max_part_count: int = 16
    max_behavior_count: int = 2
    max_instances: int = 8


class BuilderTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    operation: IntentOperation
    input_plan_path: str
    target_intent_id: str | None = None
    object_context_path: str | None = None
    world_settings: WorldSettings = Field(default_factory=WorldSettings)
    expected_checks: dict[str, Any] = Field(default_factory=dict)


class SuiteDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    builder_schema_path: str = "schemas/builder_spec.schema.json"
    task_schema_path: str = "schemas/builder_task.schema.json"


class SuiteConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suite_id: str
    description: str | None = None
    defaults: SuiteDefaults = Field(default_factory=SuiteDefaults)
    task_paths: list[str] = Field(default_factory=list)
    task_roots: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_task_sources(self) -> "SuiteConfig":
        if not self.task_paths and not self.task_roots:
            raise ValueError("suite config must provide task_paths or task_roots")
        return self


class LoadedTask(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    task_path: str
    task: BuilderTask
    normalized_plan: NormalizedScenePlan
    object_context: BuilderSpec | None = None


class RunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    operation: IntentOperation
    schema_valid: bool
    semantic_valid: bool
    deterministic: bool
    expected_checks_passed: bool
    schema_errors: list[str] = Field(default_factory=list)
    semantic_errors: list[str] = Field(default_factory=list)
    expectation_errors: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    canonical_hash: str | None = None
    total_score: float
    builder_spec: dict[str, Any] | None = None

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResponseType(str, Enum):
    SCENE_ACTIONS = "scene_actions"
    SCENE_PATCH = "scene_patch"
    CLARIFICATION_REQUEST = "clarification_request"
    REFUSAL = "refusal"


class PositionMode(str, Enum):
    ABSOLUTE = "absolute"
    RELATIVE = "relative"


class Relation(str, Enum):
    LEFT_OF = "left_of"
    RIGHT_OF = "right_of"
    BEHIND = "behind"
    IN_FRONT_OF = "in_front_of"
    AROUND = "around"


class ActionType(str, Enum):
    ADD_OBJECT = "add_object"
    REMOVE_OBJECT = "remove_object"
    MOVE_OBJECT = "move_object"
    ROTATE_OBJECT = "rotate_object"
    SCALE_OBJECT = "scale_object"
    SET_MATERIAL = "set_material"
    SET_COLOR = "set_color"
    DUPLICATE_OBJECT = "duplicate_object"
    GROUP_OBJECTS = "group_objects"
    UNGROUP_OBJECTS = "ungroup_objects"
    REPLACE_OBJECT = "replace_object"
    SET_RELATION = "set_relation"
    CLEAR_AREA = "clear_area"
    SPAWN_LAYOUT = "spawn_layout"
    ANNOTATE_CONSTRAINT = "annotate_constraint"


class ObjectSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    asset_id: str | None = None
    style: str | None = None
    variant: str | None = None


class PositionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: PositionMode
    reference_object: str | None = None
    relation: Relation | None = None
    offset_meters: float | None = None
    absolute: list[float] | None = None


class TransformSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position: PositionSpec | None = None
    rotation: list[float] | None = None
    scale: list[float] | None = None


class AttributesSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    color: str | None = None
    material: str | None = None
    count: int | None = None
    layout: str | None = None


class ConstraintSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grounded: bool | None = None
    non_overlapping: bool | None = None
    preserve_paths_clear: bool | None = None


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: ActionType
    target: str | None = None
    object_spec: ObjectSpec | None = None
    transform: TransformSpec | None = None
    attributes: AttributesSpec | None = None
    constraints: ConstraintSpec | None = None
    references: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class Clarification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    missing_fields: list[str] = Field(default_factory=list)


class Refusal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str
    safe_alternative: str | None = None


class Uncertainty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    has_ambiguity: bool
    fields: list[str] = Field(default_factory=list)


class ScenePlanningResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    response_type: ResponseType
    actions: list[Action] | None = None
    patch: dict[str, Any] | None = None
    clarification: Clarification | None = None
    refusal: Refusal | None = None
    notes: str | None = None
    uncertainty: Uncertainty

    @model_validator(mode="after")
    def validate_payload(self) -> "ScenePlanningResponse":
        if self.response_type == ResponseType.SCENE_ACTIONS and self.actions is None:
            raise ValueError("scene_actions responses must include actions")
        if self.response_type == ResponseType.SCENE_PATCH and self.patch is None:
            raise ValueError("scene_patch responses must include patch")
        if (
            self.response_type == ResponseType.CLARIFICATION_REQUEST
            and self.clarification is None
        ):
            raise ValueError(
                "clarification_request responses must include clarification"
            )
        if self.response_type == ResponseType.REFUSAL and self.refusal is None:
            raise ValueError("refusal responses must include refusal")
        return self


class SceneObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    category: str
    position: list[float]
    tags: list[str] = Field(default_factory=list)


class AllowedCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categories: list[str]
    action_types: list[ActionType]


class SceneDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_id: str
    objects: list[SceneObject]
    allowed_catalog: AllowedCatalog


class ScoringWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_validity: float = 0.25
    action_type: float = 0.25
    argument_match: float = 0.30
    spatial_match: float = 0.20


class ScoringProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    hard_fail_on_schema_invalid: bool = True


class BenchmarkTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    category: str
    difficulty: str
    scene_id: str
    prompts: list[str]
    allowed_response_types: list[ResponseType]
    gold_response: ScenePlanningResponse
    scoring_profile: ScoringProfile
    metadata: dict[str, Any] = Field(default_factory=dict)


class SuiteDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system_prompt: str = (
        "You are a scene-planning assistant.\n"
        "Output JSON only.\n"
        "Use schema_version 1.0.\n"
        "Do not invent unsupported categories or actions.\n"
        "If the request is ambiguous, return a clarification_request.\n"
        "If the request is impossible or unsupported, return a refusal."
    )
    response_schema_path: str = "schemas/response.schema.json"
    scene_schema_path: str = "schemas/scene.schema.json"
    task_schema_path: str = "schemas/task.schema.json"


class SuiteConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None = None
    defaults: SuiteDefaults = Field(default_factory=SuiteDefaults)
    suite_id: str
    task_paths: list[str]


class LoadedTask(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path
    task: BenchmarkTask
    scene: SceneDefinition


class RunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_id: str
    task_id: str
    prompt_index: int | None = None
    prompt_text: str | None = None
    adapter_name: str
    schema_valid: bool
    response_type_match: bool
    action_type_score: float
    argument_match_score: float
    spatial_match_score: float
    total_score: float
    raw_output: str
    parsed_response: dict[str, Any] | None = None
    prompt_bundle: list[dict[str, Any]] | None = None
    inspect_log_location: str | None = None
    errors: list[str] = Field(default_factory=list)

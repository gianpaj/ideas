from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scene_runtime.models import (
    Action,
    ActionType,
    AllowedCatalog,
    AttributesSpec,
    Clarification,
    ConstraintSpec,
    ObjectSpec,
    PositionMode,
    PositionSpec,
    Refusal,
    Relation,
    ResponseType,
    SceneDefinition,
    SceneObject,
    ScenePlanningResponse,
    TransformSpec,
    Uncertainty,
)


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
    task_paths: list[str] = Field(default_factory=list)
    task_roots: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_task_sources(self) -> "SuiteConfig":
        if not self.task_paths and not self.task_roots:
            raise ValueError("suite config must provide task_paths or task_roots")
        return self


class MatrixModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    enabled: bool = True
    model_args_file: str | None = None
    label: str | None = None
    base_url: str | None = None
    repeats: int | None = Field(default=None, ge=1)


class RunMatrixConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matrix_id: str
    suite: str = "configs/suites/v1_core.yaml"
    models: list[MatrixModelConfig]


class LoadedTask(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path
    task: BenchmarkTask
    scene: SceneDefinition


class RunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_id: str
    task_id: str
    paraphrase_group: str | None = None
    prompt_index: int | None = None
    repeat_index: int | None = None
    prompt_text: str | None = None
    adapter_name: str
    schema_valid: bool
    response_type_match: bool
    action_type_score: float
    argument_match_score: float
    spatial_match_score: float
    total_score: float
    total_time_seconds: float | None = None
    working_time_seconds: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    total_cost_usd: float | None = None
    score_per_total_second: float | None = None
    score_per_working_second: float | None = None
    score_per_1k_tokens: float | None = None
    score_per_dollar: float | None = None
    raw_output: str
    parsed_response: dict[str, Any] | None = None
    normalized_plan: dict[str, Any] | None = None
    render_drafts: list[dict[str, Any]] = Field(default_factory=list)
    prompt_bundle: list[dict[str, Any]] | None = None
    inspect_log_location: str | None = None
    errors: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def populate_efficiency_metrics(self) -> "RunResult":
        if self.score_per_total_second is None and self.total_time_seconds not in (None, 0):
            self.score_per_total_second = round(
                self.total_score / self.total_time_seconds,
                6,
            )
        if (
            self.score_per_working_second is None
            and self.working_time_seconds not in (None, 0)
        ):
            self.score_per_working_second = round(
                self.total_score / self.working_time_seconds,
                6,
            )
        if self.score_per_1k_tokens is None and self.total_tokens not in (None, 0):
            self.score_per_1k_tokens = round(
                self.total_score / (self.total_tokens / 1000),
                6,
            )
        if self.score_per_dollar is None and self.total_cost_usd not in (None, 0):
            self.score_per_dollar = round(
                self.total_score / self.total_cost_usd,
                6,
            )
        return self

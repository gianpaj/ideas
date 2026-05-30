from __future__ import annotations

import json
import re
from json import JSONDecodeError
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from scene_runtime.artifacts import ArtifactType, BuilderSpec, VoxelBuilderSpec
from scene_runtime.models import ScenePlanningResponse


ModelT = TypeVar("ModelT", bound=BaseModel)


def _strip_code_fence(raw_output: str) -> str:
    stripped = raw_output.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw_output


def _decode_json(raw_output: str) -> Any:
    candidate = _strip_code_fence(raw_output)
    try:
        return json.loads(candidate)
    except JSONDecodeError as exc:
        raise ValueError(f"invalid JSON output: {exc}") from exc


def parse_response_json(raw_output: str) -> ScenePlanningResponse:
    data = _decode_json(raw_output)
    try:
        return ScenePlanningResponse.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid response payload: {exc}") from exc


def _parse_model(raw_output: str, model_cls: type[ModelT]) -> ModelT:
    data = _decode_json(raw_output)
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid {model_cls.__name__} payload: {exc}") from exc


def parse_artifact_json(
    raw_output: str, artifact_type: ArtifactType
) -> ScenePlanningResponse | BuilderSpec | VoxelBuilderSpec:
    if artifact_type is ArtifactType.SCENE_ACTIONS:
        return parse_response_json(raw_output)
    if artifact_type is ArtifactType.BUILDER:
        return _parse_model(raw_output, BuilderSpec)
    if artifact_type is ArtifactType.VOXEL_BUILDER:
        return _parse_model(raw_output, VoxelBuilderSpec)
    raise ValueError(f"unsupported artifact type: {artifact_type}")

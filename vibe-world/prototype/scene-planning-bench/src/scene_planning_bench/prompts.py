from __future__ import annotations

from typing import Any

from scene_planning_bench.types import BenchmarkTask, SceneDefinition
from scene_runtime import ArtifactType
from scene_runtime.contracts import PlanningRequest
from scene_runtime.prompting import (
    build_artifact_prompt_bundle,
    build_prompt_bundle as build_runtime_prompt_bundle,
)


def build_prompt_bundle(
    system_prompt: str,
    scene: SceneDefinition,
    task: BenchmarkTask,
    response_schema: dict[str, Any],
    prompt_text: str,
) -> list[dict[str, str]]:
    metadata: dict[str, Any] = {
        "task_id": task.task_id,
        "category": task.category,
        "difficulty": task.difficulty,
        "target_artifact": task.target_artifact.value,
    }

    if task.target_artifact is ArtifactType.SCENE_ACTIONS:
        metadata["allowed_response_types"] = [
            response_type.value for response_type in task.allowed_response_types
        ]
        request = PlanningRequest(
            request_id=f"{task.task_id}::prompt_bundle",
            scene=scene,
            user_prompt=prompt_text,
            system_prompt=system_prompt,
            response_schema=response_schema,
            metadata=metadata,
        )
        return build_runtime_prompt_bundle(request, metadata_label="Task metadata JSON")

    if task.target_artifact is ArtifactType.VOXEL_CORE:
        # Mirror the production object-generation call exactly: only the system
        # prompt (the suite's = the shipped voxel-builder prompt) plus the player
        # text. No scene context or JSON-schema injection, so optimizing here
        # tunes the same input distribution the game actually sends to Gemini.
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Player prompt: {prompt_text}"},
        ]

    return build_artifact_prompt_bundle(
        artifact_type=task.target_artifact,
        scene=scene,
        user_prompt=prompt_text,
        artifact_schema=response_schema,
        system_prompt=system_prompt,
        metadata=metadata,
    )

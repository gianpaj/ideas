from __future__ import annotations

from typing import Any

from scene_planning_bench.types import BenchmarkTask, SceneDefinition
from scene_runtime.contracts import PlanningRequest
from scene_runtime.prompting import build_prompt_bundle as build_runtime_prompt_bundle


def build_prompt_bundle(
    system_prompt: str,
    scene: SceneDefinition,
    task: BenchmarkTask,
    response_schema: dict[str, Any],
    prompt_text: str,
) -> list[dict[str, str]]:
    request = PlanningRequest(
        request_id=f"{task.task_id}::prompt_bundle",
        scene=scene,
        user_prompt=prompt_text,
        system_prompt=system_prompt,
        response_schema=response_schema,
        metadata={
            "task_id": task.task_id,
            "category": task.category,
            "difficulty": task.difficulty,
            "allowed_response_types": [
                response_type.value for response_type in task.allowed_response_types
            ],
        },
    )
    return build_runtime_prompt_bundle(request, metadata_label="Task metadata JSON")

from __future__ import annotations

import json
from typing import Any

from scene_planning_bench.types import BenchmarkTask, SceneDefinition


def build_prompt_bundle(
    system_prompt: str,
    scene: SceneDefinition,
    task: BenchmarkTask,
    response_schema: dict[str, Any],
    prompt_text: str,
) -> list[dict[str, str]]:
    scene_payload = scene.model_dump(mode="json", exclude_none=True)
    task_payload = {
        "task_id": task.task_id,
        "category": task.category,
        "difficulty": task.difficulty,
        "allowed_response_types": [
            response_type.value for response_type in task.allowed_response_types
        ],
    }
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "system",
            "content": (
                "Scene context JSON:\n"
                + json.dumps(scene_payload, indent=2)
                + "\n\n"
                + "Task metadata JSON:\n"
                + json.dumps(task_payload, indent=2)
                + "\n\n"
                + "Response schema JSON Schema:\n"
                + json.dumps(response_schema, indent=2)
                + "\n\n"
                + "Return only a JSON object that conforms to the schema."
            ),
        },
        {"role": "user", "content": prompt_text},
    ]

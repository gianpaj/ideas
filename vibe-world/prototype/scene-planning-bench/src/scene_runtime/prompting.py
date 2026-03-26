from __future__ import annotations

import json

from scene_runtime.contracts import PlanningRequest


def build_prompt_bundle(
    request: PlanningRequest,
    *,
    metadata_label: str = "Request metadata JSON",
) -> list[dict[str, str]]:
    scene_payload = request.scene.model_dump(mode="json", exclude_none=True)
    parts = [
        "Scene context JSON:\n" + json.dumps(scene_payload, indent=2),
    ]

    if request.metadata:
        parts.append(
            metadata_label + ":\n" + json.dumps(request.metadata, indent=2)
        )

    parts.append(
        "Response schema JSON Schema:\n"
        + json.dumps(request.response_schema, indent=2)
    )
    parts.append("Return only a JSON object that conforms to the schema.")

    return [
        {"role": "system", "content": request.system_prompt},
        {"role": "system", "content": "\n\n".join(parts)},
        {"role": "user", "content": request.user_prompt},
    ]

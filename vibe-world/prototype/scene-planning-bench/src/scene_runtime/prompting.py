from __future__ import annotations

import json
from typing import Any

from scene_runtime.artifacts import ArtifactType
from scene_runtime.contracts import PlanningRequest
from scene_runtime.models import SceneDefinition


ARTIFACT_SYSTEM_PROMPTS: dict[ArtifactType, str] = {
    ArtifactType.SCENE_ACTIONS: (
        "You are a scene-planning assistant.\n"
        "Output JSON only.\n"
        "Use schema_version 1.0.\n"
        "Do not invent unsupported categories or actions.\n"
        "If the request is ambiguous, return a clarification_request.\n"
        "If the request is impossible or unsupported, return a refusal."
    ),
    ArtifactType.BUILDER: (
        "You are an object-builder assistant.\n"
        "Output JSON only that conforms to the BuilderSpec schema.\n"
        "Use builder_version 0.1.\n"
        "Describe the target object as a list of named parts with primitives, materials, and dimensions.\n"
        "Include at least one instance with an anchor_mode and offset.\n"
        "Populate complexity counts to reflect parts, instances, and behaviors."
    ),
    ArtifactType.VOXEL_BUILDER: (
        "You are a voxel-builder assistant.\n"
        "Output JSON only that conforms to the VoxelBuilderSpec schema.\n"
        "Use spec_version 0.1.\n"
        "Compose the object from voxel operations (add_box, add_sphere, add_line, paint_region, rotate_region, clone_region).\n"
        "Declare grid.unit_meters, up_axis 'y', and rotation_step_degrees 90.\n"
        "Every op_id must be unique and reference a declared material_id."
    ),
}


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


def build_artifact_prompt_bundle(
    *,
    artifact_type: ArtifactType,
    scene: SceneDefinition,
    user_prompt: str,
    artifact_schema: dict[str, Any],
    system_prompt: str | None = None,
    metadata: dict[str, Any] | None = None,
    metadata_label: str = "Task metadata JSON",
) -> list[dict[str, str]]:
    effective_system_prompt = system_prompt or ARTIFACT_SYSTEM_PROMPTS[artifact_type]
    scene_payload = scene.model_dump(mode="json", exclude_none=True)
    parts = [
        f"Target artifact: {artifact_type.value}",
        "Scene context JSON:\n" + json.dumps(scene_payload, indent=2),
    ]

    if metadata:
        parts.append(metadata_label + ":\n" + json.dumps(metadata, indent=2))

    parts.append(
        "Artifact schema JSON Schema:\n" + json.dumps(artifact_schema, indent=2)
    )
    parts.append("Return only a JSON object that conforms to the schema.")

    return [
        {"role": "system", "content": effective_system_prompt},
        {"role": "system", "content": "\n\n".join(parts)},
        {"role": "user", "content": user_prompt},
    ]

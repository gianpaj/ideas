from __future__ import annotations

from scene_builder_runtime.contracts import BuilderSpec, WorldSettings

ALLOWED_PRIMITIVES = {
    "cube",
    "slab",
    "column",
    "stair",
    "wedge",
    "arch",
    "platform",
    "blob",
}
ALLOWED_MATERIALS = {
    "stone",
    "moss_stone",
    "neon",
    "glass_block",
    "jelly",
    "cloud",
    "wood",
    "lava_light",
    "void",
    "red",
}
ALLOWED_BEHAVIORS = {
    "glow",
    "bob",
    "pulse",
    "spin",
    "bounce",
    "open_close",
    "hover",
}


def validate_builder_spec_semantics(
    spec: BuilderSpec,
    world_settings: WorldSettings,
) -> list[str]:
    errors: list[str] = []

    for part in spec.parts:
        if part.primitive not in ALLOWED_PRIMITIVES:
            errors.append(f"unsupported primitive: {part.primitive}")
        if part.material not in ALLOWED_MATERIALS:
            errors.append(f"unsupported material on part {part.part_id}: {part.material}")
        if len(part.dimensions) != 3:
            errors.append(f"part {part.part_id} must provide exactly three dimensions")

    for material in spec.materials:
        if material not in ALLOWED_MATERIALS:
            errors.append(f"unsupported material in materials list: {material}")

    for behavior in spec.behaviors:
        if behavior not in ALLOWED_BEHAVIORS:
            errors.append(f"unsupported behavior: {behavior}")

    if spec.complexity.part_count > world_settings.max_part_count:
        errors.append(
            f"part count {spec.complexity.part_count} exceeds cap {world_settings.max_part_count}"
        )
    if spec.complexity.behavior_count > world_settings.max_behavior_count:
        errors.append(
            "behavior count "
            f"{spec.complexity.behavior_count} exceeds cap {world_settings.max_behavior_count}"
        )
    if spec.complexity.instance_count > world_settings.max_instances:
        errors.append(
            f"instance count {spec.complexity.instance_count} exceeds cap {world_settings.max_instances}"
        )

    return errors

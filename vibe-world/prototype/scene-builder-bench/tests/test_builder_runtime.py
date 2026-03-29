from scene_builder_bench.registry import load_normalized_plan, project_root
from scene_builder_runtime import BuilderSpec, WorldSettings, build_builder_spec, hash_payload


def test_build_builder_spec_is_deterministic_for_pine_tree() -> None:
    root = project_root()
    plan = load_normalized_plan(
        root / "fixtures" / "normalized_plans" / "add_pine_tree_left_of_cabin_001.normalized.json"
    )

    first = build_builder_spec(plan, world_settings=WorldSettings())
    second = build_builder_spec(plan, world_settings=WorldSettings())

    assert first.object_category == "tree"
    assert first.complexity.instance_count == 1
    assert hash_payload(first.model_dump(mode="json", exclude_none=True)) == hash_payload(
        second.model_dump(mode="json", exclude_none=True)
    )


def test_refine_inherits_parts_from_object_context() -> None:
    root = project_root()
    plan = load_normalized_plan(
        root / "fixtures" / "normalized_plans" / "refine_tree_soft_glow_001.normalized.json"
    )
    context = BuilderSpec.model_validate_json(
        (root / "fixtures" / "object_contexts" / "tree_1.builder.json").read_text(encoding="utf-8")
    )

    spec = build_builder_spec(plan, object_context=context, world_settings=WorldSettings())

    assert spec.operation.value == "refine"
    assert spec.complexity.part_count >= 2
    assert "glow" in spec.behaviors
    assert "neon" in spec.materials

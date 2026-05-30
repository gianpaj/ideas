from scene_planning_bench.prompts import build_prompt_bundle
from scene_planning_bench.registry import load_scene, load_task, project_root
from scene_planning_bench.validation import load_schema


def test_build_prompt_bundle_includes_scene_and_schema() -> None:
    root = project_root()
    scene = load_scene(root / "scenes" / "forest_cabin_001.json")
    task = load_task(
        root / "tasks" / "v1_core" / "single_turn" / "add_pine_tree_left_of_cabin_001.json"
    )
    response_schema = load_schema(root / "schemas" / "response.schema.json")

    prompt_bundle = build_prompt_bundle(
        "System prompt",
        scene,
        task,
        response_schema,
        task.prompts[0],
    )

    assert len(prompt_bundle) == 3
    assert prompt_bundle[0]["role"] == "system"
    assert "Scene context JSON" in prompt_bundle[1]["content"]
    assert "Response schema JSON Schema" in prompt_bundle[1]["content"]
    assert "allowed_response_types" not in prompt_bundle[1]["content"]
    assert prompt_bundle[2]["content"] == task.prompts[0]

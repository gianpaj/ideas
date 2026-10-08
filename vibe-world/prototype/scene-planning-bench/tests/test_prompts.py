from scene_planning_bench.prompts import build_prompt_bundle
from scene_planning_bench.registry import (
    load_scene,
    load_suite,
    load_task,
    load_tasks_from_suite,
    project_root,
)
from scene_planning_bench.validation import load_schema


def test_build_prompt_bundle_includes_scene_and_schema() -> None:
    root = project_root()
    scene = load_scene(root / "scenes" / "forest_cabin_001.json")
    task = load_task(
        root
        / "tasks"
        / "v1_core"
        / "single_turn"
        / "add_pine_tree_left_of_cabin_001.json"
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
    assert "allowed_response_types" in prompt_bundle[1]["content"]
    assert prompt_bundle[2]["content"] == task.prompts[0]


def test_voxel_core_baseline_and_tuned_use_production_input_format() -> None:
    root = project_root()
    for filename in ("v1_voxel_core.yaml", "v1_voxel_core_gemini_tuned.yaml"):
        suite_path = root / "configs/suites" / filename
        suite = load_suite(suite_path)
        schema = load_schema(root / suite.defaults.voxel_core_schema_path)
        for loaded in load_tasks_from_suite(suite_path):
            for prompt in loaded.task.prompts:
                bundle = build_prompt_bundle(
                    suite.defaults.system_prompt,
                    loaded.scene,
                    loaded.task,
                    schema,
                    prompt,
                )
                assert bundle == [
                    {"role": "system", "content": suite.defaults.system_prompt},
                    {"role": "user", "content": f"Player prompt: {prompt}"},
                ]

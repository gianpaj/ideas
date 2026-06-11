import copy
import json

from scene_planning_bench.adapters.mock_adapter import MockAdapter
from scene_planning_bench.evaluation import evaluate_output
from scene_planning_bench.registry import (
    load_scene,
    load_task,
    load_tasks_from_suite,
    project_root,
)
from scene_planning_bench.runner import run_suite_with_adapter
from scene_planning_bench.scoring import compute_voxel_core_score
from scene_runtime import ArtifactType

GOOD_CORE = {
    "object_category": "pine_tree",
    "size_tier": "medium",
    "style_tags": ["forest"],
    "behaviors": [],
    "materials": [
        {"material_id": "wood", "color_hint": "#6b4a2b"},
        {"material_id": "moss_stone", "color_hint": "#2f6b3a"},
    ],
    "operations": [
        {"op_id": "trunk", "kind": "add_box", "position": [0, 1, 0], "size": [0.6, 2, 0.6], "material_id": "wood"},
        {"op_id": "c1", "kind": "add_box", "position": [0, 2.4, 0], "size": [2, 1, 2], "material_id": "moss_stone"},
        {"op_id": "c2", "kind": "add_box", "position": [0, 3.2, 0], "size": [1.4, 0.9, 1.4], "material_id": "moss_stone"},
        {"op_id": "c3", "kind": "add_box", "position": [0, 3.9, 0], "size": [0.8, 0.7, 0.8], "material_id": "moss_stone"},
    ],
    "quantity": 1,
}


def test_good_core_scores_all_ones() -> None:
    score = compute_voxel_core_score(GOOD_CORE, profile="object")
    assert score.schema_validity == 1.0
    assert all(value == 1.0 for value in score.subscores.values()), score.subscores


def test_off_palette_material_penalized() -> None:
    core = copy.deepcopy(GOOD_CORE)
    core["materials"][0]["material_id"] = "chrome"
    core["operations"][0]["material_id"] = "chrome"
    score = compute_voxel_core_score(core, profile="object")
    assert score.subscores["palette_compliance"] < 1.0


def test_undeclared_op_material_penalized() -> None:
    core = copy.deepcopy(GOOD_CORE)
    core["operations"][0]["material_id"] = "not_declared"
    score = compute_voxel_core_score(core, profile="object")
    assert score.subscores["materials_declared"] == 0.0


def test_too_few_operations_penalized() -> None:
    core = copy.deepcopy(GOOD_CORE)
    core["operations"] = core["operations"][:2]
    score = compute_voxel_core_score(core, profile="object")
    assert score.subscores["op_count_in_range"] == 0.0


def test_duplicate_op_ids_penalized() -> None:
    core = copy.deepcopy(GOOD_CORE)
    core["operations"][1]["op_id"] = "trunk"
    score = compute_voxel_core_score(core, profile="object")
    assert score.subscores["op_ids_unique"] == 0.0


def test_floating_object_not_grounded() -> None:
    core = copy.deepcopy(GOOD_CORE)
    for op in core["operations"]:
        op["position"][1] += 5
    score = compute_voxel_core_score(core, profile="object")
    assert score.subscores["grounded"] == 0.0


def test_sunk_object_is_grounded_because_server_autogrounds() -> None:
    # A core modeled centered on the origin dips below the floor (min_y < 0).
    # The server lifts it to y=0, so this must NOT be penalized.
    core = copy.deepcopy(GOOD_CORE)
    for op in core["operations"]:
        op["position"][1] -= 2
    score = compute_voxel_core_score(core, profile="object")
    assert score.subscores["grounded"] == 1.0


def test_missing_required_op_field_fails_compile_hard() -> None:
    core = copy.deepcopy(GOOD_CORE)
    del core["operations"][0]["size"]  # add_box without size cannot compile
    score = compute_voxel_core_score(core, profile="object")
    assert score.schema_validity == 0.0


def test_stray_op_key_compiles_but_soft_penalized() -> None:
    # color_hint belongs on the material; on an op it is silently stripped by
    # production (so it compiles) but the requested color is lost (soft penalty).
    core = copy.deepcopy(GOOD_CORE)
    core["operations"][0]["color_hint"] = "#ff0000"
    score = compute_voxel_core_score(core, profile="object")
    assert score.schema_validity == 1.0  # not a hard fail
    assert score.subscores["ops_well_formed"] < 1.0  # but penalized
    # one stray op out of four => 3/4 clean
    assert score.subscores["ops_well_formed"] == 0.75


def test_non_hex_color_hint_penalized() -> None:
    core = copy.deepcopy(GOOD_CORE)
    core["materials"][0]["color_hint"] = "brown"
    score = compute_voxel_core_score(core, profile="object")
    assert score.subscores["color_hint_valid"] < 1.0


def test_disconnected_parts_penalized() -> None:
    # Float one box far above the rest (the prod table 👎: tabletop above legs).
    core = copy.deepcopy(GOOD_CORE)
    core["operations"][3]["position"][1] += 10
    score = compute_voxel_core_score(core, profile="object")
    assert score.subscores["parts_connected"] == 0.0
    # Still grounded (the lowest op is unchanged) — these are independent checks.
    assert score.subscores["grounded"] == 1.0


def test_diagonal_line_penalized() -> None:
    # A line moving on >1 axis falls back to a bounds box in the compiler (the
    # prod campfire 👎 log3).
    core = copy.deepcopy(GOOD_CORE)
    core["operations"].append(
        {"op_id": "diag", "kind": "add_line", "from": [0, 1, 0], "to": [1, 2, 1],
         "radius": 0.2, "material_id": "wood"}
    )
    score = compute_voxel_core_score(core, profile="object")
    assert score.subscores["lines_axis_aligned"] == 0.0


def test_duplicate_material_penalized() -> None:
    # Same material_id declared twice → later color_hint silently overrides (the
    # prod campfire 👎: lava_light declared 4×).
    core = copy.deepcopy(GOOD_CORE)
    core["materials"].append({"material_id": "wood", "color_hint": "#000000"})
    score = compute_voxel_core_score(core, profile="object")
    assert score.subscores["materials_unique"] == 0.0


def test_reject_profile_accepts_rejection() -> None:
    score = compute_voxel_core_score({"rejection": "gibberish"}, profile="reject")
    assert score.schema_validity == 1.0
    assert score.subscores["rejected_correctly"] == 1.0


def test_reject_profile_rejects_a_built_object() -> None:
    score = compute_voxel_core_score(GOOD_CORE, profile="reject")
    assert score.subscores["rejected_correctly"] == 0.0


def test_object_profile_unexpected_rejection_hard_fails() -> None:
    score = compute_voxel_core_score({"rejection": "nope"}, profile="object")
    assert score.schema_validity == 0.0


def test_voxel_core_suite_loads() -> None:
    root = project_root()
    tasks = load_tasks_from_suite(root / "configs" / "suites" / "v1_voxel_core.yaml")
    assert len(tasks) == 6
    assert all(
        loaded.task.target_artifact is ArtifactType.VOXEL_CORE for loaded in tasks
    )


def test_voxel_core_suite_runner_smoke(tmp_path) -> None:
    results, summary_path = run_suite_with_adapter(
        "configs/suites/v1_voxel_core.yaml",
        MockAdapter(),
        tmp_path / "voxel_core_outputs",
    )
    assert len(results) == 6
    assert all(result.schema_valid for result in results)
    assert all(result.total_score == 1.0 for result in results)
    assert summary_path.exists()


def test_evaluate_voxel_core_gold_scores_one() -> None:
    root = project_root()
    task = load_task(
        root
        / "tasks"
        / "v1_voxel_core"
        / "single_turn"
        / "voxel_core_pine_tree_001.json"
    )
    scene = load_scene(root / "scenes" / f"{task.scene_id}.json")
    result = evaluate_output(
        task,
        scene=scene,
        raw_output=json.dumps(task.gold_payload()),
        adapter_name="mock",
        response_schema={},
        sample_id=f"{task.task_id}::prompt_0",
        prompt_index=0,
        prompt_text=task.prompts[0],
        prompt_bundle=None,
    )
    assert result.schema_valid is True
    assert result.total_score == 1.0
    assert result.artifact_subscores["grounded"] == 1.0

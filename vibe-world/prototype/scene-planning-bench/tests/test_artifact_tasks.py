import json

from scene_planning_bench.adapters.mock_adapter import MockAdapter
from scene_planning_bench.evaluation import evaluate_output
from scene_planning_bench.inspect_runner import run_suite_with_inspect_mock
from scene_planning_bench.registry import (
    load_scene,
    load_suite,
    load_task,
    load_tasks_from_suite,
    project_root,
)
from scene_planning_bench.runner import (
    load_artifact_schemas,
    resolve_task_schema,
    run_suite_with_adapter,
)
from scene_planning_bench.scoring import (
    compute_builder_scores,
    compute_voxel_scores,
)
from scene_planning_bench.utils import read_json
from scene_planning_bench.validation import validate_with_schema_path
from scene_runtime import ArtifactType


def test_builder_task_file_passes_schema_with_refs() -> None:
    root = project_root()
    for relative in [
        "tasks/v1_builder/single_turn/build_pine_tree_001.json",
        "tasks/v1_builder/constraints/build_barrel_triangle_001.json",
    ]:
        errors = validate_with_schema_path(
            read_json(root / relative),
            root / "schemas" / "task.schema.json",
        )
        assert errors == [], f"{relative}: {errors}"


def test_voxel_builder_task_file_passes_schema_with_refs() -> None:
    root = project_root()
    for relative in [
        "tasks/v1_voxel_builder/single_turn/voxel_pine_tree_001.json",
        "tasks/v1_voxel_builder/single_turn/voxel_forest_guardian_avatar_001.json",
        "tasks/v1_voxel_builder/constraints/voxel_barrel_ring_001.json",
    ]:
        errors = validate_with_schema_path(
            read_json(root / relative),
            root / "schemas" / "task.schema.json",
        )
        assert errors == [], f"{relative}: {errors}"


def test_builder_suite_loads() -> None:
    root = project_root()
    suite = load_suite(root / "configs" / "suites" / "v1_builder.yaml")
    assert suite.suite_id == "v1_builder"
    tasks = load_tasks_from_suite(root / "configs" / "suites" / "v1_builder.yaml")
    assert len(tasks) == 2
    assert all(
        loaded.task.target_artifact is ArtifactType.BUILDER for loaded in tasks
    )


def test_voxel_builder_suite_loads() -> None:
    root = project_root()
    suite = load_suite(root / "configs" / "suites" / "v1_voxel_builder.yaml")
    assert suite.suite_id == "v1_voxel_builder"
    tasks = load_tasks_from_suite(root / "configs" / "suites" / "v1_voxel_builder.yaml")
    assert len(tasks) == 3
    assert all(
        loaded.task.target_artifact is ArtifactType.VOXEL_BUILDER for loaded in tasks
    )


def test_all_artifacts_suite_loads() -> None:
    root = project_root()
    tasks = load_tasks_from_suite(
        root / "configs" / "suites" / "v1_all_artifacts.yaml"
    )
    artifact_types = {loaded.task.target_artifact for loaded in tasks}
    assert ArtifactType.SCENE_ACTIONS in artifact_types
    assert ArtifactType.BUILDER in artifact_types
    assert ArtifactType.VOXEL_BUILDER in artifact_types


def test_builder_scores_are_perfect_on_gold() -> None:
    task = load_task(
        project_root()
        / "tasks"
        / "v1_builder"
        / "single_turn"
        / "build_pine_tree_001.json"
    )
    assert task.gold_builder is not None
    scores = compute_builder_scores(task.gold_builder, task.gold_builder)
    assert all(value == 1.0 for value in scores.values())


def test_voxel_scores_are_perfect_on_gold() -> None:
    task = load_task(
        project_root()
        / "tasks"
        / "v1_voxel_builder"
        / "single_turn"
        / "voxel_pine_tree_001.json"
    )
    assert task.gold_voxel_builder is not None
    scores = compute_voxel_scores(task.gold_voxel_builder, task.gold_voxel_builder)
    assert all(value == 1.0 for value in scores.values())


def test_evaluate_builder_gold_output_scores_one() -> None:
    root = project_root()
    task = load_task(
        root / "tasks" / "v1_builder" / "single_turn" / "build_pine_tree_001.json"
    )
    scene = load_scene(root / "scenes" / f"{task.scene_id}.json")
    suite = load_suite(root / "configs" / "suites" / "v1_builder.yaml")
    artifact_schemas = load_artifact_schemas(root, suite.defaults)
    artifact_schema = resolve_task_schema(task, artifact_schemas)
    raw_output = json.dumps(task.gold_payload())
    result = evaluate_output(
        task,
        scene=scene,
        raw_output=raw_output,
        adapter_name="mock",
        response_schema={},
        sample_id=f"{task.task_id}::prompt_0",
        prompt_index=0,
        prompt_text=task.prompts[0],
        prompt_bundle=None,
        artifact_schema=artifact_schema,
    )
    assert result.schema_valid is True
    assert result.total_score == 1.0
    assert result.action_type_score == 1.0
    assert result.spatial_match_score == 1.0
    assert result.artifact_subscores
    assert result.parsed_artifact is not None


def test_evaluate_voxel_gold_output_scores_one() -> None:
    root = project_root()
    task = load_task(
        root
        / "tasks"
        / "v1_voxel_builder"
        / "single_turn"
        / "voxel_forest_guardian_avatar_001.json"
    )
    suite = load_suite(root / "configs" / "suites" / "v1_voxel_builder.yaml")
    artifact_schemas = load_artifact_schemas(root, suite.defaults)
    artifact_schema = resolve_task_schema(task, artifact_schemas)
    scene = load_scene(root / "scenes" / f"{task.scene_id}.json")
    raw_output = json.dumps(task.gold_payload())
    result = evaluate_output(
        task,
        scene=scene,
        raw_output=raw_output,
        adapter_name="mock",
        response_schema={},
        sample_id=f"{task.task_id}::prompt_0",
        prompt_index=0,
        prompt_text=task.prompts[0],
        prompt_bundle=None,
        artifact_schema=artifact_schema,
    )
    assert result.schema_valid is True
    assert result.total_score == 1.0
    assert "op_kind_match" in result.artifact_subscores


def test_builder_suite_runner_smoke(tmp_path) -> None:
    results, summary_path = run_suite_with_adapter(
        "configs/suites/v1_builder.yaml",
        MockAdapter(),
        tmp_path / "builder_outputs",
    )
    assert len(results) == 2
    assert all(result.schema_valid for result in results)
    assert all(result.total_score == 1.0 for result in results)
    assert all(
        result.target_artifact is ArtifactType.BUILDER for result in results
    )
    assert summary_path.exists()


def test_voxel_builder_suite_runner_smoke(tmp_path) -> None:
    results, summary_path = run_suite_with_adapter(
        "configs/suites/v1_voxel_builder.yaml",
        MockAdapter(),
        tmp_path / "voxel_outputs",
    )
    assert len(results) == 3
    assert all(result.schema_valid for result in results)
    assert all(result.total_score == 1.0 for result in results)
    assert all(
        result.target_artifact is ArtifactType.VOXEL_BUILDER for result in results
    )
    assert summary_path.exists()


def test_all_artifacts_suite_inspect_mock(tmp_path) -> None:
    logs, results, summary_path = run_suite_with_inspect_mock(
        "configs/suites/v1_all_artifacts.yaml",
        tmp_path / "all_outputs",
    )
    assert len(logs) == 1
    assert len(results) >= 6
    artifact_types = {result.target_artifact for result in results}
    assert ArtifactType.SCENE_ACTIONS in artifact_types
    assert ArtifactType.BUILDER in artifact_types
    assert ArtifactType.VOXEL_BUILDER in artifact_types
    assert summary_path.exists()

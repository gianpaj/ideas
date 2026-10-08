from scene_planning_bench.registry import (
    load_suite,
    load_tasks_from_suite,
    project_root,
)
from scene_planning_bench.types import RunMatrixConfig
from scene_planning_bench.utils import read_yaml
from scene_runtime import ArtifactType


def test_voxel_core_matrix_compares_mercury_with_game_and_fast_baselines() -> None:
    root = project_root()
    matrix = RunMatrixConfig.model_validate(
        read_yaml(root / "configs/matrices/voxel_core_models.yaml")
    )
    assert [entry.model for entry in matrix.models] == [
        "inception/mercury-2.5",
        "google/gemini-2.5-flash",
        "google/gemini-3.5-flash-lite",
        "google/gemini-3.1-flash-lite",
        "anthropic/claude-haiku-5-5",
        "openai/gpt-6-luna",
    ]
    assert all(entry.enabled for entry in matrix.models)
    assert len({entry.label for entry in matrix.models}) == len(matrix.models)
    assert matrix.models[-1].reasoning_effort == "none"
    assert all(entry.reasoning_effort is None for entry in matrix.models[:-1])

    suite = load_suite(root / matrix.suite)
    assert suite.suite_id == "v1_voxel_core"
    tasks = load_tasks_from_suite(root / matrix.suite)
    assert len(tasks) == 6
    assert all(task.task.target_artifact is ArtifactType.VOXEL_CORE for task in tasks)

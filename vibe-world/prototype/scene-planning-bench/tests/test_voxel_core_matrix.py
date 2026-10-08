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


def test_tuned_cross_provider_matrix_preserves_selected_models_and_effort() -> None:
    root = project_root()
    baseline = RunMatrixConfig.model_validate(
        read_yaml(root / "configs/matrices/voxel_core_models.yaml")
    )
    tuned = RunMatrixConfig.model_validate(
        read_yaml(root / "configs/matrices/voxel_core_tuned_cross_provider.yaml")
    )
    assert tuned.suite == "configs/suites/v1_voxel_core_gemini_tuned.yaml"
    assert [entry.model for entry in tuned.models] == [
        entry.model
        for entry in baseline.models
        if entry.model != "google/gemini-2.5-flash"
    ]
    assert all(entry.enabled for entry in tuned.models)
    assert len({entry.label for entry in tuned.models}) == len(tuned.models)
    assert [(entry.label, entry.reasoning_effort) for entry in tuned.models] == [
        ("mercury-2.5", None),
        ("gemini-3.5-flash-lite", None),
        ("gemini-3.1-flash-lite", None),
        ("claude-haiku-5-5-low", "low"),
        ("gpt-6-luna-none", "none"),
    ]


def test_gemini_tuned_suite_preserves_baseline_tasks_and_schemas() -> None:
    root = project_root()
    baseline_path = root / "configs/suites/v1_voxel_core.yaml"
    matrix = RunMatrixConfig.model_validate(
        read_yaml(root / "configs/matrices/voxel_core_gemini_tuned.yaml")
    )
    assert [(entry.model, entry.label) for entry in matrix.models] == [
        ("google/gemini-3.5-flash-lite", "gemini-3.5-flash-lite")
    ]
    assert matrix.models[0].enabled
    assert matrix.models[0].reasoning_effort is None

    baseline = load_suite(baseline_path)
    tuned = load_suite(root / matrix.suite)
    assert tuned.suite_id == "v1_voxel_core_gemini_tuned"
    assert tuned.task_roots == baseline.task_roots
    assert tuned.defaults.model_dump(exclude={"system_prompt"}) == (
        baseline.defaults.model_dump(exclude={"system_prompt"})
    )
    assert tuned.defaults.system_prompt != baseline.defaults.system_prompt
    assert load_tasks_from_suite(root / matrix.suite) == load_tasks_from_suite(
        baseline_path
    )

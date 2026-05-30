from pathlib import Path

from scene_planning_bench.registry import (
    load_suite,
    load_task,
    load_tasks_from_suite,
    project_root,
    resolve_suite_task_paths,
)


def test_load_single_task() -> None:
    root = project_root()
    task = load_task(
        root / "tasks" / "v1_core" / "single_turn" / "add_pine_tree_left_of_cabin_001.json"
    )
    assert task.task_id == "add_pine_tree_left_of_cabin_001"
    assert task.scene_id == "forest_cabin_001"


def test_load_tasks_from_suite() -> None:
    tasks = load_tasks_from_suite(
        project_root() / "configs" / "suites" / "v1_core.yaml"
    )
    assert len(tasks) == 3
    assert all(loaded.scene.scene_id == loaded.task.scene_id for loaded in tasks)


def test_load_suite() -> None:
    suite = load_suite(project_root() / "configs" / "suites" / "v1_core.yaml")
    assert suite.suite_id == "v1_core"
    assert suite.task_roots


def test_resolve_suite_task_paths_from_roots() -> None:
    suite = load_suite(project_root() / "configs" / "suites" / "v1_core.yaml")
    task_paths = resolve_suite_task_paths(suite)
    assert len(task_paths) == 3
    assert task_paths[0].startswith("tasks/v1_core/")


def test_dev_and_hidden_suites_are_disjoint() -> None:
    root = project_root()
    dev_paths = set(
        resolve_suite_task_paths(load_suite(root / "configs" / "suites" / "v1_dev.yaml"))
    )
    hidden_paths = set(
        resolve_suite_task_paths(
            load_suite(root / "configs" / "suites" / "v1_hidden.yaml")
        )
    )

    assert dev_paths
    assert hidden_paths
    assert dev_paths.isdisjoint(hidden_paths)

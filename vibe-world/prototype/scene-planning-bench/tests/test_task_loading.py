from pathlib import Path

from scene_planning_bench.registry import load_suite, load_task, load_tasks_from_suite, project_root


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
    assert suite.task_paths

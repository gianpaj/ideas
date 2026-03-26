from __future__ import annotations

from pathlib import Path

from scene_planning_bench.types import BenchmarkTask, LoadedTask, SceneDefinition, SuiteConfig
from scene_planning_bench.utils import read_json, read_yaml


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_suite(path: Path) -> SuiteConfig:
    return SuiteConfig.model_validate(read_yaml(path))


def load_scene(path: Path) -> SceneDefinition:
    return SceneDefinition.model_validate(read_json(path))


def load_task(path: Path) -> BenchmarkTask:
    return BenchmarkTask.model_validate(read_json(path))


def load_tasks_from_suite(suite_path: Path) -> list[LoadedTask]:
    root = project_root()
    suite = load_suite(suite_path)
    loaded: list[LoadedTask] = []

    for task_relative_path in suite.task_paths:
        task_path = root / task_relative_path
        task = load_task(task_path)
        scene_path = root / "scenes" / f"{task.scene_id}.json"
        scene = load_scene(scene_path)
        loaded.append(LoadedTask(path=task_path, task=task, scene=scene))

    return loaded

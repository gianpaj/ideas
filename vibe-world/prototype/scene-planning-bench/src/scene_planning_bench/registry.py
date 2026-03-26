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


def resolve_suite_task_paths(suite: SuiteConfig) -> list[str]:
    resolved = list(suite.task_paths)
    root = project_root()

    for task_root in suite.task_roots:
        task_dir = root / task_root
        resolved.extend(
            sorted(
                str(path.relative_to(root))
                for path in task_dir.rglob("*.json")
            )
        )

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(resolved))


def load_tasks_from_suite(suite_path: Path) -> list[LoadedTask]:
    root = project_root()
    suite = load_suite(suite_path)
    loaded: list[LoadedTask] = []

    for task_relative_path in resolve_suite_task_paths(suite):
        task_path = root / task_relative_path
        task = load_task(task_path)
        scene_path = root / "scenes" / f"{task.scene_id}.json"
        scene = load_scene(scene_path)
        loaded.append(LoadedTask(path=task_path, task=task, scene=scene))

    return loaded

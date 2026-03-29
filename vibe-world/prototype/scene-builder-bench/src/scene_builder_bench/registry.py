from __future__ import annotations

from pathlib import Path

from scene_builder_bench.utils import read_json, read_yaml
from scene_builder_runtime import BuilderSpec, BuilderTask, LoadedTask, NormalizedScenePlan, SuiteConfig


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_suite(path: Path) -> SuiteConfig:
    return SuiteConfig.model_validate(read_yaml(path))


def load_task(path: Path) -> BuilderTask:
    return BuilderTask.model_validate(read_json(path))


def load_normalized_plan(path: Path) -> NormalizedScenePlan:
    return NormalizedScenePlan.model_validate(read_json(path))


def load_builder_spec(path: Path) -> BuilderSpec:
    return BuilderSpec.model_validate(read_json(path))


def resolve_suite_task_paths(suite: SuiteConfig) -> list[str]:
    root = project_root()
    resolved = list(suite.task_paths)

    for task_root in suite.task_roots:
        task_dir = root / task_root
        resolved.extend(
            sorted(
                str(path.relative_to(root))
                for path in task_dir.rglob("*.json")
            )
        )

    return list(dict.fromkeys(resolved))


def load_tasks_from_suite(suite_path: Path) -> list[LoadedTask]:
    root = project_root()
    suite = load_suite(suite_path)
    loaded: list[LoadedTask] = []

    for task_relative_path in resolve_suite_task_paths(suite):
        task_path = root / task_relative_path
        task = load_task(task_path)
        normalized_plan = load_normalized_plan(root / task.input_plan_path)
        object_context = (
            load_builder_spec(root / task.object_context_path)
            if task.object_context_path
            else None
        )
        loaded.append(
            LoadedTask(
                task_path=task_relative_path,
                task=task,
                normalized_plan=normalized_plan,
                object_context=object_context,
            )
        )

    return loaded

from __future__ import annotations

from pathlib import Path
from typing import Any

from scene_planning_bench.adapters.base import Adapter
from scene_planning_bench.evaluation import evaluate_output
from scene_planning_bench.registry import (
    load_suite,
    load_tasks_from_suite,
    project_root,
)
from scene_planning_bench.reports.json_report import write_run_reports
from scene_planning_bench.types import BenchmarkTask, RunResult, SuiteDefaults
from scene_planning_bench.validation import load_schema
from scene_runtime import ArtifactType


def load_artifact_schemas(
    root: Path, defaults: SuiteDefaults
) -> dict[ArtifactType, dict[str, Any]]:
    return {
        ArtifactType.SCENE_ACTIONS: load_schema(root / defaults.response_schema_path),
        ArtifactType.BUILDER: load_schema(root / defaults.builder_schema_path),
        ArtifactType.VOXEL_BUILDER: load_schema(
            root / defaults.voxel_builder_schema_path
        ),
    }


def resolve_task_schema(
    task: BenchmarkTask,
    schemas: dict[ArtifactType, dict[str, Any]],
) -> dict[str, Any]:
    return schemas[task.target_artifact]


def run_suite_with_adapter(
    suite_relative_path: str,
    adapter: Adapter,
    output_dir: Path,
    *,
    repeats: int = 1,
) -> tuple[list[RunResult], Path]:
    if repeats < 1:
        raise ValueError("repeats must be at least 1")

    root = project_root()
    suite_path = root / suite_relative_path
    suite_config = load_suite(suite_path)
    schemas = load_artifact_schemas(root, suite_config.defaults)
    loaded_tasks = load_tasks_from_suite(suite_path)
    results: list[RunResult] = []

    for loaded_task in loaded_tasks:
        task = loaded_task.task
        artifact_schema = resolve_task_schema(task, schemas)
        for repeat_index in range(repeats):
            raw_output = adapter.generate(loaded_task)
            results.append(
                evaluate_output(
                    task,
                    loaded_task.scene,
                    raw_output,
                    adapter.name,
                    schemas[ArtifactType.SCENE_ACTIONS],
                    sample_id=_sample_id(
                        task.task_id,
                        prompt_index=0,
                        repeat_index=repeat_index,
                        repeats=repeats,
                    ),
                    prompt_index=0,
                    repeat_index=repeat_index,
                    prompt_text=task.prompts[0],
                    artifact_schema=artifact_schema,
                )
            )

    summary_path = write_run_reports(output_dir, results)
    return results, summary_path


def _sample_id(
    task_id: str,
    *,
    prompt_index: int,
    repeat_index: int,
    repeats: int,
) -> str:
    base = f"{task_id}::prompt_{prompt_index}"
    if repeats == 1:
        return base
    return f"{base}::repeat_{repeat_index}"

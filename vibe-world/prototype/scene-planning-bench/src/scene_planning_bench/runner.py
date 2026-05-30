from __future__ import annotations

from pathlib import Path

from scene_planning_bench.adapters.base import Adapter
from scene_planning_bench.evaluation import evaluate_output
from scene_planning_bench.registry import load_tasks_from_suite, project_root
from scene_planning_bench.reports.json_report import write_run_reports
from scene_planning_bench.types import RunResult
from scene_planning_bench.validation import load_schema


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
    response_schema = load_schema(root / "schemas" / "response.schema.json")
    loaded_tasks = load_tasks_from_suite(suite_path)
    results: list[RunResult] = []

    for loaded_task in loaded_tasks:
        for repeat_index in range(repeats):
            raw_output = adapter.generate(loaded_task)
            results.append(
                evaluate_output(
                    loaded_task.task,
                    loaded_task.scene,
                    raw_output,
                    adapter.name,
                    response_schema,
                    sample_id=_sample_id(
                        loaded_task.task.task_id,
                        prompt_index=0,
                        repeat_index=repeat_index,
                        repeats=repeats,
                    ),
                    prompt_index=0,
                    repeat_index=repeat_index,
                    prompt_text=loaded_task.task.prompts[0],
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

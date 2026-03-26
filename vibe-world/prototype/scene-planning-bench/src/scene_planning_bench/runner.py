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
) -> tuple[list[RunResult], Path]:
    root = project_root()
    suite_path = root / suite_relative_path
    response_schema = load_schema(root / "schemas" / "response.schema.json")
    loaded_tasks = load_tasks_from_suite(suite_path)
    results: list[RunResult] = []

    for loaded_task in loaded_tasks:
        raw_output = adapter.generate(loaded_task)
        results.append(
            evaluate_output(
                loaded_task.task,
                raw_output,
                adapter.name,
                response_schema,
                sample_id=f"{loaded_task.task.task_id}::prompt_0",
                prompt_index=0,
                prompt_text=loaded_task.task.prompts[0],
            )
        )

    summary_path = write_run_reports(output_dir, results)
    return results, summary_path

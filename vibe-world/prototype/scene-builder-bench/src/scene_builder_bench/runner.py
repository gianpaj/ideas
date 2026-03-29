from __future__ import annotations

from pathlib import Path

from scene_builder_bench.adapters.base import BuilderAdapter
from scene_builder_bench.evaluation import evaluate_loaded_task
from scene_builder_bench.registry import load_suite, load_tasks_from_suite, project_root
from scene_builder_bench.reports.json_report import write_run_report
from scene_builder_bench.validation.schema_validate import load_schema
from scene_builder_runtime import RunResult


def run_suite_with_adapter(
    suite: str,
    adapter: BuilderAdapter,
    output_dir: Path,
) -> tuple[list[RunResult], Path]:
    root = project_root()
    suite_config = load_suite(root / suite)
    builder_schema = load_schema(root / suite_config.defaults.builder_schema_path)
    results = [
        evaluate_loaded_task(loaded_task, adapter, builder_schema)
        for loaded_task in load_tasks_from_suite(root / suite)
    ]
    report_path = write_run_report(output_dir, results)
    return results, report_path

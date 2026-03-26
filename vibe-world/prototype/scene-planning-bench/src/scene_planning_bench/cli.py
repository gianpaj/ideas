from __future__ import annotations

from pathlib import Path

import typer

from scene_planning_bench.adapters.mock_adapter import MockAdapter
from scene_planning_bench.registry import load_tasks_from_suite, project_root
from scene_planning_bench.reports.compare_report import compare_summaries
from scene_planning_bench.runner import run_suite_with_adapter
from scene_planning_bench.validation import load_schema, validate_with_schema

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("validate-data")
def validate_data(
    suite: str = "configs/suites/v1_core.yaml",
) -> None:
    root = project_root()
    response_schema = load_schema(root / "schemas" / "response.schema.json")
    tasks = load_tasks_from_suite(root / suite)
    invalid = 0

    for loaded_task in tasks:
        schema_errors = validate_with_schema(
            loaded_task.task.gold_response.model_dump(mode="json", exclude_none=True),
            response_schema,
        )
        if schema_errors:
            invalid += 1
            typer.echo(f"{loaded_task.task.task_id}: invalid gold response")
            for error in schema_errors:
                typer.echo(f"  - {error}")

    if invalid:
        raise typer.Exit(code=1)

    typer.echo(f"validated {len(tasks)} tasks")


@app.command("run-mock")
def run_mock(
    suite: str = "configs/suites/v1_core.yaml",
    output_dir: Path | None = None,
) -> None:
    root = project_root()
    output = output_dir or root / "outputs" / "latest"
    _, summary_path = run_suite_with_adapter(suite, MockAdapter(), output)
    typer.echo(f"wrote summary to {summary_path}")


@app.command("compare-runs")
def compare_runs(left: Path, right: Path) -> None:
    comparison = compare_summaries(left, right)
    typer.echo(comparison.to_string(index=False))

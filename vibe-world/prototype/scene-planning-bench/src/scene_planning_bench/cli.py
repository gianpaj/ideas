from __future__ import annotations

from pathlib import Path

import typer

from scene_planning_bench.inspect_runner import run_suite_with_inspect_mock
from scene_planning_bench.adapters.mock_adapter import MockAdapter
from scene_planning_bench.registry import (
    load_suite,
    load_tasks_from_suite,
    project_root,
    resolve_suite_task_paths,
)
from scene_planning_bench.reports.compare_report import compare_summaries
from scene_planning_bench.runner import run_suite_with_adapter
from scene_planning_bench.utils import read_json, read_yaml
from scene_planning_bench.validation import (
    load_schema,
    validate_with_schema,
    validate_with_schema_path,
)

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("validate-data")
def validate_data(
    suite: str = "configs/suites/v1_core.yaml",
) -> None:
    root = project_root()
    suite_path = root / suite
    suite_config = load_suite(root / suite)
    suite_schema_path = root / "schemas" / "suite.schema.json"
    task_schema_path = root / suite_config.defaults.task_schema_path
    scene_schema_path = root / suite_config.defaults.scene_schema_path
    response_schema = load_schema(root / suite_config.defaults.response_schema_path)
    tasks = load_tasks_from_suite(root / suite)
    invalid = 0

    suite_errors = validate_with_schema_path(read_yaml(suite_path), suite_schema_path)
    if suite_errors:
        invalid += 1
        typer.echo(f"{suite}: invalid suite config")
        for error in suite_errors:
            typer.echo(f"  - {error}")

    for task_relative_path in resolve_suite_task_paths(suite_config):
        task_errors = validate_with_schema_path(
            read_json(root / task_relative_path),
            task_schema_path,
        )
        if task_errors:
            invalid += 1
            typer.echo(f"{task_relative_path}: invalid task file")
            for error in task_errors:
                typer.echo(f"  - {error}")

    validated_scene_ids: set[str] = set()
    for loaded_task in tasks:
        if loaded_task.task.scene_id not in validated_scene_ids:
            scene_json_path = root / "scenes" / f"{loaded_task.task.scene_id}.json"
            scene_errors = validate_with_schema_path(
                read_json(scene_json_path),
                scene_schema_path,
            )
            if scene_errors:
                invalid += 1
                typer.echo(f"{loaded_task.task.scene_id}: invalid scene file")
                for error in scene_errors:
                    typer.echo(f"  - {error}")
            validated_scene_ids.add(loaded_task.task.scene_id)

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

    typer.echo(f"validated {len(tasks)} tasks and {len(validated_scene_ids)} scenes")


@app.command("run-mock")
def run_mock(
    suite: str = "configs/suites/v1_core.yaml",
    output_dir: Path | None = None,
) -> None:
    root = project_root()
    output = output_dir or root / "outputs" / "latest"
    _, summary_path = run_suite_with_adapter(suite, MockAdapter(), output)
    typer.echo(f"wrote summary to {summary_path}")


@app.command("run-inspect-mock")
def run_inspect_mock(
    suite: str = "configs/suites/v1_core.yaml",
    output_dir: Path | None = None,
) -> None:
    root = project_root()
    output = output_dir or root / "outputs" / "inspect_mock_latest"
    _, _, summary_path = run_suite_with_inspect_mock(suite, output)
    typer.echo(f"wrote summary to {summary_path}")


@app.command("compare-runs")
def compare_runs(left: Path, right: Path) -> None:
    comparison = compare_summaries(left, right)
    typer.echo(comparison.to_string(index=False))

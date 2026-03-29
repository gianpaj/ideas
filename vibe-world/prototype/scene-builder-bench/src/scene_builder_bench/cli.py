from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path

import typer

from scene_builder_bench.adapters.local_builder import LocalBuilderAdapter
from scene_builder_bench.registry import (
    load_suite,
    load_tasks_from_suite,
    project_root,
    resolve_suite_task_paths,
)
from scene_builder_bench.runner import run_suite_with_adapter
from scene_builder_bench.utils import read_json, read_yaml, write_json
from scene_builder_bench.validation.schema_validate import (
    load_schema,
    validate_with_schema,
    validate_with_schema_path,
)

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _default_run_output_dir(root: Path, suite_id: str, label: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    return root / "outputs" / "runs" / f"{timestamp}_{suite_id}_{label}"


@app.command("validate-data")
def validate_data(
    suite: str = "configs/suites/v1_builder.yaml",
) -> None:
    root = project_root()
    suite_path = root / suite
    suite_config = load_suite(suite_path)
    invalid = 0

    suite_errors = validate_with_schema_path(
        read_yaml(suite_path),
        root / "schemas" / "suite.schema.json",
    )
    if suite_errors:
        invalid += 1
        typer.echo(f"{suite}: invalid suite config")
        for error in suite_errors:
            typer.echo(f"  - {error}")

    task_schema_path = root / suite_config.defaults.task_schema_path
    builder_schema = load_schema(root / suite_config.defaults.builder_schema_path)

    for task_relative_path in resolve_suite_task_paths(suite_config):
        task_path = root / task_relative_path
        task_json = read_json(task_path)
        task_errors = validate_with_schema_path(task_json, task_schema_path)
        if task_errors:
            invalid += 1
            typer.echo(f"{task_relative_path}: invalid task file")
            for error in task_errors:
                typer.echo(f"  - {error}")

    for loaded_task in load_tasks_from_suite(suite_path):
        spec_payload = loaded_task.object_context.model_dump(mode="json", exclude_none=True) if loaded_task.object_context else None
        if spec_payload is not None:
            context_errors = validate_with_schema(spec_payload, builder_schema)
            if context_errors:
                invalid += 1
                typer.echo(f"{loaded_task.task.task_id}: invalid object context")
                for error in context_errors:
                    typer.echo(f"  - {error}")

    if invalid:
        raise typer.Exit(code=1)

    typer.echo("all builder benchmark data is valid")


@app.command("run-local")
def run_local(
    suite: str = "configs/suites/v1_builder.yaml",
    output_dir: Path | None = None,
) -> None:
    root = project_root()
    suite_config = load_suite(root / suite)
    output = output_dir or _default_run_output_dir(root, suite_config.suite_id, "local")
    output.mkdir(parents=True, exist_ok=True)

    results, report_path = run_suite_with_adapter(
        suite,
        LocalBuilderAdapter(),
        output,
    )

    manifest = {
        "suite_id": suite_config.suite_id,
        "task_count": len(results),
        "report_path": str(report_path),
    }
    write_json(output / "run_manifest.json", manifest)
    typer.echo(f"wrote {report_path}")
    typer.echo(f"wrote {output / 'run_manifest.json'}")


def main() -> None:
    app()

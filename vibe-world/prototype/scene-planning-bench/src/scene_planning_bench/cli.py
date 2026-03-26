from __future__ import annotations

from pathlib import Path
from typing import Any
import os

import typer

from scene_planning_bench.inspect_runner import run_suite_with_inspect, run_suite_with_inspect_mock
from scene_planning_bench.adapters.mock_adapter import MockAdapter
from scene_planning_bench.registry import (
    load_suite,
    load_tasks_from_suite,
    project_root,
    resolve_suite_task_paths,
)
from scene_planning_bench.reports.compare_report import compare_summaries
from scene_planning_bench.runner import run_suite_with_adapter
from scene_planning_bench.run_layout import build_run_manifest, default_run_output_dir
from scene_planning_bench.types import RunResult
from scene_planning_bench.utils import read_data_file, read_json, read_yaml, write_json
from scene_planning_bench.validation import (
    load_schema,
    validate_with_schema,
    validate_with_schema_path,
)

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _provider_setup_hint(model: str) -> str | None:
    if model.startswith("openai/"):
        return (
            "OpenAI runs require the `openai` package and `OPENAI_API_KEY` in the environment."
        )
    return None


def _resolve_output_dir(suite: str, output_dir: Path | None, label: str) -> Path:
    if output_dir is not None:
        return output_dir
    root = project_root()
    suite_config = load_suite(root / suite)
    return default_run_output_dir(root, suite_config.suite_id, label)


def _write_manifest(
    suite: str,
    output_dir: Path,
    run_kind: str,
    adapter_name: str,
    results: list[RunResult],
    summary_path: Path,
    *,
    extra: dict[str, Any] | None = None,
) -> Path:
    root = project_root()
    suite_config = load_suite(root / suite)
    manifest = build_run_manifest(
        suite_id=suite_config.suite_id,
        run_kind=run_kind,
        adapter_name=adapter_name,
        output_dir=output_dir,
        results=results,
        summary_path=summary_path,
        extra=extra,
    )
    manifest_path = output_dir / "run_manifest.json"
    write_json(manifest_path, manifest)
    return manifest_path


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
    output = _resolve_output_dir(suite, output_dir, "mock")
    results, summary_path = run_suite_with_adapter(suite, MockAdapter(), output)
    manifest_path = _write_manifest(
        suite,
        output,
        "adapter",
        "mock",
        results,
        summary_path,
    )
    typer.echo(f"wrote summary to {summary_path}")
    typer.echo(f"wrote manifest to {manifest_path}")


@app.command("run-inspect-mock")
def run_inspect_mock(
    suite: str = "configs/suites/v1_core.yaml",
    output_dir: Path | None = None,
) -> None:
    output = _resolve_output_dir(suite, output_dir, "inspect-mock")
    _, results, summary_path = run_suite_with_inspect_mock(suite, output)
    manifest_path = _write_manifest(
        suite,
        output,
        "inspect",
        "mockllm/scene-planning-bench",
        results,
        summary_path,
        extra={"inspect_log_dir": str(output / "inspect_logs")},
    )
    typer.echo(f"wrote summary to {summary_path}")
    typer.echo(f"wrote manifest to {manifest_path}")


@app.command("run-inspect-model")
def run_inspect_model(
    model: str,
    suite: str = "configs/suites/v1_core.yaml",
    output_dir: Path | None = None,
    model_args_file: Path | None = None,
) -> None:
    provider_hint = _provider_setup_hint(model)
    if model.startswith("openai/") and not os.getenv("OPENAI_API_KEY"):
        typer.echo(
            "missing OPENAI_API_KEY for OpenAI model runs",
            err=True,
        )
        if provider_hint:
            typer.echo(provider_hint, err=True)
        raise typer.Exit(code=1)

    output = _resolve_output_dir(suite, output_dir, model)
    model_args = read_data_file(model_args_file) if model_args_file else {}
    try:
        _, results, summary_path = run_suite_with_inspect(
            suite,
            output,
            model=model,
            model_args=model_args,
        )
    except Exception as exc:
        typer.echo(f"run failed for model {model}", err=True)
        typer.echo(str(exc), err=True)
        if provider_hint:
            typer.echo(provider_hint, err=True)
        raise typer.Exit(code=1) from exc

    manifest_path = _write_manifest(
        suite,
        output,
        "inspect",
        model,
        results,
        summary_path,
        extra={
            "inspect_log_dir": str(output / "inspect_logs"),
            "model_args_file": str(model_args_file) if model_args_file else None,
        },
    )
    typer.echo(f"wrote summary to {summary_path}")
    typer.echo(f"wrote manifest to {manifest_path}")


@app.command("compare-runs")
def compare_runs(left: Path, right: Path) -> None:
    comparison = compare_summaries(left, right)
    typer.echo(comparison.to_string(index=False))

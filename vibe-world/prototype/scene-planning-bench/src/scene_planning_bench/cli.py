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
from scene_planning_bench.reports.matrix_report import (
    write_matrix_manifest,
    write_matrix_reports,
)
from scene_planning_bench.runner import run_suite_with_adapter
from scene_planning_bench.run_layout import (
    build_run_manifest,
    default_matrix_output_dir,
    default_run_output_dir,
)
from scene_planning_bench.types import RunMatrixConfig, RunResult
from scene_planning_bench.utils import (
    load_env,
    read_data_file,
    read_json,
    read_yaml,
    write_json,
)
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
    if model.startswith("anthropic/"):
        return (
            "Anthropic runs require the `anthropic` package and `ANTHROPIC_API_KEY` in the environment."
        )
    if model.startswith("google/"):
        return (
            "Google runs require the `google-genai` package and `GOOGLE_API_KEY` in the environment."
        )
    return None


def _resolve_output_dir(suite: str, output_dir: Path | None, label: str) -> Path:
    if output_dir is not None:
        return output_dir
    root = project_root()
    suite_config = load_suite(root / suite)
    return default_run_output_dir(root, suite_config.suite_id, label)


def _resolve_matrix_output_dir(
    suite: str,
    output_dir: Path | None,
    label: str,
) -> Path:
    if output_dir is not None:
        return output_dir
    root = project_root()
    suite_config = load_suite(root / suite)
    return default_matrix_output_dir(root, suite_config.suite_id, label)


def _load_default_env(env_file: Path | None = None) -> Path | None:
    candidate = env_file or (project_root() / ".env")
    if load_env(candidate):
        return candidate
    return None


def _require_provider_env(model: str) -> None:
    missing_var: str | None = None
    if model.startswith("openai/") and not os.getenv("OPENAI_API_KEY"):
        missing_var = "OPENAI_API_KEY"
    elif model.startswith("anthropic/") and not os.getenv("ANTHROPIC_API_KEY"):
        missing_var = "ANTHROPIC_API_KEY"
    elif model.startswith("google/") and not os.getenv("GOOGLE_API_KEY"):
        missing_var = "GOOGLE_API_KEY"

    if missing_var is not None:
        typer.echo(f"missing {missing_var} for model runs", err=True)
        provider_hint = _provider_setup_hint(model)
        if provider_hint:
            typer.echo(provider_hint, err=True)
        raise typer.Exit(code=1)


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


def _run_inspect_model_impl(
    *,
    model: str,
    suite: str,
    output: Path,
    model_args_file: Path | None = None,
) -> tuple[list[RunResult], Path, Path]:
    _require_provider_env(model)
    model_args = read_data_file(model_args_file) if model_args_file else {}
    try:
        if model == "mockllm/scene-planning-bench" and model_args_file is None:
            _, results, summary_path = run_suite_with_inspect_mock(suite, output)
        else:
            _, results, summary_path = run_suite_with_inspect(
                suite,
                output,
                model=model,
                model_args=model_args,
            )
    except Exception as exc:
        typer.echo(f"run failed for model {model}", err=True)
        typer.echo(str(exc), err=True)
        provider_hint = _provider_setup_hint(model)
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
    return results, summary_path, manifest_path


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
    _load_default_env()
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
    _load_default_env()
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
    env_file: Path | None = None,
) -> None:
    loaded_env = _load_default_env(env_file)
    output = _resolve_output_dir(suite, output_dir, model)
    _, summary_path, manifest_path = _run_inspect_model_impl(
        model=model,
        suite=suite,
        output=output,
        model_args_file=model_args_file,
    )
    if loaded_env:
        typer.echo(f"loaded env from {loaded_env}")
    typer.echo(f"wrote summary to {summary_path}")
    typer.echo(f"wrote manifest to {manifest_path}")


@app.command("run-matrix")
def run_matrix(
    matrix_file: Path,
    output_dir: Path | None = None,
    env_file: Path | None = None,
    continue_on_error: bool = True,
) -> None:
    loaded_env = _load_default_env(env_file)
    matrix_path = matrix_file.resolve()
    matrix = RunMatrixConfig.model_validate(read_data_file(matrix_path))
    matrix_output = _resolve_matrix_output_dir(
        matrix.suite,
        output_dir,
        matrix.matrix_id,
    )
    rows: list[dict[str, Any]] = []

    for entry in matrix.models:
        if not entry.enabled:
            continue
        label = entry.label or entry.model
        run_output = matrix_output / "runs" / label.replace("/", "_")
        try:
            _results, summary_path, manifest_path = _run_inspect_model_impl(
                model=entry.model,
                suite=matrix.suite,
                output=run_output,
                model_args_file=(
                    (matrix_path.parent / entry.model_args_file).resolve()
                    if entry.model_args_file is not None
                    else None
                ),
            )
            aggregate = read_json(run_output / "aggregate.json")
            rows.append(
                {
                    "label": label,
                    "model": entry.model,
                    "status": "success",
                    "run_dir": str(run_output),
                    "summary_path": str(summary_path),
                    "manifest_path": str(manifest_path),
                    "mean_total_score": aggregate.get("mean_total_score"),
                    "mean_total_time_seconds": aggregate.get("mean_total_time_seconds"),
                    "mean_working_time_seconds": aggregate.get(
                        "mean_working_time_seconds"
                    ),
                    "mean_total_tokens": aggregate.get("mean_total_tokens"),
                    "total_cost_usd": aggregate.get("total_cost_usd"),
                    "score_per_total_second": aggregate.get(
                        "score_per_total_second"
                    ),
                    "score_per_dollar": aggregate.get("score_per_dollar"),
                }
            )
        except typer.Exit as exc:
            rows.append(
                {
                    "label": label,
                    "model": entry.model,
                    "status": "failed",
                    "run_dir": str(run_output),
                    "error": f"exit_code={exc.exit_code}",
                }
            )
            if not continue_on_error:
                raise

    summary_path, leaderboard_path = write_matrix_reports(matrix_output, rows)
    manifest_path = write_matrix_manifest(
        matrix_output,
        {
            "matrix_id": matrix.matrix_id,
            "suite": matrix.suite,
            "env_file": str(loaded_env) if loaded_env else None,
            "matrix_file": str(matrix_path),
            "continue_on_error": continue_on_error,
            "model_count": len([entry for entry in matrix.models if entry.enabled]),
            "summary_path": str(summary_path),
            "leaderboard_path": str(leaderboard_path),
        },
    )
    if loaded_env:
        typer.echo(f"loaded env from {loaded_env}")
    typer.echo(f"wrote matrix summary to {summary_path}")
    typer.echo(f"wrote leaderboard to {leaderboard_path}")
    typer.echo(f"wrote matrix manifest to {manifest_path}")


@app.command("compare-runs")
def compare_runs(left: Path, right: Path) -> None:
    comparison = compare_summaries(left, right)
    typer.echo(comparison.to_string(index=False))

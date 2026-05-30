from __future__ import annotations

import os
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

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

PROVIDER_ENV_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
}

PROVIDER_BASE_URLS: dict[str, str] = {}


def _default_run_output_dir(root: Path, suite_id: str, label: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    return root / "outputs" / "runs" / f"{timestamp}_{suite_id}_{label}"


def _load_env() -> None:
    env_path = project_root() / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and value and key not in os.environ:
            os.environ[key] = value


def _make_llm_adapter(
    model: str,
    *,
    base_url: str | None = None,
) -> "LLMBuilderAdapter":
    from scene_builder_bench.adapters.llm_builder import LLMBuilderAdapter

    provider = model.split("/")[0] if "/" in model else ""
    env_key = PROVIDER_ENV_KEYS.get(provider, "")
    api_key = os.environ.get(env_key) if env_key else None
    resolved_base_url = base_url or PROVIDER_BASE_URLS.get(provider)
    return LLMBuilderAdapter(
        model=model,
        base_url=resolved_base_url,
        api_key=api_key,
    )


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


@app.command("run-llm")
def run_llm(
    model: str,
    suite: str = "configs/suites/v1_builder.yaml",
    output_dir: Path | None = None,
    base_url: str | None = None,
) -> None:
    _load_env()
    root = project_root()
    suite_config = load_suite(root / suite)
    label = model.replace("/", "_")
    output = output_dir or _default_run_output_dir(root, suite_config.suite_id, label)
    output.mkdir(parents=True, exist_ok=True)

    adapter = _make_llm_adapter(model, base_url=base_url)
    results, report_path = run_suite_with_adapter(suite, adapter, output)

    manifest = {
        "suite_id": suite_config.suite_id,
        "model": model,
        "task_count": len(results),
        "report_path": str(report_path),
    }
    write_json(output / "run_manifest.json", manifest)
    typer.echo(f"wrote {report_path}")


@app.command("run-matrix")
def run_matrix(
    matrix_file: Path,
    output_dir: Path | None = None,
    continue_on_error: bool = True,
) -> None:
    _load_env()
    root = project_root()
    matrix = read_yaml(matrix_file)
    suite = matrix.get("suite", "configs/suites/v1_builder.yaml")
    matrix_id = matrix.get("matrix_id", "unnamed")
    suite_config = load_suite(root / suite)

    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    matrix_output = output_dir or (
        root / "outputs" / "matrices" / f"{timestamp}_{suite_config.suite_id}_{matrix_id}"
    )
    matrix_output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []

    for entry in matrix.get("models", []):
        if not entry.get("enabled", True):
            continue
        model = entry["model"]
        label = entry.get("label", model)
        base_url = entry.get("base_url")
        run_output = matrix_output / "runs" / label.replace("/", "_")
        run_output.mkdir(parents=True, exist_ok=True)

        typer.echo(f"running {label} ({model})...")
        try:
            adapter = _make_llm_adapter(model, base_url=base_url)
            results, report_path = run_suite_with_adapter(suite, adapter, run_output)
            aggregate = read_json(report_path)
            rows.append({
                "label": label,
                "model": model,
                "status": "success",
                "average_score": aggregate.get("average_score"),
                "task_count": aggregate.get("task_count"),
                "results": [
                    {
                        "task_id": r.get("task_id"),
                        "total_score": r.get("total_score"),
                        "schema_valid": r.get("schema_valid"),
                        "semantic_valid": r.get("semantic_valid"),
                        "deterministic": r.get("deterministic"),
                        "expected_checks_passed": r.get("expected_checks_passed"),
                    }
                    for r in aggregate.get("results", [])
                ],
            })
            typer.echo(f"  {label}: avg_score={aggregate.get('average_score')}")
        except Exception as exc:
            rows.append({
                "label": label,
                "model": model,
                "status": "failed",
                "error": str(exc),
            })
            typer.echo(f"  {label}: FAILED — {exc}")
            if not continue_on_error:
                raise typer.Exit(code=1) from exc

    leaderboard = sorted(
        [r for r in rows if r["status"] == "success"],
        key=lambda r: r.get("average_score", 0),
        reverse=True,
    )
    summary = {
        "matrix_id": matrix_id,
        "suite": suite,
        "model_count": len(rows),
        "leaderboard": leaderboard,
        "all_runs": rows,
    }
    summary_path = matrix_output / "matrix_summary.json"
    write_json(summary_path, summary)
    typer.echo(f"\nwrote matrix summary to {summary_path}")

    typer.echo("\n=== LEADERBOARD ===")
    for i, entry in enumerate(leaderboard, 1):
        typer.echo(f"  {i}. {entry['label']}: {entry.get('average_score', 'N/A')}")


def main() -> None:
    app()

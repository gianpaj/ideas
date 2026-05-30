import json
from pathlib import Path

from scene_planning_bench.chart import infer_csv_from_manifest, render_matrix_table

from scene_planning_bench.adapters.mock_adapter import MockAdapter
from scene_planning_bench.cli import run_matrix
from scene_planning_bench.inspect_runner import (
    _extract_log_error_message,
    run_suite_with_inspect_mock,
)
from scene_planning_bench.runner import run_suite_with_adapter


def test_runner_smoke(tmp_path: Path) -> None:
    results, summary_path = run_suite_with_adapter(
        "configs/suites/v1_core.yaml",
        MockAdapter(),
        tmp_path / "outputs",
    )

    assert len(results) == 3
    assert all(result.schema_valid for result in results)
    assert all(result.sample_id.endswith("::prompt_0") for result in results)
    assert all(result.total_time_seconds is None for result in results)
    assert summary_path.exists()
    aggregate = json.loads((tmp_path / "outputs" / "aggregate.json").read_text())
    assert aggregate["task_count"] == 3
    assert aggregate["paraphrase_group_count"] == 1
    assert "pine_tree_left_of_cabin" in aggregate["by_paraphrase_group"]
    assert aggregate["total_score_stddev"] == 0.0


def test_runner_repeats_samples(tmp_path: Path) -> None:
    results, summary_path = run_suite_with_adapter(
        "configs/suites/v1_dev.yaml",
        MockAdapter(),
        tmp_path / "outputs",
        repeats=2,
    )

    assert len(results) == 4
    assert all(result.repeat_index in {0, 1} for result in results)
    assert all("::repeat_" in result.sample_id for result in results)
    assert summary_path.exists()
    aggregate = json.loads((tmp_path / "outputs" / "aggregate.json").read_text())
    assert aggregate["sample_count"] == 4
    assert aggregate["task_count"] == 2
    assert aggregate["total_score_stderr"] == 0.0


def test_inspect_runner_smoke(tmp_path: Path) -> None:
    logs, results, summary_path = run_suite_with_inspect_mock(
        "configs/suites/v1_core.yaml",
        tmp_path / "inspect_outputs",
    )

    assert len(logs) == 1
    assert len(results) == 3
    assert all(result.schema_valid for result in results)
    assert all(result.inspect_log_location for result in results)
    assert all(result.total_time_seconds is not None for result in results)
    assert all(result.total_tokens is not None for result in results)
    assert all(result.score_per_total_second is not None for result in results)
    assert all(result.total_cost_usd is None for result in results)
    assert summary_path.exists()
    aggregate = json.loads(
        (tmp_path / "inspect_outputs" / "aggregate.json").read_text()
    )
    assert aggregate["task_count"] == 3
    assert aggregate["mean_total_time_seconds"] is not None
    assert aggregate["mean_total_tokens"] is not None
    assert aggregate["score_per_total_second"] is not None
    assert aggregate["score_per_dollar"] is None
    assert list((tmp_path / "inspect_outputs" / "inspect_logs").glob("*.json"))


def test_inspect_log_error_message_prefers_top_level_message() -> None:
    class ErrorLog:
        error = {"message": "Your API key was reported as leaked."}

    assert (
        _extract_log_error_message(ErrorLog())
        == "Your API key was reported as leaked."
    )


def test_run_matrix_smoke(tmp_path: Path) -> None:
    matrix_file = tmp_path / "matrix.yaml"
    matrix_file.write_text(
        "\n".join(
            [
                "matrix_id: test_matrix",
                "suite: configs/suites/v1_core.yaml",
                "models:",
                "  - model: mockllm/scene-planning-bench",
                "    label: mock_primary",
                "  - model: mockllm/scene-planning-bench",
                "    label: mock_secondary",
            ]
        )
    )
    env_file = tmp_path / ".env"
    env_file.write_text("DUMMY_VALUE=1\n")

    run_matrix(
        matrix_file=matrix_file,
        output_dir=tmp_path / "matrix_outputs",
        env_file=env_file,
        continue_on_error=False,
    )

    matrix_summary = tmp_path / "matrix_outputs" / "matrix_summary.csv"
    leaderboard = tmp_path / "matrix_outputs" / "matrix_leaderboard.csv"
    manifest = tmp_path / "matrix_outputs" / "matrix_manifest.json"
    assert matrix_summary.exists()
    assert leaderboard.exists()
    assert manifest.exists()
    summary = json.loads(
        (tmp_path / "matrix_outputs" / "matrix_manifest.json").read_text()
    )
    assert summary["model_count"] == 2


def test_chart_resolves_csv_from_manifest(tmp_path: Path) -> None:
    output_dir = tmp_path / "matrix_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_csv = output_dir / "matrix_summary.csv"
    summary_csv.write_text(
        "\n".join(
            [
                "label,model,status,mean_total_score",
                "mock_primary,openai/gpt-5.4-mini,success,0.91",
                "mock_secondary,anthropic/claude-sonnet,success,0.87",
            ]
        )
        + "\n"
    )

    leaderboard_csv = output_dir / "matrix_leaderboard.csv"
    leaderboard_csv.write_text(
        "\n".join(
            [
                "label,model,status,mean_total_score",
                "mock_primary,openai/gpt-5.4-mini,success,0.91",
            ]
        )
        + "\n"
    )

    manifest = output_dir / "matrix_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "summary_path": str(summary_csv),
                "leaderboard_path": str(leaderboard_csv),
            }
        )
    )

    assert infer_csv_from_manifest(manifest, "summary") == summary_csv
    assert infer_csv_from_manifest(manifest, "leaderboard") == leaderboard_csv


def test_inception_provider_env_check() -> None:
    """Verify inception/ prefix triggers INCEPTION_API_KEY check."""
    import os
    from unittest.mock import patch
    from scene_planning_bench.cli import _require_provider_env

    # Should not raise when key is set
    with patch.dict(os.environ, {"INCEPTION_API_KEY": "test-key"}):
        _require_provider_env("inception/mercury-2")

    # Should raise when key is missing
    with patch.dict(os.environ, {}, clear=True):
        import typer
        import pytest
        with pytest.raises(typer.Exit):
            _require_provider_env("inception/mercury-2")


def test_chart_renders_matrix_table(capsys, tmp_path: Path) -> None:
    csv_path = tmp_path / "matrix_summary.csv"
    csv_path.write_text(
        "\n".join(
            [
                "label,model,status,mean_total_score",
                "gpt-5.4-mini,openai/gpt-5.4-mini,success,0.91",
                "claude-sonnet,anthropic/claude-sonnet,success,0.87",
                "gemini-flash,google/gemini-flash,success,0.89",
            ]
        )
        + "\n"
    )

    render_matrix_table(
        csv_path,
        "mean_total_score",
        row_field="label",
        column_field="provider",
    )

    output = capsys.readouterr().out
    assert "label" in output
    assert "openai" in output
    assert "anthropic" in output
    assert "google" in output
    assert "gpt-5.4-mini" in output
    assert "0.9100" in output

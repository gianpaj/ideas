import json
from pathlib import Path

from scene_planning_bench.adapters.mock_adapter import MockAdapter
from scene_planning_bench.cli import run_matrix
from scene_planning_bench.inspect_runner import run_suite_with_inspect_mock
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
    aggregate = json.loads((tmp_path / "inspect_outputs" / "aggregate.json").read_text())
    assert aggregate["task_count"] == 3
    assert aggregate["mean_total_time_seconds"] is not None
    assert aggregate["mean_total_tokens"] is not None
    assert aggregate["score_per_total_second"] is not None
    assert aggregate["score_per_dollar"] is None
    assert list((tmp_path / "inspect_outputs" / "inspect_logs").glob("*.json"))


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
    summary = json.loads((tmp_path / "matrix_outputs" / "matrix_manifest.json").read_text())
    assert summary["model_count"] == 2

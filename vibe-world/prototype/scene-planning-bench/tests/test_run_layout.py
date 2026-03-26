from pathlib import Path

from scene_planning_bench.run_layout import build_run_manifest, default_run_output_dir
from scene_planning_bench.types import RunResult


def test_default_run_output_dir_uses_suite_and_label() -> None:
    output_dir = default_run_output_dir(Path("/tmp/root"), "v1_core", "inspect-mock")
    assert output_dir.parent == Path("/tmp/root/outputs/runs")
    assert "v1-core" in output_dir.name
    assert "inspect-mock" in output_dir.name


def test_build_run_manifest_counts_tasks_and_samples() -> None:
    results = [
        RunResult(
            sample_id="task_a::prompt_0",
            task_id="task_a",
            adapter_name="mock",
            schema_valid=True,
            response_type_match=True,
            action_type_score=1.0,
            argument_match_score=1.0,
            spatial_match_score=1.0,
            total_score=1.0,
            raw_output="{}",
        ),
        RunResult(
            sample_id="task_b::prompt_0",
            task_id="task_b",
            adapter_name="mock",
            schema_valid=True,
            response_type_match=True,
            action_type_score=1.0,
            argument_match_score=1.0,
            spatial_match_score=1.0,
            total_score=1.0,
            raw_output="{}",
        ),
    ]

    manifest = build_run_manifest(
        suite_id="v1_core",
        run_kind="inspect",
        adapter_name="mockllm/scene-planning-bench",
        output_dir=Path("/tmp/out"),
        results=results,
        summary_path=Path("/tmp/out/summary.csv"),
        extra={"inspect_log_dir": "/tmp/out/inspect_logs"},
    )

    assert manifest["suite_id"] == "v1_core"
    assert manifest["sample_count"] == 2
    assert manifest["task_count"] == 2
    assert manifest["extra"]["inspect_log_dir"] == "/tmp/out/inspect_logs"

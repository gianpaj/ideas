from pathlib import Path

from scene_planning_bench.adapters.mock_adapter import MockAdapter
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
    assert summary_path.exists()
    assert (tmp_path / "outputs" / "aggregate.json").exists()


def test_inspect_runner_smoke(tmp_path: Path) -> None:
    logs, results, summary_path = run_suite_with_inspect_mock(
        "configs/suites/v1_core.yaml",
        tmp_path / "inspect_outputs",
    )

    assert len(logs) == 1
    assert len(results) == 3
    assert all(result.schema_valid for result in results)
    assert all(result.inspect_log_location for result in results)
    assert summary_path.exists()
    assert (tmp_path / "inspect_outputs" / "aggregate.json").exists()
    assert list((tmp_path / "inspect_outputs" / "inspect_logs").glob("*.json"))

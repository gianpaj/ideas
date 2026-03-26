from pathlib import Path

from scene_planning_bench.adapters.mock_adapter import MockAdapter
from scene_planning_bench.runner import run_suite_with_adapter


def test_runner_smoke(tmp_path: Path) -> None:
    results, summary_path = run_suite_with_adapter(
        "configs/suites/v1_core.yaml",
        MockAdapter(),
        tmp_path / "outputs",
    )

    assert len(results) == 3
    assert all(result.schema_valid for result in results)
    assert summary_path.exists()

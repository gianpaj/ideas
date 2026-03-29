from scene_builder_bench.adapters.local_builder import LocalBuilderAdapter
from scene_builder_bench.runner import run_suite_with_adapter
from scene_builder_bench.registry import project_root


def test_run_suite_with_adapter_smoke(tmp_path) -> None:
    root = project_root()

    results, report_path = run_suite_with_adapter(
        "configs/suites/v1_builder.yaml",
        LocalBuilderAdapter(),
        tmp_path / "runs",
    )

    assert len(results) == 3
    assert report_path.exists()
    assert all(result.schema_valid for result in results)
    assert all(result.semantic_valid for result in results)

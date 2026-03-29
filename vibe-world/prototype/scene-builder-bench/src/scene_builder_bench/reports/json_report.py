from __future__ import annotations

from pathlib import Path

from scene_builder_bench.utils import write_json
from scene_builder_runtime import RunResult


def write_run_report(output_dir: Path, results: list[RunResult]) -> Path:
    aggregate = {
        "task_count": len(results),
        "average_score": round(
            sum(result.total_score for result in results) / max(len(results), 1),
            6,
        ),
        "results": [
            result.model_dump(mode="json", exclude_none=True) for result in results
        ],
    }
    path = output_dir / "aggregate.json"
    write_json(path, aggregate)
    return path

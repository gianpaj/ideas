from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from scene_planning_bench.types import RunResult
from scene_planning_bench.utils import write_json


def build_aggregate_report(results: list[RunResult]) -> dict[str, Any]:
    if not results:
        return {
            "sample_count": 0,
            "task_count": 0,
            "adapter_names": [],
            "mean_total_score": 0.0,
            "schema_valid_rate": 0.0,
        }

    return {
        "sample_count": len(results),
        "task_count": len({result.task_id for result in results}),
        "adapter_names": sorted({result.adapter_name for result in results}),
        "mean_total_score": round(
            sum(result.total_score for result in results) / len(results),
            6,
        ),
        "schema_valid_rate": round(
            sum(1 for result in results if result.schema_valid) / len(results),
            6,
        ),
    }


def write_run_reports(
    output_dir: Path,
    results: list[RunResult],
    *,
    manifest: dict[str, Any] | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    for result in results:
        write_json(
            output_dir / "tasks" / f"{result.sample_id}.json",
            result.model_dump(mode="json"),
        )

    summary_path = output_dir / "summary.csv"
    summary_rows = [
        {
            "sample_id": result.sample_id,
            "task_id": result.task_id,
            "prompt_index": result.prompt_index,
            "prompt_text": result.prompt_text,
            "adapter_name": result.adapter_name,
            "schema_valid": result.schema_valid,
            "response_type_match": result.response_type_match,
            "action_type_score": result.action_type_score,
            "argument_match_score": result.argument_match_score,
            "spatial_match_score": result.spatial_match_score,
            "total_score": result.total_score,
            "inspect_log_location": result.inspect_log_location,
            "errors": " | ".join(result.errors),
        }
        for result in results
    ]
    pd.DataFrame(summary_rows).to_csv(
        summary_path,
        index=False,
    )

    write_json(output_dir / "aggregate.json", build_aggregate_report(results))
    if manifest is not None:
        write_json(output_dir / "run_manifest.json", manifest)
    return summary_path

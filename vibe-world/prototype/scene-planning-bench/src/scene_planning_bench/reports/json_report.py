from __future__ import annotations

from pathlib import Path

import pandas as pd

from scene_planning_bench.types import RunResult
from scene_planning_bench.utils import write_json


def write_run_reports(output_dir: Path, results: list[RunResult]) -> Path:
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
    return summary_path

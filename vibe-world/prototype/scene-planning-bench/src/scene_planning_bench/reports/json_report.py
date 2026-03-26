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
            "paraphrase_group_count": 0,
            "adapter_names": [],
            "mean_total_score": 0.0,
            "schema_valid_rate": 0.0,
            "by_task": {},
            "by_paraphrase_group": {},
        }

    by_task = {
        task_id: {
            "sample_count": len(task_results),
            "mean_total_score": round(
                sum(result.total_score for result in task_results) / len(task_results),
                6,
            ),
        }
        for task_id, task_results in _group_results(results, key="task_id").items()
    }
    by_paraphrase_group = {
        group_id: {
            "sample_count": len(group_results),
            "mean_total_score": round(
                sum(result.total_score for result in group_results)
                / len(group_results),
                6,
            ),
            "task_ids": sorted({result.task_id for result in group_results}),
        }
        for group_id, group_results in _group_results(
            [result for result in results if result.paraphrase_group],
            key="paraphrase_group",
        ).items()
    }

    return {
        "sample_count": len(results),
        "task_count": len({result.task_id for result in results}),
        "paraphrase_group_count": len(by_paraphrase_group),
        "adapter_names": sorted({result.adapter_name for result in results}),
        "mean_total_score": round(
            sum(result.total_score for result in results) / len(results),
            6,
        ),
        "schema_valid_rate": round(
            sum(1 for result in results if result.schema_valid) / len(results),
            6,
        ),
        "by_task": by_task,
        "by_paraphrase_group": by_paraphrase_group,
    }


def _group_results(
    results: list[RunResult],
    *,
    key: str,
) -> dict[str, list[RunResult]]:
    grouped: dict[str, list[RunResult]] = {}
    for result in results:
        group_key = getattr(result, key)
        if group_key is None:
            continue
        grouped.setdefault(group_key, []).append(result)
    return grouped


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
            "paraphrase_group": result.paraphrase_group,
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

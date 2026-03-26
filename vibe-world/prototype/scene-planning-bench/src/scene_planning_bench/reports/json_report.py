from __future__ import annotations

from pathlib import Path

import pandas as pd

from scene_planning_bench.types import RunResult
from scene_planning_bench.utils import write_json


def write_run_reports(output_dir: Path, results: list[RunResult]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    for result in results:
        write_json(
            output_dir / "tasks" / f"{result.task_id}.json",
            result.model_dump(mode="json"),
        )

    summary_path = output_dir / "summary.csv"
    pd.DataFrame([result.model_dump(mode="json") for result in results]).to_csv(
        summary_path,
        index=False,
    )
    return summary_path

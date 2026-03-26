from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from scene_planning_bench.utils import write_json


def write_matrix_reports(
    output_dir: Path,
    rows: list[dict[str, Any]],
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "matrix_summary.csv"
    leaderboard_path = output_dir / "matrix_leaderboard.csv"

    summary_df = pd.DataFrame(rows)
    if summary_df.empty:
        summary_df = pd.DataFrame(
            columns=[
                "model",
                "status",
                "mean_total_score",
                "mean_total_time_seconds",
                "total_cost_usd",
                "score_per_total_second",
                "score_per_dollar",
                "run_dir",
                "summary_path",
            ]
        )
    summary_df.to_csv(summary_path, index=False)

    leaderboard_df = summary_df.copy()
    if not leaderboard_df.empty and "status" in leaderboard_df.columns:
        leaderboard_df = leaderboard_df[leaderboard_df["status"] == "success"].copy()
    if not leaderboard_df.empty:
        if "score_per_dollar" in leaderboard_df.columns:
            leaderboard_df["score_per_dollar_rank"] = (
                leaderboard_df["score_per_dollar"].rank(
                    method="min",
                    ascending=False,
                    na_option="bottom",
                )
            )
        if "mean_total_time_seconds" in leaderboard_df.columns:
            leaderboard_df["speed_rank"] = leaderboard_df["mean_total_time_seconds"].rank(
                method="min",
                ascending=True,
                na_option="bottom",
            )
        if "mean_total_score" in leaderboard_df.columns:
            leaderboard_df["quality_rank"] = leaderboard_df["mean_total_score"].rank(
                method="min",
                ascending=False,
                na_option="bottom",
            )
        sort_cols = [
            col
            for col in ["quality_rank", "score_per_dollar_rank", "speed_rank"]
            if col in leaderboard_df.columns
        ]
        if sort_cols:
            leaderboard_df = leaderboard_df.sort_values(sort_cols)
    leaderboard_df.to_csv(leaderboard_path, index=False)
    return summary_path, leaderboard_path


def write_matrix_manifest(output_dir: Path, payload: dict[str, Any]) -> Path:
    manifest_path = output_dir / "matrix_manifest.json"
    write_json(manifest_path, payload)
    return manifest_path

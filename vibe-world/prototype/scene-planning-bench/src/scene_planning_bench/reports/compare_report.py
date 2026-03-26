from __future__ import annotations

from pathlib import Path

import pandas as pd


def compare_summaries(left: Path, right: Path) -> pd.DataFrame:
    left_df = pd.read_csv(left).add_prefix("left_")
    right_df = pd.read_csv(right).add_prefix("right_")
    if "left_task_id" in left_df.columns and "right_task_id" in right_df.columns:
        left_key = "left_task_id"
        right_key = "right_task_id"
    else:
        left_key = "left_sample_id" if "left_sample_id" in left_df.columns else "left_task_id"
        right_key = (
            "right_sample_id" if "right_sample_id" in right_df.columns else "right_task_id"
        )
    merged = left_df.merge(
        right_df,
        left_on=left_key,
        right_on=right_key,
        how="outer",
    )
    merged["score_delta"] = merged["right_total_score"] - merged["left_total_score"]
    if "left_total_time_seconds" in merged.columns and "right_total_time_seconds" in merged.columns:
        merged["time_delta_seconds"] = (
            merged["right_total_time_seconds"] - merged["left_total_time_seconds"]
        )
    if "left_total_cost_usd" in merged.columns and "right_total_cost_usd" in merged.columns:
        merged["cost_delta_usd"] = (
            merged["right_total_cost_usd"] - merged["left_total_cost_usd"]
        )
    if "left_score_per_dollar" in merged.columns and "right_score_per_dollar" in merged.columns:
        merged["score_per_dollar_delta"] = (
            merged["right_score_per_dollar"] - merged["left_score_per_dollar"]
        )
    return merged

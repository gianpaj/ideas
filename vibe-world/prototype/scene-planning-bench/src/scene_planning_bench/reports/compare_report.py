from __future__ import annotations

from pathlib import Path

import pandas as pd


def compare_summaries(left: Path, right: Path) -> pd.DataFrame:
    left_df = pd.read_csv(left).add_prefix("left_")
    right_df = pd.read_csv(right).add_prefix("right_")
    merged = left_df.merge(
        right_df,
        left_on="left_task_id",
        right_on="right_task_id",
        how="outer",
    )
    merged["score_delta"] = merged["right_total_score"] - merged["left_total_score"]
    return merged

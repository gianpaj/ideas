from __future__ import annotations

import argparse
import csv
from pathlib import Path

from termgraph import Args, BarChart, Colors, Data

DEFAULT_METRIC = "mean_total_score"


def latest_matrix_csv(kind: str) -> Path:
    matches = sorted(Path("outputs/matrices").glob(f"*/matrix_{kind}.csv"))
    if not matches:
        raise FileNotFoundError(
            f"no matrix_{kind}.csv files found under outputs/matrices/"
        )
    return matches[-1]


def load_chart_data(
    filename: Path,
    metric: str,
    *,
    label_field: str = "label",
    include_failed: bool = False,
) -> tuple[list[float], list[str]]:
    values: list[float] = []
    labels: list[str] = []

    with filename.open("r", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or metric not in reader.fieldnames:
            raise ValueError(f"metric {metric!r} not found in {filename}")

        for row in reader:
            if not include_failed and row.get("status") == "failed":
                continue

            raw_value = (row.get(metric) or "").strip()
            if raw_value == "":
                continue

            try:
                value = float(raw_value)
            except ValueError:
                continue

            labels.append(row.get(label_field) or row.get("model") or "unknown")
            values.append(value)

    if not values:
        raise ValueError(
            f"no numeric values found for metric {metric!r} in {filename}"
        )
    return values, labels


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render matrix CSV metrics with termgraph")
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Path to matrix_summary.csv or matrix_leaderboard.csv. Defaults to latest matrix_summary.csv.",
    )
    parser.add_argument(
        "--kind",
        choices=["summary", "leaderboard"],
        default="summary",
        help="Used only when --csv is omitted.",
    )
    parser.add_argument(
        "--metric",
        default=DEFAULT_METRIC,
        help="Numeric CSV column to chart, for example mean_total_score, mean_total_time_seconds, score_per_total_second, or score_per_dollar.",
    )
    parser.add_argument(
        "--label-field",
        default="label",
        help="CSV column to use for chart labels.",
    )
    parser.add_argument(
        "--include-failed",
        action="store_true",
        help="Include rows where status=failed if the metric column is numeric.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional chart title.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=60,
        help="Bar width.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    csv_path = args.csv or latest_matrix_csv(args.kind)
    values, labels = load_chart_data(
        csv_path,
        args.metric,
        label_field=args.label_field,
        include_failed=args.include_failed,
    )

    data = Data(values, labels)
    chart = BarChart(
        data,
        Args(
            title=args.title or f"{args.metric} ({csv_path.name})",
            colors=[Colors.Blue],
            width=args.width,
        ),
    )
    chart.draw()


if __name__ == "__main__":
    main()

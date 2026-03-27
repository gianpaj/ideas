from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace
else:
    Namespace = argparse.Namespace

DEFAULT_METRIC = "mean_total_score"
DEFAULT_GROUP_FIELD = "provider"


def latest_matrix_csv(kind: str) -> Path:
    matches = sorted(Path("outputs/matrices").glob(f"*/matrix_{kind}.csv"))
    if not matches:
        raise FileNotFoundError(
            f"no matrix_{kind}.csv files found under outputs/matrices/"
        )
    return matches[-1]


def latest_matrix_manifest() -> Path:
    matches = sorted(Path("outputs/matrices").glob("*/matrix_manifest.json"))
    if not matches:
        raise FileNotFoundError(
            "no matrix_manifest.json files found under outputs/matrices/"
        )
    return matches[-1]


def read_manifest(manifest_path: Path) -> dict[str, str | bool | int | float | None]:
    with manifest_path.open("r") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"manifest at {manifest_path} must be a JSON object")
    if not all(isinstance(key, str) for key in payload):
        raise ValueError(f"manifest at {manifest_path} must use string keys")
    return {
        key: value
        for key, value in payload.items()
        if isinstance(value, str | bool | int | float) or value is None
    }


def infer_csv_from_manifest(manifest_path: Path, kind: str) -> Path:
    payload = read_manifest(manifest_path)
    key = f"{kind}_path"
    raw_path = payload.get(key)
    if isinstance(raw_path, str) and raw_path.strip():
        return Path(raw_path)
    candidate = manifest_path.parent / f"matrix_{kind}.csv"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"could not resolve matrix_{kind}.csv from manifest {manifest_path}"
    )


def infer_provider(model: str) -> str:
    if "/" in model:
        return model.split("/", 1)[0]
    return "unknown"


def load_rows(
    filename: Path,
    *,
    include_failed: bool = False,
) -> list[dict[str, str]]:
    with filename.open("r", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"no CSV header found in {filename}")

        rows: list[dict[str, str]] = []
        for row in reader:
            normalized_row = {
                key: value or "" for key, value in row.items() if key is not None
            }
            if not include_failed and normalized_row.get("status") == "failed":
                continue
            rows.append(normalized_row)
    return rows


def load_chart_data(
    filename: Path,
    metric: str,
    *,
    label_field: str = "label",
    include_failed: bool = False,
) -> tuple[list[float], list[str]]:
    values: list[float] = []
    labels: list[str] = []

    rows = load_rows(filename, include_failed=include_failed)
    if rows and metric not in rows[0]:
        raise ValueError(f"metric {metric!r} not found in {filename}")

    for row in rows:
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
        raise ValueError(f"no numeric values found for metric {metric!r} in {filename}")
    return values, labels


def build_grouped_chart_data(
    filename: Path,
    metric: str,
    *,
    group_field: str = DEFAULT_GROUP_FIELD,
    label_field: str = "label",
    include_failed: bool = False,
) -> tuple[list[float], list[str]]:
    rows = load_rows(filename, include_failed=include_failed)
    grouped: dict[str, list[tuple[str, float]]] = defaultdict(list)

    for row in rows:
        raw_value = (row.get(metric) or "").strip()
        if raw_value == "":
            continue

        try:
            value = float(raw_value)
        except ValueError:
            continue

        model = row.get("model") or ""
        group_value = row.get(group_field) or ""
        if group_field == "provider" and not group_value:
            group_value = infer_provider(model)

        label_value = row.get(label_field) or model or "unknown"
        if not group_value:
            group_value = "ungrouped"

        grouped[group_value].append((label_value, value))

    if not grouped:
        raise ValueError(f"no numeric values found for metric {metric!r} in {filename}")

    values: list[float] = []
    labels: list[str] = []
    for group_name in sorted(grouped):
        for label_value, value in sorted(grouped[group_name], key=lambda item: item[0]):
            labels.append(f"{group_name}: {label_value}")
            values.append(value)
    return values, labels


def render_matrix_table(
    filename: Path,
    metric: str,
    *,
    row_field: str = "label",
    column_field: str = DEFAULT_GROUP_FIELD,
    include_failed: bool = False,
) -> None:
    rows = load_rows(filename, include_failed=include_failed)
    grouped: dict[str, dict[str, float]] = defaultdict(dict)
    row_names: set[str] = set()
    column_names: set[str] = set()

    for row in rows:
        raw_value = (row.get(metric) or "").strip()
        if raw_value == "":
            continue

        try:
            value = float(raw_value)
        except ValueError:
            continue

        model = row.get("model") or ""
        row_name = row.get(row_field) or model or "unknown"
        column_name = row.get(column_field) or ""
        if column_field == "provider" and not column_name:
            column_name = infer_provider(model)
        if not column_name:
            column_name = "ungrouped"

        grouped[row_name][column_name] = value
        row_names.add(row_name)
        column_names.add(column_name)

    if not grouped:
        raise ValueError(f"no numeric values found for metric {metric!r} in {filename}")

    sorted_rows = sorted(row_names)
    sorted_columns = sorted(column_names)

    first_col_width = max(len(row_field), *(len(name) for name in sorted_rows))
    col_widths = {column: max(len(column), 12) for column in sorted_columns}

    header = (
        " " * first_col_width
        + " | "
        + " | ".join(column.ljust(col_widths[column]) for column in sorted_columns)
    )
    divider = "-" * len(header)

    print(header)
    print(divider)
    for row_name in sorted_rows:
        cells: list[str] = []
        for column in sorted_columns:
            value = grouped[row_name].get(column)
            if value is None:
                cells.append("".ljust(col_widths[column]))
            else:
                cells.append(f"{value:.4f}".ljust(col_widths[column]))
        print(row_name.ljust(first_col_width) + " | " + " | ".join(cells))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render matrix CSV metrics with termgraph"
    )
    _ = parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Path to matrix_summary.csv or matrix_leaderboard.csv. Defaults to latest matrix_summary.csv.",
    )
    _ = parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Path to matrix_manifest.json. If provided without --csv, resolve the CSV path from the manifest.",
    )
    _ = parser.add_argument(
        "--kind",
        choices=["summary", "leaderboard"],
        default="summary",
        help="Used only when --csv is omitted.",
    )
    _ = parser.add_argument(
        "--metric",
        default=DEFAULT_METRIC,
        help="Numeric CSV column to chart, for example mean_total_score, mean_total_time_seconds, score_per_total_second, or score_per_dollar.",
    )
    _ = parser.add_argument(
        "--label-field",
        default="label",
        help="CSV column to use for chart labels.",
    )
    _ = parser.add_argument(
        "--group-field",
        default=DEFAULT_GROUP_FIELD,
        help="CSV column to use for grouped matrix/chart output. Defaults to provider, inferred from model when absent.",
    )
    _ = parser.add_argument(
        "--row-field",
        default="label",
        help="CSV column to use for matrix row labels.",
    )
    _ = parser.add_argument(
        "--column-field",
        default=DEFAULT_GROUP_FIELD,
        help="CSV column to use for matrix columns. Defaults to provider, inferred from model when absent.",
    )
    _ = parser.add_argument(
        "--mode",
        choices=["bars", "grouped-bars", "matrix"],
        default="bars",
        help="bars renders a plain bar chart, grouped-bars prefixes labels with the group field, and matrix prints a row/column matrix table.",
    )
    _ = parser.add_argument(
        "--include-failed",
        action="store_true",
        help="Include rows where status=failed if the metric column is numeric.",
    )
    _ = parser.add_argument(
        "--title",
        default=None,
        help="Optional chart title.",
    )
    _ = parser.add_argument(
        "--width",
        type=int,
        default=60,
        help="Bar width.",
    )
    return parser


def resolve_csv_path(args: Namespace) -> Path:
    csv_path = args.csv
    if isinstance(csv_path, Path):
        return csv_path

    manifest_path = args.manifest
    kind = str(args.kind)
    if isinstance(manifest_path, Path):
        return infer_csv_from_manifest(manifest_path, kind)

    try:
        return latest_matrix_csv(kind)
    except FileNotFoundError:
        manifest_path = latest_matrix_manifest()
        return infer_csv_from_manifest(manifest_path, kind)


def main() -> None:
    from termgraph import Args, BarChart, Colors, Data  # type: ignore[import-not-found]

    parser = build_parser()
    args = parser.parse_args()

    csv_path = resolve_csv_path(args)
    metric = str(args.metric)
    mode = str(args.mode)
    row_field = str(args.row_field)
    column_field = str(args.column_field)
    group_field = str(args.group_field)
    label_field = str(args.label_field)
    include_failed = bool(args.include_failed)
    title = args.title if isinstance(args.title, str) else None
    width = int(args.width)

    if mode == "matrix":
        render_matrix_table(
            csv_path,
            metric,
            row_field=row_field,
            column_field=column_field,
            include_failed=include_failed,
        )
        return

    if mode == "grouped-bars":
        values, labels = build_grouped_chart_data(
            csv_path,
            metric,
            group_field=group_field,
            label_field=label_field,
            include_failed=include_failed,
        )
    else:
        values, labels = load_chart_data(
            csv_path,
            metric,
            label_field=label_field,
            include_failed=include_failed,
        )

    data = Data(values, labels)  # type: ignore[call-arg]
    chart = BarChart(  # type: ignore[call-arg]
        data,
        Args(  # type: ignore[call-arg]
            title=title or f"{metric} ({csv_path.name})",
            colors=[Colors.Blue],  # type: ignore[attr-defined]
            width=width,
        ),
    )
    chart.draw()  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()

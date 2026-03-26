from __future__ import annotations

from pathlib import Path
from typing import Any

from scene_planning_bench.types import RunResult
from scene_planning_bench.utils import slugify, utc_now_iso, utc_timestamp_slug


def default_run_output_dir(root: Path, suite_id: str, label: str) -> Path:
    run_name = f"{utc_timestamp_slug()}_{slugify(suite_id)}_{slugify(label)}"
    return root / "outputs" / "runs" / run_name


def build_run_manifest(
    *,
    suite_id: str,
    run_kind: str,
    adapter_name: str,
    output_dir: Path,
    results: list[RunResult],
    summary_path: Path,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "created_at_utc": utc_now_iso(),
        "suite_id": suite_id,
        "run_kind": run_kind,
        "adapter_name": adapter_name,
        "output_dir": str(output_dir),
        "summary_path": str(summary_path),
        "aggregate_path": str(output_dir / "aggregate.json"),
        "task_count": len({result.task_id for result in results}),
        "sample_count": len(results),
    }
    if extra:
        manifest["extra"] = extra
    return manifest

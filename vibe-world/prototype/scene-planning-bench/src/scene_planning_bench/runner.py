from __future__ import annotations

from pathlib import Path

from scene_planning_bench.adapters.base import Adapter
from scene_planning_bench.registry import load_tasks_from_suite, project_root
from scene_planning_bench.reports.json_report import write_run_reports
from scene_planning_bench.scoring import (
    aggregate_score,
    compute_action_type_score,
    compute_argument_match_score,
    compute_schema_score,
)
from scene_planning_bench.types import RunResult
from scene_planning_bench.validation import load_schema, parse_response_json, validate_with_schema


def run_suite_with_adapter(
    suite_relative_path: str,
    adapter: Adapter,
    output_dir: Path,
) -> tuple[list[RunResult], Path]:
    root = project_root()
    suite_path = root / suite_relative_path
    response_schema = load_schema(root / "schemas" / "response.schema.json")
    loaded_tasks = load_tasks_from_suite(suite_path)
    results: list[RunResult] = []

    for loaded_task in loaded_tasks:
        raw_output = adapter.generate(loaded_task)
        schema_valid = False
        response_type_match = False
        action_type_score = 0.0
        argument_match_score = 0.0
        spatial_match_score = 1.0
        parsed_payload = None
        errors: list[str] = []

        try:
            parsed = parse_response_json(raw_output)
            parsed_payload = parsed.model_dump(mode="json", exclude_none=True)
            schema_errors = validate_with_schema(parsed_payload, response_schema)
            schema_valid = not schema_errors
            response_type_match = (
                parsed.response_type == loaded_task.task.gold_response.response_type
            )
            action_type_score = compute_action_type_score(
                loaded_task.task.gold_response,
                parsed,
            )
            argument_match_score = compute_argument_match_score(
                loaded_task.task.gold_response,
                parsed,
            )
            errors.extend(schema_errors)
        except ValueError as exc:
            errors.append(str(exc))
            schema_errors = errors

        total_score = aggregate_score(
            loaded_task.task.scoring_profile,
            schema_validity=compute_schema_score(schema_errors),
            action_type=action_type_score,
            argument_match=argument_match_score,
            spatial_match=spatial_match_score,
        )

        results.append(
            RunResult(
                task_id=loaded_task.task.task_id,
                adapter_name=adapter.name,
                schema_valid=schema_valid,
                response_type_match=response_type_match,
                action_type_score=action_type_score,
                argument_match_score=argument_match_score,
                spatial_match_score=spatial_match_score,
                total_score=total_score,
                raw_output=raw_output,
                parsed_response=parsed_payload,
                errors=errors,
            )
        )

    summary_path = write_run_reports(output_dir, results)
    return results, summary_path

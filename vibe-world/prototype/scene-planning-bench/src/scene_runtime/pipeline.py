from __future__ import annotations

from scene_runtime.contracts import PlanningOutcome, PlanningRequest
from scene_runtime.normalize import normalize_response
from scene_runtime.parsing import parse_response_json
from scene_runtime.rendering import build_render_drafts
from scene_runtime.schema import validate_with_schema


def process_planning_request(
    request: PlanningRequest,
    raw_output: str,
) -> PlanningOutcome:
    outcome = PlanningOutcome(
        request_id=request.request_id,
        raw_output=raw_output,
    )

    try:
        parsed_response = parse_response_json(raw_output)
    except ValueError as exc:
        outcome.diagnostics.append(str(exc))
        return outcome

    outcome.parsed_response = parsed_response
    schema_errors = validate_with_schema(
        parsed_response.model_dump(mode="json", exclude_none=True),
        request.response_schema,
    )
    outcome.schema_errors.extend(schema_errors)

    if schema_errors:
        outcome.diagnostics.extend(schema_errors)
        return outcome

    normalized_plan = normalize_response(request, parsed_response)
    outcome.normalized_plan = normalized_plan
    outcome.render_drafts = build_render_drafts(normalized_plan)
    outcome.diagnostics.extend(normalized_plan.diagnostics)
    return outcome

from __future__ import annotations

import json
import re
from json import JSONDecodeError

from pydantic import ValidationError

from scene_planning_bench.types import ScenePlanningResponse


def _strip_code_fence(raw_output: str) -> str:
    stripped = raw_output.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw_output


def parse_response_json(raw_output: str) -> ScenePlanningResponse:
    candidate = _strip_code_fence(raw_output)
    try:
        data = json.loads(candidate)
    except JSONDecodeError as exc:
        raise ValueError(f"invalid JSON output: {exc}") from exc

    try:
        return ScenePlanningResponse.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid response payload: {exc}") from exc

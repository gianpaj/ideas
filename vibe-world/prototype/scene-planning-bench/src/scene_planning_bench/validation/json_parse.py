from __future__ import annotations

import json
from json import JSONDecodeError

from pydantic import ValidationError

from scene_planning_bench.types import ScenePlanningResponse


def parse_response_json(raw_output: str) -> ScenePlanningResponse:
    try:
        data = json.loads(raw_output)
    except JSONDecodeError as exc:
        raise ValueError(f"invalid JSON output: {exc}") from exc

    try:
        return ScenePlanningResponse.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid response payload: {exc}") from exc

from __future__ import annotations

from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scene_planning_bench.utils import read_json


def load_schema(path: Path) -> dict[str, Any]:
    return read_json(path)


def validate_with_schema(data: Any, schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    return [error.message for error in validator.iter_errors(data)]

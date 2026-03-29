from __future__ import annotations

from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scene_builder_bench.utils import read_json


def load_schema(path: Path) -> dict[str, Any]:
    return read_json(path)


def validate_with_schema(payload: Any, schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    return [
        f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=str)
    ]


def validate_with_schema_path(payload: Any, path: Path) -> list[str]:
    return validate_with_schema(payload, load_schema(path))

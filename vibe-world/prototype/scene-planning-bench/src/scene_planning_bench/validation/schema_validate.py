from __future__ import annotations

from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from scene_planning_bench.utils import read_json


def load_schema(path: Path) -> dict[str, Any]:
    return read_json(path)


def build_schema_registry(schema_dir: Path) -> Registry[Any]:
    registry: Registry[Any] = Registry()
    for path in schema_dir.glob("*.json"):
        registry = registry.with_resource(
            path.name,
            Resource.from_contents(read_json(path)),
        )
    return registry


def validate_with_schema(data: Any, schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    return [error.message for error in validator.iter_errors(data)]


def validate_with_schema_path(data: Any, schema_path: Path) -> list[str]:
    schema = load_schema(schema_path)
    validator = Draft202012Validator(
        schema,
        registry=build_schema_registry(schema_path.parent),
    )
    return [error.message for error in validator.iter_errors(data)]

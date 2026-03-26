from scene_planning_bench.registry import load_task, project_root
from scene_planning_bench.utils import read_json, read_yaml
from scene_planning_bench.validation import (
    load_schema,
    parse_response_json,
    validate_with_schema,
    validate_with_schema_path,
)


def test_valid_gold_response_passes_schema() -> None:
    root = project_root()
    task = load_task(
        root / "tasks" / "v1_core" / "single_turn" / "add_pine_tree_left_of_cabin_001.json"
    )
    schema = load_schema(root / "schemas" / "response.schema.json")
    errors = validate_with_schema(
        task.gold_response.model_dump(mode="json", exclude_none=True),
        schema,
    )
    assert errors == []


def test_invalid_payload_fails_schema() -> None:
    schema = load_schema(project_root() / "schemas" / "response.schema.json")
    payload = {
        "schema_version": "1.0",
        "response_type": "scene_actions",
        "uncertainty": {"has_ambiguity": False, "fields": []},
    }
    errors = validate_with_schema(payload, schema)
    assert errors


def test_task_file_passes_schema_with_refs() -> None:
    root = project_root()
    errors = validate_with_schema_path(
        read_json(
            root
            / "tasks"
            / "v1_core"
            / "single_turn"
            / "add_pine_tree_left_of_cabin_001.json"
        ),
        root / "schemas" / "task.schema.json",
    )
    assert errors == []


def test_suite_config_passes_schema() -> None:
    root = project_root()
    errors = validate_with_schema_path(
        read_yaml(root / "configs" / "suites" / "v1_core.yaml"),
        root / "schemas" / "suite.schema.json",
    )
    assert errors == []


def test_parse_response_json_accepts_fenced_json() -> None:
    response = parse_response_json(
        """```json
        {
          "schema_version": "1.0",
          "response_type": "clarification_request",
          "clarification": {
            "question": "Which lake should the house be placed near?",
            "missing_fields": ["reference_object"]
          },
          "uncertainty": {
            "has_ambiguity": true,
            "fields": ["reference_object"]
          }
        }
        ```"""
    )
    assert response.response_type.value == "clarification_request"

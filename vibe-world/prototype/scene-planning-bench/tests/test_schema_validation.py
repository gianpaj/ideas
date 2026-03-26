from scene_planning_bench.registry import load_task, project_root
from scene_planning_bench.validation import load_schema, validate_with_schema


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
        "uncertainty": {"has_ambiguity": False, "fields": []}
    }
    errors = validate_with_schema(payload, schema)
    assert errors

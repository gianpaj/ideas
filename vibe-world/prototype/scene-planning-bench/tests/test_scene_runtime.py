from scene_planning_bench.registry import load_scene, project_root
from scene_runtime import (
    Clarification,
    NormalizedScenePlan,
    PlanKind,
    PlanningOutcome,
    PlanningRequest,
    ResponseType,
    Uncertainty,
    build_prompt_bundle,
    load_schema,
    parse_response_json,
)


def test_scene_runtime_build_prompt_bundle_from_request() -> None:
    root = project_root()
    scene = load_scene(root / "scenes" / "forest_cabin_001.json")
    schema = load_schema(root / "schemas" / "response.schema.json")
    request = PlanningRequest(
        request_id="req_001",
        scene=scene,
        user_prompt="Add a pine tree to the left of the cabin.",
        system_prompt="System prompt",
        response_schema=schema,
        metadata={"flow": "live_preview"},
    )

    prompt_bundle = build_prompt_bundle(request)

    assert len(prompt_bundle) == 3
    assert prompt_bundle[0]["role"] == "system"
    assert "Scene context JSON" in prompt_bundle[1]["content"]
    assert "Request metadata JSON" in prompt_bundle[1]["content"]
    assert "Response schema JSON Schema" in prompt_bundle[1]["content"]
    assert prompt_bundle[2]["content"] == request.user_prompt


def test_scene_runtime_planning_outcome_keeps_parsed_response() -> None:
    parsed = parse_response_json(
        """```json
        {
          "schema_version": "1.0",
          "response_type": "clarification_request",
          "clarification": {
            "question": "Which cabin do you mean?",
            "missing_fields": ["reference_object"]
          },
          "uncertainty": {
            "has_ambiguity": true,
            "fields": ["reference_object"]
          }
        }
        ```"""
    )

    outcome = PlanningOutcome(
        request_id="req_002",
        raw_output="{}",
        parsed_response=parsed,
    )

    assert outcome.parsed_response is not None
    assert outcome.parsed_response.response_type == ResponseType.CLARIFICATION_REQUEST


def test_scene_runtime_normalized_plan_contract_is_instantiable() -> None:
    plan = NormalizedScenePlan(
        request_id="req_003",
        plan_kind=PlanKind.CLARIFICATION,
        source_response_type=ResponseType.CLARIFICATION_REQUEST,
        uncertainty=Uncertainty(has_ambiguity=True, fields=["reference_object"]),
        clarification=Clarification(
            question="Which object should this be placed near?",
            missing_fields=["reference_object"],
        ),
    )

    assert plan.plan_version == "0.1"
    assert plan.plan_kind == PlanKind.CLARIFICATION
    assert plan.clarification is not None

import json
from pathlib import Path

from scene_planning_bench.reports.json_report import write_run_reports
from scene_planning_bench.types import RunResult


def test_write_run_reports_persists_runtime_artifacts(tmp_path: Path) -> None:
    result = RunResult(
        sample_id="task_a::prompt_0",
        task_id="task_a",
        adapter_name="mock",
        schema_valid=True,
        response_type_match=True,
        action_type_score=1.0,
        argument_match_score=1.0,
        spatial_match_score=1.0,
        total_score=1.0,
        raw_output="{}",
        repeat_index=1,
        parsed_response={"response_type": "scene_actions"},
        normalized_plan={
            "plan_kind": "object_intent",
            "intents": [{"intent_id": "intent_1"}],
        },
        render_drafts=[{"draft_id": "draft_1"}],
        diagnostics=["normalized successfully"],
    )

    summary_path = write_run_reports(tmp_path, [result])

    assert summary_path.exists()
    task_payload = json.loads((tmp_path / "tasks" / "task_a::prompt_0.json").read_text())
    assert task_payload["normalized_plan"]["plan_kind"] == "object_intent"
    assert task_payload["render_drafts"][0]["draft_id"] == "draft_1"

    summary_csv = summary_path.read_text()
    assert "normalized_intent_count" in summary_csv
    assert "render_draft_count" in summary_csv
    assert "repeat_index" in summary_csv
    assert "total_score_stderr" in (tmp_path / "aggregate.json").read_text()
    assert "diagnostics" in summary_csv

import csv
import json
from pathlib import Path

import httpx
import pytest
from anthropic import AsyncAnthropic
from inspect_ai import Task
from inspect_ai import eval as inspect_eval
from inspect_ai.dataset import Sample
from inspect_ai.log import read_eval_log
from inspect_ai.model import GenerateConfig
from inspect_ai.model._providers import anthropic as anthropic_provider
from inspect_ai.solver import generate
from pydantic import ValidationError

from scene_planning_bench import cli, inspect_runner
from scene_planning_bench.types import MatrixModelConfig


@pytest.mark.parametrize(
    "effort", [None, "none", "minimal", "low", "medium", "high", "xhigh"]
)
def test_matrix_accepts_reasoning_effort(effort: str | None) -> None:
    entry = MatrixModelConfig(model="openai/gpt-6-luna", reasoning_effort=effort)
    assert entry.reasoning_effort == effort


@pytest.mark.parametrize("effort", [None, "low", "medium", "high", "xhigh", "max"])
def test_matrix_accepts_anthropic_reasoning_effort(effort: str | None) -> None:
    entry = MatrixModelConfig(
        model="anthropic/claude-haiku-5-5", reasoning_effort=effort
    )
    assert entry.reasoning_effort == effort


@pytest.mark.parametrize(
    ("model", "effort"),
    [
        ("openai/gpt-6-luna", "max"),
        ("anthropic/claude-haiku-5-5", "none"),
        ("anthropic/claude-haiku-5-5", "minimal"),
    ],
)
def test_matrix_rejects_provider_invalid_effort(model: str, effort: str) -> None:
    with pytest.raises(ValidationError):
        MatrixModelConfig(model=model, reasoning_effort=effort)


def test_matrix_rejects_invalid_reasoning_effort() -> None:
    with pytest.raises(ValidationError):
        MatrixModelConfig(model="openai/gpt-6-luna", reasoning_effort="typo")


def test_matrix_rejects_reasoning_effort_for_other_providers() -> None:
    with pytest.raises(ValidationError, match="only for openai/"):
        MatrixModelConfig(model="google/gemini-3.1-flash-lite", reasoning_effort="low")


@pytest.mark.parametrize("effort", [None, "low"])
def test_runner_passes_generation_setting_not_model_argument(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, effort: str | None
) -> None:
    captured = {}

    def fake_eval(task, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(inspect_runner, "inspect_eval", fake_eval)
    inspect_runner.run_suite_with_inspect(
        "configs/suites/v1_dev.yaml",
        tmp_path,
        model="openai/gpt-6-luna",
        reasoning_effort=effort,
    )
    assert captured["model_args"] == {}
    if effort is None:
        assert "reasoning_effort" not in captured
    else:
        assert captured["reasoning_effort"] == effort


def test_matrix_records_and_forwards_effort(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = []

    def fake_eval(task, **kwargs):
        captured.append(kwargs)
        return []

    monkeypatch.setattr(inspect_runner, "inspect_eval", fake_eval)
    monkeypatch.setattr(cli, "_require_provider_env", lambda model: None)
    matrix = tmp_path / "matrix.yaml"
    matrix.write_text(
        "matrix_id: reasoning_test\n"
        "suite: configs/suites/v1_dev.yaml\n"
        "models:\n"
        "  - model: openai/gpt-6-luna\n"
        "    label: luna-low\n"
        "    reasoning_effort: low\n"
        "  - model: openai/gpt-6-luna\n"
        "    label: luna-default\n"
        "  - model: anthropic/claude-haiku-5-5\n"
        "    label: haiku-low\n"
        "    reasoning_effort: low\n"
        "  - model: anthropic/claude-haiku-5-5\n"
        "    label: haiku-medium\n"
        "    reasoning_effort: medium\n"
        "  - model: anthropic/claude-haiku-5-5\n"
        "    label: haiku-default\n"
    )
    env = tmp_path / ".env"
    env.write_text("")
    output = tmp_path / "output"
    cli.run_matrix(matrix, output_dir=output, env_file=env, repeats=3)

    assert captured[0]["reasoning_effort"] == "low"
    assert "reasoning_effort" not in captured[1]
    assert captured[2]["extra_body"] == {"output_config": {"effort": "low"}}
    assert captured[3]["extra_body"] == {"output_config": {"effort": "medium"}}
    assert "extra_body" not in captured[4]
    assert captured[4]["model_args"] == {}
    for filename in ("matrix_summary.csv", "matrix_leaderboard.csv"):
        rows = {r["label"]: r for r in csv.DictReader((output / filename).open())}
        assert rows["luna-low"]["reasoning_effort"] == "low"
        assert rows["luna-default"]["reasoning_effort"] == ""
        assert rows["haiku-low"]["reasoning_effort"] == "low"
        assert rows["haiku-medium"]["reasoning_effort"] == "medium"
        assert rows["haiku-default"]["reasoning_effort"] == ""
    for label, expected in (
        ("luna-low", "low"),
        ("luna-default", None),
        ("haiku-low", "low"),
        ("haiku-medium", "medium"),
        ("haiku-default", None),
    ):
        manifest = json.loads(
            (output / "runs" / label / "run_manifest.json").read_text()
        )
        assert manifest["extra"]["reasoning_effort"] == expected
        assert manifest["extra"]["repeats"] == 3


def test_failed_matrix_entry_preserves_effort(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_eval(task, **kwargs):
        raise RuntimeError("unsupported effort for this model")

    monkeypatch.setattr(inspect_runner, "inspect_eval", fake_eval)
    monkeypatch.setattr(cli, "_require_provider_env", lambda model: None)
    matrix = tmp_path / "matrix.yaml"
    matrix.write_text(
        "matrix_id: failure_test\n"
        "suite: configs/suites/v1_dev.yaml\n"
        "models:\n"
        "  - model: openai/gpt-6-luna\n"
        "    reasoning_effort: none\n"
    )
    env = tmp_path / ".env"
    env.write_text("")
    output = tmp_path / "output"
    cli.run_matrix(matrix, output_dir=output, env_file=env)
    row = next(csv.DictReader((output / "matrix_summary.csv").open()))
    assert row["status"] == "failed"
    assert row["reasoning_effort"] == "none"


@pytest.mark.parametrize("effort", [None, "low", "medium", "high", "xhigh", "max"])
@pytest.mark.parametrize("native_generation_supported", [False, True])
def test_anthropic_native_effort_forwarding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    effort: str | None,
    native_generation_supported: bool,
) -> None:
    captured = {}
    fields = ["metadata", "service_tier"]
    if native_generation_supported:
        fields.append("output_config")
    monkeypatch.setattr(
        anthropic_provider, "anthropic_extra_body_fields", lambda: fields
    )

    def fake_eval(task, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(inspect_runner, "inspect_eval", fake_eval)
    inspect_runner.run_suite_with_inspect(
        "configs/suites/v1_dev.yaml",
        tmp_path,
        model="anthropic/claude-haiku-5-5",
        reasoning_effort=effort,
    )
    assert "reasoning_effort" not in captured
    assert "effort" not in captured
    if effort is None:
        assert "extra_body" not in captured
        assert captured["model_args"] == {}
    else:
        payload = {"output_config": {"effort": effort}}
        assert captured["extra_body"] == payload
        assert captured["model_args"] == (
            {} if native_generation_supported else {"extra_body": payload}
        )


def test_anthropic_fallback_preserves_model_arguments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = {}
    model_args = {
        "streaming": False,
        "extra_body": {
            "metadata": {"user_id": "benchmark"},
            "output_config": {"effort": "high", "format": {"type": "json_schema"}},
        },
    }
    original = json.loads(json.dumps(model_args))
    monkeypatch.setattr(anthropic_provider, "anthropic_extra_body_fields", lambda: [])

    def fake_eval(task, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(inspect_runner, "inspect_eval", fake_eval)
    inspect_runner.run_suite_with_inspect(
        "configs/suites/v1_dev.yaml",
        tmp_path,
        model="anthropic/claude-haiku-5-5",
        model_args=model_args,
        reasoning_effort="xhigh",
    )
    assert model_args == original
    assert captured["model_args"]["streaming"] is False
    assert captured["model_args"]["extra_body"] == {
        "metadata": {"user_id": "benchmark"},
        "output_config": {"effort": "xhigh", "format": {"type": "json_schema"}},
    }


@pytest.mark.parametrize("effort", [None, "low", "medium", "high", "xhigh", "max"])
def test_installed_anthropic_adapter_payload_and_saved_config_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, effort: str | None
) -> None:
    requests = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "msg_offline",
                "type": "message",
                "role": "assistant",
                "model": "claude-haiku-5-5",
                "content": [{"type": "text", "text": "ok"}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    def offline_client(self):
        return AsyncAnthropic(
            api_key="offline-dummy-key",
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
        )

    monkeypatch.setattr(
        anthropic_provider.AnthropicAPI, "_create_client", offline_client
    )
    saved_logs = []

    def offline_eval(task, **kwargs):
        # Exercise real Inspect logging and the installed adapter with one cheap fixture.
        logs = inspect_eval(
            Task(dataset=[Sample(input="Reply ok")], solver=generate()),
            **(
                kwargs
                | {
                    "model_args": kwargs["model_args"] | {"streaming": False},
                    "max_tokens": 1024,
                }
            ),
        )
        saved_logs.extend(logs)
        return []

    monkeypatch.setattr(inspect_runner, "inspect_eval", offline_eval)
    inspect_runner.run_suite_with_inspect(
        "configs/suites/v1_dev.yaml",
        tmp_path,
        model="anthropic/claude-haiku-5-5",
        reasoning_effort=effort,
    )
    assert saved_logs[0].status == "success", saved_logs[0].error
    assert len(requests) == 1
    log = read_eval_log(saved_logs[0].location)
    config = log.eval.model_generate_config
    assert config.reasoning_effort is None
    assert config.effort is None
    assert "thinking" not in requests[0]
    if effort is None:
        assert "output_config" not in requests[0]
        assert config.extra_body is None
        assert "extra_body" not in log.eval.model_args
    else:
        payload = {"output_config": {"effort": effort}}
        assert requests[0]["output_config"] == payload["output_config"]
        assert config.extra_body == payload
        if "output_config" not in anthropic_provider.anthropic_extra_body_fields():
            assert log.eval.model_args["extra_body"] == payload
        # completion_config only retains native generation fields on supported adapters.
        adapter = anthropic_provider.AnthropicAPI(
            "claude-haiku-5-5", api_key="offline-dummy-key"
        )
        params, _, _, _ = adapter.completion_config(
            GenerateConfig(max_tokens=1024, extra_body=payload)
        )
        if "output_config" in anthropic_provider.anthropic_extra_body_fields():
            assert params["output_config"] == payload["output_config"]
        else:
            assert "output_config" not in params
        assert "thinking" not in params

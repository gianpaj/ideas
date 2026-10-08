import csv
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scene_planning_bench import cli, inspect_runner
from scene_planning_bench.types import MatrixModelConfig


@pytest.mark.parametrize(
    "effort", [None, "none", "minimal", "low", "medium", "high", "xhigh"]
)
def test_matrix_accepts_reasoning_effort(effort: str | None) -> None:
    entry = MatrixModelConfig(model="openai/gpt-6-luna", reasoning_effort=effort)
    assert entry.reasoning_effort == effort


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
    )
    env = tmp_path / ".env"
    env.write_text("")
    output = tmp_path / "output"
    cli.run_matrix(matrix, output_dir=output, env_file=env, repeats=3)

    assert captured[0]["reasoning_effort"] == "low"
    assert "reasoning_effort" not in captured[1]
    for filename in ("matrix_summary.csv", "matrix_leaderboard.csv"):
        rows = {r["label"]: r for r in csv.DictReader((output / filename).open())}
        assert rows["luna-low"]["reasoning_effort"] == "low"
        assert rows["luna-default"]["reasoning_effort"] == ""
    for label, expected in (("luna-low", "low"), ("luna-default", None)):
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

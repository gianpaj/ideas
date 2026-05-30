from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from inspect_ai import Task, eval as inspect_eval
from inspect_ai.dataset import Sample
from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.model import ChatMessageSystem, ChatMessageUser, ModelOutput, ModelUsage
from inspect_ai.scorer import Score, Target, mean, scorer, stderr

from scene_planning_bench.evaluation import evaluate_output
from scene_planning_bench.prompts import build_prompt_bundle
from scene_planning_bench.registry import load_suite, load_tasks_from_suite, project_root
from scene_planning_bench.reports.json_report import write_run_reports
from scene_planning_bench.types import BenchmarkTask, RunResult
from scene_planning_bench.validation import load_schema
from scene_runtime import SceneDefinition

SCORER_NAME = "scene_plan_benchmark"


def _prompt_bundle_to_chat_messages(
    prompt_bundle: list[dict[str, str]],
) -> list[ChatMessageSystem | ChatMessageUser]:
    messages: list[ChatMessageSystem | ChatMessageUser] = []
    for message in prompt_bundle:
        if message["role"] == "system":
            messages.append(ChatMessageSystem(content=message["content"]))
        elif message["role"] == "user":
            messages.append(ChatMessageUser(content=message["content"]))
        else:
            raise ValueError(f"unsupported prompt role: {message['role']}")
    return messages


@scorer(metrics=[mean(), stderr()], name=SCORER_NAME)
def inspect_scene_plan_scorer(response_schema: dict[str, Any], adapter_name: str):
    async def score(state, target: Target) -> Score:
        task = BenchmarkTask.model_validate(state.metadata["task"])
        scene = SceneDefinition.model_validate(state.metadata["scene"])
        result = evaluate_output(
            task,
            scene,
            state.output.completion if state.output else "",
            adapter_name,
            response_schema,
            sample_id=str(state.sample_id),
            prompt_index=state.metadata.get("prompt_index"),
            repeat_index=state.metadata.get("repeat_index"),
            prompt_text=state.metadata.get("prompt_text"),
            prompt_bundle=state.metadata.get("prompt_bundle"),
        )
        return Score(
            value=result.total_score,
            answer=state.output.completion if state.output else "",
            explanation=f"Schema valid: {result.schema_valid}",
            metadata=result.model_dump(mode="json", exclude_none=True),
        )

    return score


def _build_dataset(
    suite_relative_path: str,
    response_schema: dict[str, Any],
    *,
    repeats: int = 1,
) -> tuple[str, list[Sample]]:
    if repeats < 1:
        raise ValueError("repeats must be at least 1")

    root = project_root()
    suite_path = root / suite_relative_path
    suite = load_suite(suite_path)
    loaded_tasks = load_tasks_from_suite(suite_path)
    samples: list[Sample] = []

    for loaded_task in loaded_tasks:
        for prompt_index, prompt_text in enumerate(loaded_task.task.prompts):
            for repeat_index in range(repeats):
                sample_id = _sample_id(
                    loaded_task.task.task_id,
                    prompt_index=prompt_index,
                    repeat_index=repeat_index,
                    repeats=repeats,
                )
                prompt_bundle = build_prompt_bundle(
                    suite.defaults.system_prompt,
                    loaded_task.scene,
                    loaded_task.task,
                    response_schema,
                    prompt_text,
                )
                samples.append(
                    Sample(
                        id=sample_id,
                        input=_prompt_bundle_to_chat_messages(prompt_bundle),
                        target=json.dumps(
                            loaded_task.task.gold_response.model_dump(
                                mode="json",
                                exclude_none=True,
                            ),
                            sort_keys=True,
                        ),
                        metadata={
                            "task": loaded_task.task.model_dump(
                                mode="json",
                                exclude_none=True,
                            ),
                            "scene": loaded_task.scene.model_dump(
                                mode="json",
                                exclude_none=True,
                            ),
                            "prompt_index": prompt_index,
                            "repeat_index": repeat_index,
                            "prompt_text": prompt_text,
                            "prompt_bundle": prompt_bundle,
                        },
                    )
                )

    return suite.suite_id, samples


def _mock_outputs_for_suite(
    suite_relative_path: str,
    *,
    repeats: int = 1,
) -> list[ModelOutput]:
    suite_path = project_root() / suite_relative_path
    loaded_tasks = load_tasks_from_suite(suite_path)
    outputs: list[ModelOutput] = []
    for loaded_task in loaded_tasks:
        for _prompt_index, _prompt_text in enumerate(loaded_task.task.prompts):
            for _repeat_index in range(repeats):
                outputs.append(
                    ModelOutput.from_content(
                        model="mockllm",
                        content=json.dumps(
                            loaded_task.task.gold_response.model_dump(
                                mode="json",
                                exclude_none=True,
                            ),
                            sort_keys=True,
                        ),
                    )
                )
    return outputs


def _run_results_from_logs(logs: list[EvalLog]) -> list[RunResult]:
    results: list[RunResult] = []
    for log in logs:
        log_status = getattr(log, "status", None)
        if log_status == "error":
            raise RuntimeError(
                f"inspect run failed: {_extract_log_error_message(log)}"
            )
        for sample in log.samples or []:
            results.append(_run_result_from_sample(sample, log.location))
    return results


def _extract_log_error_message(log: EvalLog) -> str:
    error = getattr(log, "error", None)
    if error is None:
        return "unknown Inspect error"
    if isinstance(error, dict):
        return str(error.get("message") or error)
    message = getattr(error, "message", None)
    if message:
        return str(message)
    return str(error)


def _run_result_from_sample(sample: EvalSample, log_location: str) -> RunResult:
    if sample.scores is None or SCORER_NAME not in sample.scores:
        sample_error = getattr(sample, "error", None)
        if sample_error:
            raise RuntimeError(
                f"inspect sample {sample.id} failed: {sample_error}"
            )
        raise ValueError(
            f"inspect sample {sample.id} did not contain {SCORER_NAME} score"
        )
    score = sample.scores[SCORER_NAME]
    if score.metadata is None:
        raise ValueError(f"inspect sample {sample.id} missing benchmark score metadata")
    payload = dict(score.metadata)
    payload["inspect_log_location"] = log_location
    payload.update(_extract_sample_metrics(sample))
    return RunResult.model_validate(payload)


def _extract_sample_metrics(sample: EvalSample) -> dict[str, Any]:
    usages = list(sample.model_usage.values())
    return {
        "total_time_seconds": sample.total_time,
        "working_time_seconds": sample.working_time,
        "input_tokens": _sum_usage_field(usages, "input_tokens"),
        "output_tokens": _sum_usage_field(usages, "output_tokens"),
        "total_tokens": _sum_usage_field(usages, "total_tokens"),
        "total_cost_usd": _sum_usage_field(usages, "total_cost"),
    }


def _sum_usage_field(
    usages: list[ModelUsage],
    field_name: str,
) -> int | float | None:
    values = [
        getattr(usage, field_name)
        for usage in usages
        if getattr(usage, field_name) is not None
    ]
    if not values:
        return None
    total = sum(values)
    if isinstance(total, float):
        return round(total, 8)
    return total


def run_suite_with_inspect(
    suite_relative_path: str,
    output_dir: Path,
    *,
    model: str,
    model_args: dict[str, Any] | None = None,
    repeats: int = 1,
) -> tuple[list[EvalLog], list[RunResult], Path]:
    root = project_root()
    suite_path = root / suite_relative_path
    suite = load_suite(suite_path)
    response_schema = load_schema(root / suite.defaults.response_schema_path)
    suite_id, dataset = _build_dataset(
        suite_relative_path,
        response_schema,
        repeats=repeats,
    )
    task = Task(
        name=f"{suite_id}_inspect",
        dataset=dataset,
        scorer=inspect_scene_plan_scorer(response_schema, adapter_name=model),
    )
    inspect_log_dir = output_dir / "inspect_logs"
    logs = inspect_eval(
        task,
        model=model,
        model_args=model_args or {},
        display="none",
        log_dir=str(inspect_log_dir),
        log_format="json",
        metadata={"suite_id": suite.suite_id},
    )
    results = _run_results_from_logs(logs)
    summary_path = write_run_reports(output_dir, results)
    return logs, results, summary_path


def run_suite_with_inspect_mock(
    suite_relative_path: str,
    output_dir: Path,
    *,
    repeats: int = 1,
) -> tuple[list[EvalLog], list[RunResult], Path]:
    return run_suite_with_inspect(
        suite_relative_path,
        output_dir,
        model="mockllm/scene-planning-bench",
        model_args={
            "custom_outputs": _mock_outputs_for_suite(
                suite_relative_path,
                repeats=repeats,
            )
        },
        repeats=repeats,
    )


def _sample_id(
    task_id: str,
    *,
    prompt_index: int,
    repeat_index: int,
    repeats: int,
) -> str:
    base = f"{task_id}::prompt_{prompt_index}"
    if repeats == 1:
        return base
    return f"{base}::repeat_{repeat_index}"

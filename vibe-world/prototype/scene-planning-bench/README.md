# Scene Planning Benchmark

Deterministic benchmark for evaluating whether an LLM can convert natural-language scene-editing requests into strict structured JSON plans.

## Scope

This prototype focuses on:

- schema compliance
- deterministic task and scene loading
- strict JSON validation
- prompt-bundle assembly with stored scene and schema context
- simple deterministic scoring
- mock-model execution for smoke testing
- Inspect-backed execution, logging, and replayable run artifacts
- JSON and CSV artifacts for comparison outside Inspect

Inspect is now used for one of the execution paths, while the scoring logic remains deterministic and local to this package.

Implementation notes for future agents live in [`AGENTS.md`](AGENTS.md).

## Commands

```bash
uv run scene-planning-bench validate-data
uv run scene-planning-bench run-mock
uv run scene-planning-bench run-inspect-mock
uv run scene-planning-bench run-inspect-model openai/gpt-5.4-mini
uv run scene-planning-bench compare-runs outputs/runs/<run-a>/summary.csv outputs/runs/<run-b>/summary.csv
uv run pytest
```

## Output layout

Runs now default to timestamped folders under `outputs/runs/`.

Each run writes:

- `summary.csv`
- `aggregate.json`
- `run_manifest.json`
- `tasks/*.json`
- `inspect_logs/*.json` for Inspect-backed runs

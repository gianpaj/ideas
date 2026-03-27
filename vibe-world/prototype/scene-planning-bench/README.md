# Scene Planning Benchmark

Deterministic benchmark for evaluating whether an LLM can convert natural-language scene-editing requests into strict structured JSON plans.

## Scope

This prototype focuses on:

- schema compliance
- deterministic task and scene loading
- strict JSON validation
- prompt-bundle assembly with stored scene and schema context
- reusable runtime extraction for parsing, schema validation, and prompt construction
- simple deterministic scoring
- mock-model execution for smoke testing
- Inspect-backed execution, logging, and replayable run artifacts
- JSON and CSV artifacts for comparison outside Inspect

Inspect is now used for one of the execution paths, while the scoring logic remains deterministic and local to this package.

The project now contains two Python packages under `src/`:

- `scene_planning_bench` for benchmark-specific loading, scoring, reporting, and CLI orchestration
- `scene_runtime` for reusable planning models, parsing, schema validation, prompt construction, normalization, and draft-render conversion

Implementation notes for future agents live in [`AGENTS.md`](AGENTS.md).

## Commands

```bash
uv run scene-planning-bench validate-data
uv run scene-planning-bench run-mock
uv run scene-planning-bench run-inspect-mock
uv run scene-planning-bench run-inspect-model openai/gpt-5.4-mini
uv run scene-planning-bench run-matrix configs/matrices/example_cross_provider.yaml
uv run scene-planning-bench compare-runs outputs/runs/<run-a>/summary.csv outputs/runs/<run-b>/summary.csv
uv run pytest
```

Provider runs load `.env` automatically if present. Start from [`.env.example`](./.env.example).

## Output layout

Runs now default to timestamped folders under `outputs/runs/`.

Each run writes:

- `summary.csv`
- `aggregate.json`
- `aggregate.json` includes per-task and per-paraphrase-group summaries
- `summary.csv` also includes per-sample latency, token usage, and optional cost fields for Inspect-backed runs
- `run_manifest.json`
- `tasks/*.json`
- `inspect_logs/*.json` for Inspect-backed runs

Matrix runs write combined artifacts under `outputs/matrices/`:

- `matrix_summary.csv`
- `matrix_leaderboard.csv`
- `matrix_manifest.json`
- `runs/<model-label>/...` per model

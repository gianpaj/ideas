# Scene Planning Benchmark

Deterministic benchmark for evaluating whether an LLM can convert natural-language scene-editing requests into strict structured JSON plans.

## Scope

This prototype focuses on:

- schema compliance
- deterministic task and scene loading
- strict JSON validation
- simple deterministic scoring
- mock-model execution for smoke testing
- JSON and CSV artifacts

Inspect integration is layered on top of this core runner, not baked into scoring.

## Commands

```bash
uv run scene-planning-bench validate-data
uv run scene-planning-bench run-mock
uv run scene-planning-bench compare-runs outputs/latest/summary.csv outputs/previous/summary.csv
uv run pytest
```

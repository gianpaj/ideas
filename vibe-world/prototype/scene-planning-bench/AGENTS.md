# Scene Planning Benchmark — Local Notes

This subproject is the first real implementation artifact inside `vibe-world`.

## Purpose

Use this package to benchmark the scene-planning layer only:

- natural-language scene edit request in
- strict JSON scene plan out
- deterministic validation and scoring
- Inspect-backed execution logs for reproducibility

It is not the multiplayer game and it is not the authoritative Vibe World backend.

## Working rules

- keep benchmark-specific code inside `src/scene_planning_bench/`
- keep reusable planning/runtime code inside `src/scene_runtime/`
- keep benchmark data in `tasks/`, `scenes/`, `schemas/`, and `configs/`
- keep `README.md` current when commands or outputs change
- prefer extending schemas and tests together
- treat prompt bundles and saved run artifacts as part of reproducibility, not optional extras
- per-sample task artifacts should preserve both benchmark-facing outputs and runtime-layer outputs when available

## Useful commands

```bash
uv run scene-planning-bench validate-data
uv run scene-planning-bench run-mock
uv run scene-planning-bench run-inspect-mock
uv run pytest
```

## Expected next implementation layers

- benchmark consumption of normalized plans in saved run artifacts
- stronger normalization for more action types and richer product-facing IR
- richer scoring modules for ambiguity/state/spatial correctness

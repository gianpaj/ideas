# Scene Builder Benchmark — Local Notes

This subproject benchmarks the builder layer only:

- normalized scene plan in
- deterministic builder spec out
- schema and semantic validation
- continuity checks for refine/remix

It is not the renderer, not the multiplayer backend, and not an LLM runner.

## Working rules

- keep benchmark-specific code inside `src/scene_builder_bench/`
- keep reusable builder/runtime code inside `src/scene_builder_runtime/`
- keep benchmark data in `fixtures/`, `tasks/`, `schemas/`, and `configs/`
- prefer deterministic local fixtures over live upstream dependencies
- keep `README.md` current when commands or outputs change
- extend schemas and tests together

## Useful commands

```bash
uv run scene-builder-bench validate-data
uv run scene-builder-bench run-local
uv run pytest
```

# Scene Builder Benchmark

Deterministic benchmark scaffold for validating whether a normalized Vibe World scene plan can be converted into a stable `BuilderSpec`.

## Scope

This prototype focuses on:

- checked-in normalized-plan fixtures
- deterministic builder-spec generation
- schema validation
- semantic validation
- continuity checks for `refine`
- local-only execution and reproducible outputs

It does not yet include:

- LLM execution
- reducer simulation
- rendered output comparisons
- multiplayer state

## Commands

```bash
uv run scene-builder-bench validate-data
uv run scene-builder-bench run-local
uv run pytest
```

## Package layout

- `src/scene_builder_runtime/` — reusable builder contracts, canonicalization, validation, and local deterministic builder
- `src/scene_builder_bench/` — benchmark loader, runner, evaluation, CLI, and reports
- `fixtures/` — normalized plans and prior builder specs used as deterministic inputs
- `tasks/` — benchmark task definitions
- `schemas/` — task, suite, and builder output schemas

## Current fixture set

- `add_pine_tree_left_of_cabin_001`
- `three_red_barrels_around_campfire_001`
- `refine_tree_soft_glow_001`

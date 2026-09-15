# Scene Builder Benchmark

Benchmark for comparing deterministic and LLM-backed conversion of normalized Vibe World scene plans into `BuilderSpec` output.

## Scope

This prototype focuses on:

- checked-in normalized-plan fixtures
- deterministic builder-spec generation
- schema validation
- semantic validation
- continuity checks for `refine`
- local deterministic execution and reproducible outputs
- an optional cloud-model matrix

It does not include:

- reducer simulation
- rendered output comparisons
- multiplayer state

## Commands

```bash
uv run scene-builder-bench validate-data
uv run scene-builder-bench run-local
uv run scene-builder-bench run-matrix configs/matrices/cloud_providers.yaml
uv run pytest
```

The cloud matrix runs Mercury 2.5 first, followed by Gemini, Claude, and GPT.
Set the credentials for the providers you want to compare in
this directory's `.env` file or your shell:

```bash
INCEPTION_API_KEY=...
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
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

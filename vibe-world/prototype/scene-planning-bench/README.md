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

## Artifact types

Each task declares a `target_artifact` describing which JSON contract the model must produce. Three artifacts are supported, mirroring the scene-runtime-demo pipeline:

- `scene_actions` — the high-level `ScenePlanningResponse` (actions, clarifications, refusals). Schema: `schemas/response.schema.json`. Gold lives in `gold_response`.
- `builder` — the mid-level `BuilderSpec` (parts + instances + placement IR). Schema: `schemas/builder.schema.json`. Gold lives in `gold_builder`.
- `voxel_builder` — the low-level `VoxelBuilderSpec` (discrete ops: `add_box`, `add_sphere`, `add_line`, `paint_region`, `rotate_region`, `clone_region`). Schema: `schemas/voxel_builder.schema.json`. Gold lives in `gold_voxel_builder`.
- `voxel_core` — the production "creative core" the game's object-generation call authors (mirrors `voxelCoreSchema` in `@3dvibegame/ai-planning`). Schema: `schemas/voxel_core.schema.json`. **Constraint-scored** (not gold-reference) so wins port back to the shipped prompt; `gold_voxel_core` is only the mock fixture. See `configs/suites/v1_voxel_core.yaml` — its `system_prompt` is the shipped voxel-builder prompt verbatim.

Scoring reuses the four-component profile (schema validity, action/operation type, argument match, spatial match) across all three artifacts. For builder/voxel tasks, subscores (e.g. `part_primitive_match`, `op_kind_match`, `material_set_match`) are surfaced via `artifact_subscores` on each `RunResult` and mapped onto the headline `action_type_score`, `argument_match_score`, and `spatial_match_score` fields so reports stay uniform.

Inspect is now used for one of the execution paths, while the scoring logic remains deterministic and local to this package.

The project now contains two Python packages under `src/`:

- `scene_planning_bench` for benchmark-specific loading, scoring, reporting, and CLI orchestration
- `scene_runtime` for reusable planning models, parsing, schema validation, prompt construction, normalization, and draft-render conversion

Implementation notes for future agents live in [`AGENTS.md`](AGENTS.md).

## Quick start

This benchmark is its own Python project under `prototype/scene-planning-bench`.
`uv run` only exposes the `scene-planning-bench` CLI when you run it from that
folder, or when you point `uv` at that folder explicitly.

If you run from `vibe-world/`, `uv` does not see a `pyproject.toml` for this
package. If you run from `prototype/scene-builder-bench/`, you are in the wrong
sibling project, which exposes `scene-builder-bench`, not
`scene-planning-bench`.

### Option A: run from the package root

```bash
cd prototype/scene-planning-bench
uv run scene-planning-bench validate-data
uv run scene-planning-bench run-mock
uv run scene-planning-bench run-inspect-mock
uv run scene-planning-bench run-matrix configs/matrices/example_cross_provider.yaml
```

### Option B: run from `vibe-world/`

```bash
uv run --directory prototype/scene-planning-bench scene-planning-bench validate-data
uv run --directory prototype/scene-planning-bench scene-planning-bench run-mock
uv run --directory prototype/scene-planning-bench scene-planning-bench run-inspect-mock
uv run --directory prototype/scene-planning-bench scene-planning-bench run-matrix configs/matrices/example_cross_provider.yaml
```

### Fast smoke test

```bash
cd prototype/scene-planning-bench
uv run scene-planning-bench validate-data
uv run scene-planning-bench run-mock
```

### Provider runs

Matrix and provider-backed Inspect runs need the right API keys in `.env` (or in
your shell environment). Provider runs load `.env` automatically if present.
Start from `.env.example`.

## Commands

From `prototype/scene-planning-bench`:

```bash
uv run scene-planning-bench validate-data
uv run scene-planning-bench validate-data --suite configs/suites/v1_all_artifacts.yaml
uv run scene-planning-bench run-mock
uv run scene-planning-bench run-mock --suite configs/suites/v1_builder.yaml
uv run scene-planning-bench run-mock --suite configs/suites/v1_voxel_builder.yaml
uv run scene-planning-bench run-mock --suite configs/suites/v1_voxel_core.yaml
uv run scene-planning-bench run-inspect-model google/gemini-2.5-flash --suite configs/suites/v1_voxel_core.yaml
uv run scene-planning-bench run-mock --suite configs/suites/v1_all_artifacts.yaml
uv run scene-planning-bench run-inspect-mock
uv run scene-planning-bench run-inspect-model openai/gpt-5.4-mini
uv run scene-planning-bench run-inspect-model openai/gpt-5.4-mini --repeats 3
uv run scene-planning-bench run-inspect-model google/gemini-2.5-flash
uv run scene-planning-bench run-matrix configs/matrices/example_cross_provider.yaml
uv run scene-planning-bench compare-runs outputs/runs/<run-a>/summary.csv outputs/runs/<run-b>/summary.csv
uv run pytest
```

Available suites:

- `configs/suites/v1_core.yaml` — scene_actions baseline
- `configs/suites/v1_builder.yaml` — builder-spec tasks
- `configs/suites/v1_voxel_builder.yaml` — voxel-builder tasks
- `configs/suites/v1_voxel_core.yaml` — production object-generation prompt (constraint-scored core)
- `configs/suites/v1_all_artifacts.yaml` — all three artifact types combined

Provider runs load `.env` automatically if present. Start from [`.env.example`](./.env.example).

Commands default to `configs/suites/v1_dev.yaml`, the public development split for prompt tuning and routine model checks. Run the committed holdout split explicitly when you want a final comparison:

```bash
uv run scene-planning-bench run-matrix configs/matrices/example_cross_provider.yaml --repeats 3
uv run scene-planning-bench run-inspect-model openai/gpt-5.4-mini --suite configs/suites/v1_hidden.yaml --repeats 3
```

`configs/suites/v1_core.yaml` remains the combined compatibility suite.

## Output layout

Runs now default to timestamped folders under `outputs/runs/`.

Each run writes:

- `summary.csv`
- `aggregate.json`
- `aggregate.json` includes per-task and per-paraphrase-group summaries
- `aggregate.json` includes score standard deviation, standard error, and 95% confidence interval fields when repeated samples are present
- `summary.csv` also includes per-sample latency, token usage, optional cost fields, and runtime artifact counts
- `run_manifest.json`
- `tasks/*.json` with raw output, parsed response, normalized plan, render drafts, and diagnostics
- `inspect_logs/*.json` for Inspect-backed runs

Matrix runs write combined artifacts under `outputs/matrices/`:

- `matrix_summary.csv`
- `matrix_leaderboard.csv`
- `matrix_manifest.json`
- `runs/<model-label>/...` per model

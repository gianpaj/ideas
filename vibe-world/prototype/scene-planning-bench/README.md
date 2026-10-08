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

Scoring reuses the four-component profile (schema validity, action/operation type, argument match, spatial match) across all three artifacts. For builder/voxel tasks, subscores (e.g. `part_primitive_match`, `op_kind_match`, `material_set_match`) are surfaced via `artifact_subscores` on each `RunResult` and mapped onto the headline `action_type_score`, `argument_match_score`, and `spatial_match_score` fields so reports stay uniform.

Inspect is now used for one of the execution paths, while the scoring logic remains deterministic and local to this package.

The project now contains two Python packages under `src/`:

- `scene_planning_bench` for benchmark-specific loading, scoring, reporting, and CLI orchestration
- `scene_runtime` for reusable planning models, parsing, schema validation, prompt construction, normalization, and draft-render conversion

Implementation notes for future agents live in [`AGENTS.md`](AGENTS.md).

## Commands

```bash
uv run scene-planning-bench validate-data
uv run scene-planning-bench validate-data --suite configs/suites/v1_all_artifacts.yaml
uv run scene-planning-bench run-mock
uv run scene-planning-bench run-mock --suite configs/suites/v1_builder.yaml
uv run scene-planning-bench run-mock --suite configs/suites/v1_voxel_builder.yaml
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
- `configs/suites/v1_dev_gemini.yaml` — development tasks with explicit cardinality for Gemini prompt tuning
- `configs/suites/v1_builder.yaml` — builder-spec tasks
- `configs/suites/v1_voxel_builder.yaml` — voxel-builder tasks
- `configs/suites/v1_all_artifacts.yaml` — all three artifact types combined

Provider runs load `.env` automatically if present. Start from [`.env.example`](./.env.example).

Commands default to `configs/suites/v1_dev.yaml`, the public development split for prompt tuning and routine model checks. Run the committed holdout split explicitly when you want a final comparison:

```bash
uv run scene-planning-bench run-matrix configs/matrices/example_cross_provider.yaml --repeats 3
uv run scene-planning-bench run-inspect-model openai/gpt-5.4-mini --suite configs/suites/v1_hidden.yaml --repeats 3
```

`configs/suites/v1_core.yaml` remains the combined compatibility suite.

## Results: cross-provider development suite (2026-10-08)

Run from this package directory:

```bash
uv run scene-planning-bench run-matrix configs/matrices/example_cross_provider.yaml --repeats 3
```

Suite: `configs/suites/v1_dev.yaml`. Six models each answered two `scene_actions` tasks three times: six samples per model, 36 samples total. All model runs succeeded, and all samples passed schema validation.

Artifacts: `outputs/matrices/2026-10-08T17-56-56Z_v1-dev_example-cross-provider/`. Scores and mean latency come from `matrix_leaderboard.csv`; perfect-sample counts and median latency come from each model's `runs/<model-label>/summary.csv`.

| Model                 | Mean score | Perfect samples | Mean latency | Median latency |
| --------------------- | ---------: | --------------: | -----------: | -------------: |
| Claude Haiku 5.5      |       100% |             6/6 |       2.30 s |         2.31 s |
| Gemma 4 26B A4B       |       100% |             6/6 |      18.32 s |         7.96 s |
| Gemma 4 31B           |     97.78% |             5/6 |      41.40 s |        22.31 s |
| Gemini 3.1 Flash Lite |     93.33% |             3/6 |       1.62 s |         1.53 s |
| Claude Haiku 4.5      |     93.33% |             3/6 |       3.71 s |         3.73 s |
| Gemini 2.5 Flash      |     93.33% |             3/6 |       4.83 s |         5.48 s |

### Score interpretation

Every model scored 100% on `three_red_barrels_around_campfire_001` in every repeat. The score differences came from `add_pine_tree_left_of_cabin_001`:

- Haiku 5.5 and Gemma 26B included `attributes.count: 1` in all three responses.
- Haiku 4.5 and both Gemini models omitted `count` in all three responses, scoring 86.67% on the task.
- Gemma 31B included `count: 1` in two responses and omitted it in one.

The scorer checks count in both argument matching and spatial matching. A lower spatial score therefore does not by itself indicate incorrect placement. Whether an omitted count is equivalent to one object depends on runtime semantics, which this comparison does not establish.

### Latency and limits

Haiku 5.5 scored perfectly across six samples with latency between 2.15 and 2.42 seconds. Flash Lite had the lowest mean latency. Gemma 26B and Gemma 31B each had a large latency outlier: 66.94 and 133.68 seconds, respectively. Their mean working times were 8.38 and 23.17 seconds; the cause of the gap between total and working time is unverified.

These results measure repeatability on two development tasks, not performance across a broad task set or the builder and voxel-builder artifacts. Perfect scores on six samples do not establish general reliability. Cost fields are empty, so `score_per_dollar_rank` is not meaningful for this run.

## Gemini prompt tuning (2026-10-08)

[`configs/suites/v1_dev_gemini.yaml`](configs/suites/v1_dev_gemini.yaml) uses the same tasks and schemas as `v1_dev.yaml`, with one additional system-prompt rule:

> For a single-object action, set attributes.count to 1; do not omit it or use null. For spawn_layout, set attributes.count to the requested number of objects.

The original development suite, gold responses, scoring, and hidden split remain unchanged. The rule makes cardinality explicit rather than changing how outputs are scored.

Run from this package directory:

```bash
uv run scene-planning-bench validate-data --suite configs/suites/v1_dev_gemini.yaml
uv run scene-planning-bench run-inspect-model google/gemini-3.1-flash-lite --suite configs/suites/v1_dev_gemini.yaml --repeats 3
```

Gemini 3.1 Flash Lite scored 100% in both the initial tuned batch and a separate confirmation batch, with no further prompt revisions:

| Run                                      | Mean score | Perfect samples | Mean latency | Median latency |
| ---------------------------------------- | ---------: | --------------: | -----------: | -------------: |
| Original prompt, Gemini-only matrix      |     95.56% |             4/6 |       1.65 s |         1.52 s |
| Explicit cardinality, initial batch      |       100% |             6/6 |       1.82 s |         1.86 s |
| Explicit cardinality, confirmation batch |       100% |             6/6 |       1.90 s |         2.00 s |

Artifacts under `outputs/`:

- Baseline: `matrices/2026-10-08T18-11-20Z_v1-dev_example-cross-provider/runs/gemini-3.1-flash-lite/`
- Initial tuned batch: `runs/2026-10-08T18-13-53Z_v1-dev-gemini_google-gemini-3-1-flash-lite/`
- Confirmation batch: `runs/2026-10-08T18-14-08Z_v1-dev-gemini_google-gemini-3-1-flash-lite/`

All 12 tuned samples passed schema validation and scored perfectly. Every pine-tree response included `count: 1`; every barrel response included `count: 3` and `layout: "triangle"`. The baseline included the pine-tree count in only one of three repeats.

These are sequential runs on two development tasks, not a controlled latency comparison or evidence of general reliability. Gemini 2.5 Flash and Gemini 3.5 Flash Lite have not been tested with this tuned suite.

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

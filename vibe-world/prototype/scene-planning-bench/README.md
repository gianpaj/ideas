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

Each task declares a `target_artifact` describing which JSON contract the model must produce. Four artifacts are supported:

- `scene_actions` — the high-level `ScenePlanningResponse` (actions, clarifications, refusals). Schema: `schemas/response.schema.json`. Gold lives in `gold_response`.
- `builder` — the mid-level `BuilderSpec` (parts + instances + placement IR). Schema: `schemas/builder.schema.json`. Gold lives in `gold_builder`.
- `voxel_builder` — the low-level `VoxelBuilderSpec` (discrete ops: `add_box`, `add_sphere`, `add_line`, `paint_region`, `rotate_region`, `clone_region`). Schema: `schemas/voxel_builder.schema.json`. Gold lives in `gold_voxel_builder`.
- `voxel_core` — the production "creative core" the game's object-generation call authors (mirrors `voxelCoreSchema` in `@3dvibegame/ai-planning`). Schema: `schemas/voxel_core.schema.json`. **Constraint-scored** (not gold-reference) so wins port back to the shipped prompt; `gold_voxel_core` is only the mock fixture. See `configs/suites/v1_voxel_core.yaml` — its `system_prompt` is the shipped voxel-builder prompt verbatim.

Scoring reuses the four-component profile (schema validity, action/operation type, argument match, spatial match) across all four artifacts. For builder/voxel tasks, subscores (e.g. `part_primitive_match`, `op_kind_match`, `material_set_match`) are surfaced via `artifact_subscores` on each `RunResult` and mapped onto the headline `action_type_score`, `argument_match_score`, and `spatial_match_score` fields so reports stay uniform.

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
- `configs/suites/v1_dev.yaml` — public development tasks with explicit cardinality for all models
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

## Game object-generation comparison

[`configs/matrices/voxel_core_models.yaml`](configs/matrices/voxel_core_models.yaml) compares Mercury 2.5 against the game's Gemini 2.5 Flash baseline, Gemini 3.5 Flash Lite, Gemini 3.1 Flash Lite, Claude Haiku 5.5, and GPT-6 Luna with requested reasoning effort `none`. Mercury runs first. The suite uses the game's v3 object-generation prompt and `Player prompt: …` input format; models author voxel geometry rather than high-level scene actions.

Run from this package directory:

```bash
uv run scene-planning-bench validate-data --suite configs/suites/v1_voxel_core.yaml
uv run scene-planning-bench run-matrix configs/matrices/voxel_core_models.yaml --repeats 3
```

Set `INCEPTION_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, and `OPENAI_API_KEY` in this package's `.env` or your shell. This run sends task prompts to the providers and incurs API charges. Six tasks with three repeats produce 18 samples per model, 108 total. Results are saved under `outputs/matrices/<timestamp>_v1-voxel-core_voxel-core-models/`.

The comparison candidates come from the scene-action results below, not measured voxel-generation performance. Re-evaluate quality and latency on this suite. Its rubric checks structural constraints, not rendered visual quality, and the Inspect runner does not establish identical generation settings to the game's Gemini client. GPT-6's requested `none` setting does not guarantee zero reasoning tokens; check saved usage.

### Results: voxel-core comparison (2026-10-08)

Artifacts: `outputs/matrices/2026-10-08T19-25-20Z_v1-voxel-core_voxel-core-models/`. All six model runs succeeded. Each model answered six tasks three times; all 108 samples passed schema validation.

| Model                 | Mean score | Perfect samples | Mean latency | Median latency |
| --------------------- | ---------: | --------------: | -----------: | -------------: |
| Mercury 2.5           |     98.86% |           16/18 |       5.72 s |         5.87 s |
| Gemini 3.5 Flash Lite |     97.35% |           11/18 |       2.03 s |         2.12 s |
| GPT-6 Luna `none`     |     97.20% |           10/18 |       6.98 s |         7.18 s |
| Gemini 2.5 Flash      |     96.99% |           11/18 |      11.25 s |        10.89 s |
| Gemini 3.1 Flash Lite |     96.59% |           11/18 |       1.85 s |         2.01 s |
| Claude Haiku 5.5      |     96.25% |            9/18 |       5.80 s |         6.31 s |

Scores and mean latency come from `matrix_summary.csv`; perfect counts and medians come from each model's `summary.csv`. Latency is total sample time, including the rejection task.

Mercury had the highest observed rubric score and about 49% lower mean latency than the Gemini 2.5 Flash baseline. Gemini 3.1 Flash Lite was fastest by mean latency; Gemini 3.5 Flash Lite traded about 10% higher mean latency for a higher observed score. The score confidence intervals overlap, and six tasks with three repeats do not establish a general quality winner or reliable tail latency. Structural scores are not a visual-quality assessment. Cost fields are empty, so this run cannot establish value per dollar.

## OpenAI reasoning effort in matrices

OpenAI matrix entries accept an optional `reasoning_effort` generation setting:

```yaml
models:
  - model: openai/gpt-6-luna
    label: gpt-6-luna-low
    reasoning_effort: low
  - model: openai/gpt-6-luna
    label: gpt-6-luna-medium
    reasoning_effort: medium
```

Omit the field or set it to null to use the provider default. The benchmark accepts `none`, `minimal`, `low`, `medium`, `high`, and `xhigh`; support varies by model, and the API rejects unsupported choices. This field is restricted to `openai/` entries. Gemini thinking levels and Anthropic thinking controls are not configured through this field.

Use distinct labels for each model/effort combination so artifacts have separate directories. The example matrix compares GPT-6 Luna at `low`, `minimal`, and `none`, and GPT-5.6 Luna at `low` and `none`. GPT-5.6 Luna rejects `minimal`. Run it with:

```bash
uv run scene-planning-bench run-matrix configs/matrices/example_cross_provider.yaml --repeats 3
```

The runner passes effort as an Inspect generation setting, not a provider initialization argument. Run manifests, matrix summaries, and leaderboards record the requested `reasoning_effort`; null or blank means provider default, not reasoning disabled. Inspect logs preserve the generation configuration. `run-inspect-model` without a matrix continues to use provider defaults.

The five-model repeated comparison below uses provider defaults; the OpenAI effort comparison records explicit settings. Changing effort can affect latency, token usage, cost, and quality; compare runs before choosing a setting.

## Results: baseline prompt (2026-10-08)

This saved baseline run uses a prompt without the explicit-cardinality rule in the current `configs/suites/v1_dev.yaml`. It covers six models and two `scene_actions` tasks with three repeats: six samples per model, 36 samples total. All model runs succeeded, and all samples passed schema validation. This baseline does not include Gemini 3.5 Flash Lite.

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

## Explicit cardinality (2026-10-08)

[`configs/suites/v1_dev.yaml`](configs/suites/v1_dev.yaml) applies this system-prompt rule to all models:

> For a single-object action, set attributes.count to 1; do not omit it or use null. For spawn_layout, set attributes.count to the requested number of objects.

The rule makes cardinality explicit without changing the task set, schemas, gold responses, scoring, or hidden split. The cross-provider matrix uses this development suite.

Run from this package directory:

```bash
uv run scene-planning-bench validate-data
uv run scene-planning-bench run-inspect-model google/gemini-3.1-flash-lite --repeats 3
uv run scene-planning-bench run-matrix configs/matrices/example_cross_provider.yaml --repeats 3
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

### Cross-provider check

The explicit-cardinality prompt scored 100% for all seven unique models in `outputs/matrices/2026-10-08T18-26-09Z_v1-dev-gemini_example-cross-provider/`. Every saved sample passed schema validation; every pine-tree response included `count: 1`.

| Model                 | Mean score | Perfect samples | Mean latency |
| --------------------- | ---------: | --------------: | -----------: |
| Gemini 3.5 Flash Lite |       100% |             2/2 |       1.53 s |
| Gemini 3.1 Flash Lite |       100% |             2/2 |       1.61 s |
| Claude Haiku 5.5      |       100% |             2/2 |       1.91 s |
| Claude Haiku 4.5      |       100% |             2/2 |       3.40 s |
| Gemini 2.5 Flash      |       100% |             2/2 |       5.00 s |
| Gemma 4 26B A4B       |       100% |             2/2 |      17.63 s |
| Gemma 4 31B           |       100% |             2/2 |      23.29 s |

This saved matrix used one repeat per task and contains two Gemini 3.5 entries sharing an output directory. Both summary rows scored 100% with a 1.53-second mean latency; the table lists the model once. The current matrix has unique labels.

The `v1-dev-gemini` artifact names identify the saved runs, not a separate suite required to execute the commands above. These results cover only two development tasks. They are not a controlled latency comparison or evidence of general reliability; cost fields are empty, so dollar rankings are not meaningful.

## Results: five-model repeated comparison (2026-10-08)

Run from this package directory:

```bash
uv run scene-planning-bench run-matrix configs/matrices/example_cross_provider.yaml --repeats 3
```

Artifacts: `outputs/matrices/2026-10-08T18-38-26Z_v1-dev_example-cross-provider/`. Five models each answered two development tasks three times: six samples per model, 30 samples total. All runs succeeded, and all 30 samples passed schema validation and scored 100%.

| Model                 | Mean score | Perfect samples | Mean latency | Median latency | Latency range |
| --------------------- | ---------: | --------------: | -----------: | -------------: | ------------: |
| Gemini 3.5 Flash Lite |       100% |             6/6 |       1.50 s |         1.48 s |   1.39–1.69 s |
| Gemini 3.1 Flash Lite |       100% |             6/6 |       1.61 s |         1.66 s |   1.37–1.86 s |
| Claude Haiku 5.5      |       100% |             6/6 |       2.10 s |         2.38 s |   1.45–2.45 s |
| GPT-6 Luna            |       100% |             6/6 |       3.55 s |         3.65 s |   2.67–4.03 s |
| GPT-5.6 Luna          |       100% |             6/6 |       5.66 s |         5.62 s |   5.03–6.42 s |

Scores and mean latency come from `matrix_summary.csv`; medians and ranges come from each model's `summary.csv`. Latency is total sample time, not just working time. GPT-5.6 Luna's mean working time was 3.58 seconds, versus 5.66 seconds total; the cause of that gap is unverified.

### OpenAI reasoning settings

OpenAI's [reasoning guide](https://developers.openai.com/api/docs/guides/reasoning.md#reasoning-mode), checked on 2026-10-08, documents `medium` reasoning effort as the default for GPT-5.6 models and GPT-6 Luna. It also documents `standard` as the default reasoning mode in the Responses API. Reasoning is enabled by default for these models, not disabled merely because no setting is supplied.

Both saved OpenAI Inspect logs have empty `model_generate_config` and `model_args`, with no explicit reasoning override. The run therefore uses provider defaults rather than an explicitly pinned effort. The logs confirm nonzero reasoning usage in every OpenAI sample:

| Model        | Total reasoning tokens across six samples | Per-sample range |
| ------------ | ----------------------------------------: | ---------------: |
| GPT-6 Luna   |                                       443 |            56–87 |
| GPT-5.6 Luna |                                       421 |            59–77 |

These counts come from `inspect_logs/*.json`, not the benchmark summary CSV. OpenAI bills reasoning tokens as output tokens; they are already included in output usage and must not be added twice when estimating cost.

### Interpretation and limits

Gemini 3.5 Flash Lite had the lowest observed mean latency, about 7% below Gemini 3.1 Flash Lite. Their latency ranges overlap, and six samples per model are too few to establish a reliable speed advantage or tail-latency estimate. The OpenAI models showed no scored quality advantage on these two tasks while taking longer under their default reasoning settings.

This suite reaches its scoring ceiling for all five models. More development tasks are needed to distinguish quality; repeated perfect scores on these two prompts do not establish general reliability. Cost fields remain empty, so this comparison cannot establish value per dollar.

## Results: OpenAI effort comparison (2026-10-08)

Artifacts: `outputs/matrices/2026-10-08T18-56-52Z_v1-dev_example-cross-provider/`. Five configurations each answered two development tasks three times. All 30 samples passed schema validation and scored 100%. Each configuration has a unique label and a separate artifact directory.

| Model        | Requested effort | Perfect samples | Mean latency | Median latency | Total reasoning tokens |
| ------------ | ---------------- | --------------: | -----------: | -------------: | ---------------------: |
| GPT-6 Luna   | `low`            |             6/6 |       3.66 s |         3.61 s |                    396 |
| GPT-6 Luna   | `minimal`        |             6/6 |       3.06 s |         2.62 s |                    357 |
| GPT-6 Luna   | `none`           |             6/6 |       2.92 s |         2.89 s |                    429 |
| GPT-5.6 Luna | `low`            |             6/6 |       4.11 s |         3.70 s |                     52 |
| GPT-5.6 Luna | `none`           |             6/6 |       3.18 s |         3.15 s |                      0 |

Scores and mean latency come from `matrix_summary.csv`; medians come from per-configuration summaries. Reasoning totals come from Inspect logs and cover six samples each. The logs confirm every requested effort setting. All five configurations report the same cached-input total: 15,261 tokens.

GPT-5.6 Luna reported zero reasoning tokens in every `none` sample. At `low`, it reported zero in five samples and 52 in one. GPT-6 Luna reported reasoning tokens in every `none` sample, totaling 429. Its requested `none` setting therefore does not establish reasoning-disabled execution; the cause of the nonzero usage is unresolved.

GPT-6 Luna `none` had about 8% lower mean latency than GPT-5.6 Luna `none`, with the same perfect score. GPT-6 `minimal` had the lowest median, but a 5.87-second sample increased its mean above `none`. These are small, sequential samples, not reliable tail-latency estimates.

### Price-based comparison

The following rates were supplied by the user on 2026-10-08 and have not been independently verified:

| Model        | Input / 1M tokens | Output / 1M tokens |
| ------------ | ----------------: | -----------------: |
| GPT-6 Luna   |             $0.10 |              $0.50 |
| GPT-5.6 Luna |             $0.20 |              $1.20 |

At these rates, GPT-6 Luna has 50% lower input pricing and about 58% lower output pricing. Its higher reported output usage does not erase the output-cost advantage in the `none` comparison:

| Configuration       | Output tokens across six samples | Estimated output cost |
| ------------------- | -------------------------------: | --------------------: |
| GPT-6 Luna `none`   |                            1,411 |             $0.000706 |
| GPT-5.6 Luna `none` |                              963 |             $0.001156 |

Output estimates use `output_tokens × output_rate / 1,000,000`. Reasoning tokens are included in output usage and must not be added again. These estimates exclude input cost because most input tokens were cached and cached-input rates were not supplied. They are not total billing estimates and do not populate the benchmark's cost fields or dollar rankings.

For these two tasks and the supplied prices, GPT-6 Luna `none` is the stronger observed candidate than GPT-5.6 Luna `none`: identical scores, lower mean and median latency, and lower estimated output cost. The unresolved GPT-6 reasoning usage and the narrow task coverage limit this conclusion; broader development tasks are needed before choosing a general default.

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

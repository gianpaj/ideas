# Scene Planning Benchmark — Local Notes

This subproject is the first real implementation artifact inside `vibe-world`.

## Purpose

Use this package to benchmark the scene-planning layer only:

- natural-language scene edit request in
- strict JSON scene plan out
- deterministic validation and scoring
- spatial, action, argument, and schema scoring
- Inspect-backed execution logs for reproducibility
- repeated model runs with aggregate uncertainty metrics

It is not the multiplayer game and it is not the authoritative Vibe World backend.

## Benchmark splits

Default commands use `configs/suites/v1_dev.yaml`, the public development split for prompt tuning and routine model checks.

Use `configs/suites/v1_hidden.yaml` explicitly for committed holdout checks. Do not tune prompts directly against the hidden split.

`configs/suites/v1_core.yaml` remains the combined compatibility suite.

## Artifact types

Each task declares a `target_artifact` and the benchmark dispatches on it:

- `scene_actions` — `ScenePlanningResponse`, gold stored in `gold_response`
- `builder` — `BuilderSpec`, gold stored in `gold_builder`
- `voxel_builder` — `VoxelBuilderSpec`, gold stored in `gold_voxel_builder`
- `voxel_core` — `VoxelCoreSpec`, the production "creative core" the game's Gemini
  call authors (mirrors `voxelCoreSchema` in `@3dvibegame/ai-planning`). Scored by
  a **constraint rubric**, not gold reference, so wins port back to the shipped
  object-generation prompt. `gold_voxel_core` is only a canned fixture for the mock
  adapter (a `{"rejection": ...}` fixture is allowed). `metadata.voxel_profile`
  selects `object` (default) or `reject` behavior. The suite's `system_prompt` is
  the shipped `voxelBuilderSystemPrompt` (PROMPT_VERSION) verbatim, and the prompt
  bundle is production-faithful (system + `Player prompt: …`, no scene/schema
  injection — see `scene_planning_bench/prompts.py`). Beyond schema compliance the
  rubric encodes quality defects mined from real prod 👎 feedback
  (`tasks/v1_voxel_core/feedback/`): `parts_connected` (no floating/disconnected
  parts), `lines_axis_aligned` (diagonal `add_line` falls back to a bounds box in
  the compiler), and `materials_unique` (a material_id declared twice collapses its
  colors). To add a task from new bad feedback: query `object_feedback` where
  `rating = 'down'`, drop the prompt + a corrected gold core under that folder, and
  add a check if it exposes a new defect class.

Pydantic models live in `src/scene_runtime/artifacts.py`; schemas in `schemas/builder.schema.json`, `schemas/voxel_builder.schema.json`, and `schemas/voxel_core.schema.json`. `SuiteDefaults` carries `builder_schema_path`, `voxel_builder_schema_path`, and `voxel_core_schema_path`; `load_artifact_schemas` returns a dict keyed by `ArtifactType`. Scoring modules: `scene_planning_bench.scoring.builder_score`, `scene_planning_bench.scoring.voxel_score`, and `scene_planning_bench.scoring.voxel_core_score` (rubric; its `assemble_envelope` mirrors the server's `assembleVoxelSpec` for the "compiles" hard-fail gate). `aggregate_artifact_score` averages non-schema subscores against the scoring profile's non-schema weight total.

When adding a new artifact type: add a Pydantic model + JSON schema, extend `ArtifactType` / `parse_artifact_json`, wire it through `BenchmarkTask.gold_payload`, `SuiteDefaults`, `load_artifact_schemas`, `evaluate_output`, and `build_artifact_prompt_bundle`, then add a scoring module.

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
uv run scene-planning-bench validate-data --suite configs/suites/v1_all_artifacts.yaml
uv run scene-planning-bench run-mock
uv run scene-planning-bench run-mock --suite configs/suites/v1_builder.yaml
uv run scene-planning-bench run-mock --suite configs/suites/v1_voxel_builder.yaml
uv run scene-planning-bench run-inspect-mock
uv run scene-planning-bench run-inspect-model google/gemini-2.5-flash
uv run scene-planning-bench run-inspect-model google/gemini-2.5-flash --repeats 3
uv run scene-planning-bench run-inspect-model google/gemini-2.5-flash --suite configs/suites/v1_hidden.yaml --repeats 3
uv run pytest
```

## Expected next implementation layers

- benchmark consumption of normalized plans in saved run artifacts
- stronger normalization for more action types and richer product-facing IR
- richer scoring modules for ambiguity and state correctness

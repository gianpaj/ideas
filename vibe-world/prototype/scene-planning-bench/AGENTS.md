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

Pydantic models live in `src/scene_runtime/artifacts.py`; schemas in `schemas/builder.schema.json` and `schemas/voxel_builder.schema.json`. `SuiteDefaults` carries `builder_schema_path` and `voxel_builder_schema_path`; `load_artifact_schemas` returns a dict keyed by `ArtifactType`. Scoring modules: `scene_planning_bench.scoring.builder_score` and `scene_planning_bench.scoring.voxel_score`. `aggregate_artifact_score` averages non-schema subscores against the scoring profile's non-schema weight total.

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

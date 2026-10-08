# Gemini 3.5 Flash Lite voxel-core prompt

## Decision

Keep the game-v3 baseline in `vibe-world/prototype/scene-planning-bench/configs/suites/v1_voxel_core.yaml` unchanged. The dedicated `v1_voxel_core_gemini_tuned.yaml` suite and `configs/matrices/voxel_core_gemini_tuned.yaml` matrix isolate system-prompt tuning for `google/gemini-3.5-flash-lite`. Task roots, schemas, scoring, fixtures, and production-shaped two-message inputs match the baseline.

The selected prompt defines box-center intervals, connected assemblies, axis-aligned lines, unique material declarations, and a single authored object's 4–14 operations when quantity requests copies. Geometry must retain the requested silhouette and parts; satisfying connectivity by discarding requested parts is not acceptable.

Baseline replacement was rejected because it would erase the production comparison. Task-specific answers, scorer changes, gold changes, hidden-split tuning, and game edits are excluded.

## Evidence

Artifacts below are relative to the benchmark package's `outputs/matrices/`. Every run uses the Gemini model's `runs/gemini-3.5-flash-lite/` task JSON, aggregate, and Inspect logs.

| Run | Artifact directory | Mean score | Perfect | Mean / median latency |
| --- | --- | ---: | ---: | --- |
| Baseline, 3 repeats | `2026-10-08T19-25-20Z_v1-voxel-core_voxel-core-models` | 0.973485 | 11/18 | 2.028611 / 2.117 s |
| Geometry candidate, 3 repeats | `2026-10-08T19-53-32Z_v1-voxel-core-gemini-tuned_voxel-core-gemini-tuned` | 0.992424 | 16/18 | 2.063278 / 2.0455 s |
| Selected prompt, 3 repeats | `2026-10-08T19-54-09Z_v1-voxel-core-gemini-tuned_voxel-core-gemini-tuned` | 1.0 | 18/18 | 2.116944 / 2.084 s |
| Fresh confirmation, 10 repeats | `2026-10-08T19-54-30Z_v1-voxel-core-gemini-tuned_voxel-core-gemini-tuned` | 1.0 | 60/60 | 2.04765 / 2.165 s |

Baseline defects: disconnected parts in six samples and diagonal lines in one. The geometry candidate had one operation-count failure and one connectivity failure, both on the multiple-object task. The selected prompt puts single-object geometry and per-object operation count ahead of construction. It has no observed failures across selection and confirmation. All four runs have 100% schema validity.

Two tuning batches were sufficient under the eight-batch limit. Confirmation keeps the selected prompt fixed and uses fresh calls on the same six dev tasks. This is not a holdout check or a visual-quality assessment. It does not establish unseen-prompt reliability or semantic fidelity. Confirmation averages 1,807.516667 total tokens versus 1,224.5 for baseline; saved cost fields are null. Paid calls were authorized. No game changes or commits were made.

## Verification

- `uv run pytest`: 84 passed.
- Targeted prompt/matrix tests: 4 passed; verify task/schema parity and exact two-message input shape for both suites.
- `uv run scene-planning-bench validate-data`: 2 tasks and 1 scene validated.
- Explicit baseline and tuned `validate-data --suite …`: 6 tasks and 1 scene validated each.
- `git diff --check`: passed.

The benchmark README is the canonical command and results reference. Run artifacts remain local ignored output, not committed fixtures.

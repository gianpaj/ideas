# Local Hatch Pet Orchestrator

## Goal

Automate the deterministic majority of the Hatch Pet v2 workflow from one reference image and pet metadata. Image generation remains an explicit external handoff: the orchestrator prepares jobs, waits for generated files, validates them, and resumes safely.

## User workflow

`hatch_pet.py prepare` accepts a reference image, pet name, description, notes, style, and output directory. It invokes the existing run-preparation script and writes a resumable run state. The user generates or supplies each image listed as ready. `hatch_pet.py resume` discovers completed inputs, processes ready jobs, and advances through QA. `--dry-run` reports the next required input without changing state. `--repair-row ROW` invalidates only that row and resumes from its dependencies.

## State and boundaries

The existing `imagegen-jobs.json` remains the source of truth for visual-job status. The orchestrator adds a small `orchestrator-state.json` containing schema version, run directory, current phase, command history, timestamps, and last error. It never marks a visual job complete until the expected decoded file exists and its deterministic checks pass. It never silently replaces a failed row or overrides semantic QA.

## Pipeline phases

1. Prepare the run and discover ready jobs.
2. Accept/copy selected base and row-strip outputs into `decoded/`.
3. Extract frames and run component, clipping, chroma-adjacency, and hole checks.
4. Assemble and review the intermediate 8x9 atlas.
5. Process cardinal anchors, register look row 9, and gate row 10 on row-9 success.
6. Assemble the 8x11 atlas, run the single final despill pass, validate v2 dimensions, and produce contact sheets, previews, direction QA, and continuity reports.
7. Require explicit semantic/blind-review artifacts, then package `pet.json` and `spritesheet.webp`.

## Safety and recovery

Every subprocess uses the bundled Python runtime and captures stdout, stderr, exit code, and command arguments. Steps are idempotent and write temporary outputs before replacing final files. A failed deterministic check stops the phase with an actionable error. Resume never reruns successful work unless `--force` or `--repair-row` is supplied. Packaging is refused unless validation is v2, chroma cleanup is successful, required QA files exist, and no hard semantic failure remains.

## Implementation shape

Use a small Python package with `cli.py`, `models.py`, `state.py`, `pipeline.py`, and `commands.py`. Keep Hatch Pet scripts unchanged; invoke them through `subprocess.run` with structured command builders. Add unit tests for job readiness, dependency ordering, command construction, resume behavior, repair invalidation, and packaging gates. Add one fixture-based integration test using a prepared run with deterministic placeholder decoded strips; do not invoke image generation in tests.

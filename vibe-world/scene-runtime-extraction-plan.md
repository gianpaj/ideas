# Scene Runtime Extraction Plan

_Drafted: March 26, 2026_

## Purpose

This document turns [`scene-runtime-module-design.md`](scene-runtime-module-design.md) into an implementation sequence.

The goal is to extract a reusable runtime layer from the current scene-planning benchmark without breaking the benchmark while it is still the main implementation artifact.

## Target outcome

The benchmark package should stop owning the full planning contract.

Instead:

- `scene_runtime` should own reusable planning models, parsing, schema validation, prompt construction, normalization contracts, and render-draft contracts
- `scene_planning_bench` should consume that runtime layer for benchmark-specific evaluation, scoring, matrix runs, and reporting

## Constraints

- keep the benchmark runnable throughout the extraction
- avoid changing benchmark scoring semantics during the extraction
- preserve current CLI behavior
- prefer compatibility wrappers where needed to reduce churn
- keep the first extraction pass inside the existing `prototype/scene-planning-bench/` project

## Phase 1 — Extract reusable core primitives

Create a new package under:

- `prototype/scene-planning-bench/src/scene_runtime/`

Initial modules:

- `models.py`
- `parsing.py`
- `schema.py`
- `prompting.py`
- `contracts.py`
- `__init__.py`

Move or re-home:

- reusable response models from `scene_planning_bench/types.py`
- fenced-JSON parsing from `scene_planning_bench/validation/json_parse.py`
- schema loading and validation from `scene_planning_bench/validation/schema_validate.py`
- generalized prompt assembly derived from `scene_planning_bench/prompts.py`

Keep benchmark-specific code in place.

Success criteria:

- benchmark can still import compatibility shims from `scene_planning_bench`
- reusable code can also be imported directly from `scene_runtime`

## Phase 2 — Add runtime-only contracts

Add the first runtime-facing types:

- `PlanningRequest`
- `PlanningOutcome`
- `NormalizedScenePlan`
- `ObjectIntent`
- `RenderDraftSpec`

This phase does not need to fully implement normalization logic yet.

The initial goal is to make the contracts concrete and importable, so future work can target them directly.

Success criteria:

- live prototype code could depend on `scene_runtime` contracts without importing benchmark task or scoring types
- benchmark remains unchanged in behavior

## Phase 3 — Introduce a first normalizer

Add a first explicit normalizer:

- `ScenePlanningResponse -> NormalizedScenePlan`

First-pass mappings:

- `add_object` -> `create`
- `replace_object` -> `refine`
- `move_object` -> `refine`
- `set_color` -> `refine`
- `set_material` -> `refine`
- `spawn_layout` -> `create` with `layout_hint`

Clarification and refusal flows should map directly to top-level normalized plan kinds.

Success criteria:

- normalization is deterministic
- lossy mappings are recorded in diagnostics
- no benchmark scoring logic depends on the normalized plan yet

## Phase 4 — Add render-draft conversion

Add:

- `NormalizedScenePlan -> RenderDraftSpec`

The first render spec should stay rough and deterministic.

It should support:

- chunky primitive nodes
- draft display name
- placement anchor
- preview materials
- optional simple animation presets

Success criteria:

- a future live prototype can render a draft preview without consuming raw benchmark actions

## Phase 5 — Refactor benchmark to consume runtime layer

Refactor benchmark modules to import from `scene_runtime` instead of owning duplicate logic.

Expected benchmark consumers:

- `evaluation.py`
- `inspect_runner.py`
- `prompts.py`
- `validation/`
- selected tests

Keep benchmark-only ownership for:

- suite loading
- benchmark task models
- scoring
- reports
- matrix orchestration

Success criteria:

- benchmark still runs
- reusable logic now has one owner
- benchmark becomes a consumer of the runtime layer

## File mapping

### Reusable into `scene_runtime`

- response and scene models
- parse helpers
- schema helpers
- prompt request construction helpers
- runtime contracts
- normalization logic
- render draft conversion

### Remains in `scene_planning_bench`

- `BenchmarkTask`
- `ScoringProfile`
- `SuiteConfig`
- `RunResult`
- registry and dataset loading
- evaluation and scoring
- Inspect integration
- reports
- CLI matrix orchestration

## First implementation slice

The first actual extraction pass should do only this:

1. add `scene_runtime/models.py`
2. add `scene_runtime/parsing.py`
3. add `scene_runtime/schema.py`
4. add `scene_runtime/contracts.py`
5. add `scene_runtime/prompting.py`
6. keep benchmark compatibility wrappers in:
   - `scene_planning_bench/types.py`
   - `scene_planning_bench/validation/`
   - `scene_planning_bench/prompts.py`

That slice is intentionally limited.

It creates the shared runtime boundary without also trying to solve normalization, rendering, and backend integration in the same pass.

## Testing strategy

During extraction:

- keep unit tests around parsing and schema validation green
- add tests for `scene_runtime` imports and contracts
- run benchmark smoke tests that are unaffected by unrelated local worktree changes

Later:

- add explicit normalization tests
- add prompt-construction tests against `PlanningRequest`
- add render-draft conversion tests

## Risks

- partial extraction can leave duplicate code paths if wrappers are not cleaned up
- benchmark-specific assumptions can leak into runtime types if the boundary is not enforced
- unrelated local prototype edits can interfere with full-suite validation during this transition

## Recommendation

Start with Phase 1 and Phase 2 now.

That gives the project:

- a real shared runtime package
- stable import paths for future live prototype code
- minimal benchmark disruption

Then add normalization and render-draft conversion in later commits.

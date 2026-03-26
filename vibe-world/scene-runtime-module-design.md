# Scene Runtime Module Design

_Drafted: March 26, 2026_

## Purpose

This document defines the reusable runtime module that sits between:

- the AI worker that calls an LLM,
- strict validation of the model output,
- normalization into a Vibe World-aligned internal plan,
- rendering of a rough draft object on screen.

The goal is to support the first live prototype without locking the project into the benchmark's current generic action format forever.

## Design goal

The runtime module should support both:

- a fast path to get validated AI outputs rendered on screen quickly,
- a product-aligned path toward the Vibe World object-intent IR described in [`prompt-ir-spec.md`](prompt-ir-spec.md).

The design should not force a choice between those two goals.

## Recommended contract layers

The runtime module should use three explicit layers.

### Layer 1 — Model response contract

This is the current benchmark-facing validated response shape.

It should stay close to the existing schema and Pydantic models used in:

- `prototype/scene-planning-bench/src/scene_planning_bench/types.py`
- `prototype/scene-planning-bench/src/scene_planning_bench/validation/json_parse.py`
- `prototype/scene-planning-bench/src/scene_planning_bench/validation/schema_validate.py`

This layer keeps the first prototype moving quickly because it reuses the benchmark's current response model:

- `scene_actions`
- `clarification_request`
- `refusal`

### Layer 2 — Normalized runtime plan

This is the stable internal contract for the live product flow.

It should normalize the validated model response into a Vibe World-aligned plan that is no longer tied directly to the benchmark's raw action language.

This layer is the key design move.

It allows the benchmark to keep using the current response format, while the live prototype and future game systems depend on a cleaner internal plan shape.

### Layer 3 — Render draft spec

This is the first renderer-facing contract.

It should be a deterministic rough-draft description that the client can draw immediately.

It should not be:

- the raw LLM output,
- the benchmark response format,
- the final authoritative world object format.

It should be a lightweight preview representation for the first live creation loop.

## End-to-end pipeline

The intended flow is:

`LLM raw output -> parse -> validate -> normalize -> render`

More concretely:

1. AI worker sends a prompt bundle to an LLM.
2. Raw text output is parsed as JSON, with fenced JSON tolerated.
3. Parsed JSON is validated against the response schema.
4. Validated output is transformed into a normalized Vibe World plan.
5. The normalized plan is transformed into a renderer-friendly draft spec.
6. The renderer draws the draft object on screen.

Later, the same normalized plan can also feed the authoritative builder path.

## Core contracts

### PlanningRequest

`PlanningRequest` is the AI worker input contract.

Suggested fields:

- `request_id`
- `scene`
- `user_prompt`
- `system_prompt`
- `target_world_id`
- `target_object_id`
- `base_object_version`
- `response_schema`
- `metadata`

Purpose:

- unify the request shape for benchmark and live runtime usage,
- generalize the current prompt assembly logic from `prompts.py`,
- support both create and edit/refine flows.

### PlanningOutcome

`PlanningOutcome` is the full runtime result from one model call.

Suggested fields:

- `request_id`
- `raw_output`
- `parsed_response`
- `schema_errors`
- `normalized_plan`
- `diagnostics`

Purpose:

- preserve raw model output for debugging and replay,
- keep validated parsed output available for benchmark scoring,
- expose normalized runtime output for the live prototype.

### NormalizedScenePlan

`NormalizedScenePlan` is the product-facing internal contract.

Suggested fields:

- `plan_version`
- `request_id`
- `plan_kind`
- `source_response_type`
- `uncertainty`
- `intents`
- `clarification`
- `refusal`
- `diagnostics`

Suggested plan kinds:

- `object_intent`
- `clarification`
- `refusal`

Purpose:

- isolate live product code from the raw benchmark action format,
- keep clarification and refusal flows explicit,
- provide a single internal shape that can later feed both rendering and authoritative object creation.

### ObjectIntent

`ObjectIntent` is the main normalized unit for Vibe World creation/refinement.

Suggested fields:

- `intent_id`
- `operation`
- `target_object_id`
- `base_object_version`
- `category`
- `size_tier`
- `parts`
- `material_palette`
- `behavior_presets`
- `transform_hints`
- `style_tags`
- `layout_hint`
- `source_actions`

Suggested operations:

- `create`
- `refine`
- `remix`

This contract should align with the direction in [`prompt-ir-spec.md`](prompt-ir-spec.md), while still allowing traceability back to the original validated response.

### RenderDraftSpec

`RenderDraftSpec` is the first screen-facing contract.

Suggested fields:

- `draft_id`
- `request_id`
- `intent_id`
- `display_name`
- `primitive_nodes`
- `world_anchor`
- `bounds_hint`
- `preview_materials`
- `animation_presets`
- `warnings`

Purpose:

- support fast visual iteration,
- keep the first draft renderer deterministic and easy to debug,
- avoid exposing benchmark-specific or backend-specific details to the renderer.

## Normalization rules

The first normalizer should be explicit and loss-aware.

Suggested first-pass mappings:

- `add_object` -> `create`
- `replace_object` -> `refine`
- `move_object` -> `refine`
- `set_color` -> `refine`
- `set_material` -> `refine`
- `spawn_layout` -> `create` with `layout_hint`

Special cases:

- `clarification_request` should become `plan_kind=clarification`
- `refusal` should become `plan_kind=refusal`
- ambiguous or lossy mappings should be recorded in `diagnostics`

The normalizer should not silently invent more certainty than the model actually provided.

## Fast-path and long-path compatibility

This design intentionally supports both prototype speed and product alignment.

### Fast path

For the first live prototype:

- keep the outer validated response close to the current benchmark schema,
- reuse the current JSON parsing and schema validation logic,
- normalize into a very light runtime plan,
- render a rough draft quickly.

This is the fastest route to:

`AI worker -> validation -> normalized scene plan -> render to screen`

### Long path

For the longer-term Vibe World direction:

- evolve `ObjectIntent` toward the object-intent IR in [`prompt-ir-spec.md`](prompt-ir-spec.md),
- add richer parts, materials, behaviors, and transform hints,
- use the normalized plan as the handoff into authoritative builder specs and backend reducers.

This avoids baking the benchmark's current generic action language into the long-term product architecture.

## Benchmark boundary

The benchmark should become a consumer of the runtime core, not the owner of it.

That means the following concerns should remain benchmark-specific:

- benchmark task models
- suite and dataset loading
- deterministic scoring
- Inspect execution integration
- CSV and aggregate reporting
- matrix run orchestration

The runtime core should own:

- reusable response and scene models
- parsing
- schema validation
- prompt bundle construction for live requests
- normalization into the runtime plan
- render draft spec generation

## Proposed package layout

Suggested product-facing package boundary:

- `scene_runtime/models.py`
- `scene_runtime/parsing.py`
- `scene_runtime/schema.py`
- `scene_runtime/prompting.py`
- `scene_runtime/contracts.py`
- `scene_runtime/normalize.py`
- `scene_runtime/render_spec.py`

For the least churn, this can first live as a subpackage inside the current benchmark project before being promoted later.

## Migration plan

Suggested extraction order:

1. Extract reusable response and scene models from the benchmark package.
2. Extract fenced-JSON parsing and schema validation into the runtime module.
3. Generalize prompt-bundle assembly around `PlanningRequest`.
4. Introduce `PlanningOutcome` and `NormalizedScenePlan`.
5. Add the first explicit normalizer from `ScenePlanningResponse` to `NormalizedScenePlan`.
6. Add `RenderDraftSpec` generation for a first visual draft renderer.
7. Update the benchmark to import the reusable runtime layer instead of owning those pieces directly.

This order keeps the benchmark working while gradually converting it into a consumer of the shared runtime code.

## Risks

Main risks:

- the fast path can tempt the project to depend on generic scene actions too long,
- `spawn_layout` and grouped edits do not map perfectly to single-object intent,
- over-aggressive normalization can hide real model errors,
- pushing too much detail into the render draft spec too early can accidentally recreate a full builder contract.

These risks are manageable if the normalized layer stays explicit, traceable, and intentionally draft-oriented.

## Recommendation

Adopt a dual-layer runtime design:

- keep the current validated response schema as the outer contract,
- add a Vibe World-aligned normalized runtime plan as the internal contract,
- add a renderer-facing draft spec as the screen contract.

This is the cleanest way to get to a first live prototype quickly without freezing the project into a temporary benchmark-shaped architecture.

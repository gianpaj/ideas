# Scene Builder Benchmark Plan

_Drafted: March 28, 2026_

## Purpose

This document defines the first benchmark for the Vibe World builder layer.

The planning benchmark already validates:

- raw model output parsing
- schema validation
- normalization into `NormalizedScenePlan`
- preview draft generation

It does not yet validate the authoritative builder seam:

`normalized scene plan -> deterministic builder spec`

This benchmark exists to validate that seam directly.

## Why a separate benchmark

The builder is not a frontend concern.

For the real game, the builder should live on the worker/backend side, because:

- the client should not author authoritative object structure
- reducers must validate permissions, lifecycle, and object versions before accepting the result
- the backend must be able to reject stale, oversized, destructive, or invalid specs safely

That makes the right benchmark target a backend-oriented deterministic `BuilderSpec`, not rendered meshes.

## Scope

The first version should benchmark:

- `NormalizedScenePlan` fixture in
- selected `ObjectIntent` resolution
- deterministic `BuilderSpec` output
- schema validation
- semantic validation
- continuity rules for `refine` and `remix`

It should not benchmark:

- LLM calling
- frontend rendering
- multiplayer reducers
- full voxel meshing
- physics or navigation

## Recommended implementation location

Create a sibling prototype package:

- `prototype/scene-builder-bench/`

Keep the split parallel to `scene-planning-bench`:

- benchmark-specific code in `src/scene_builder_bench/`
- reusable builder/runtime code in `src/scene_builder_runtime/`

## Benchmark contract

### Input

- checked-in normalized-plan fixture JSON
- optional object-context fixture for `refine` and `remix`
- world-settings constraints
- expected semantic checks

### Output

- deterministic `BuilderSpec`
- canonicalized JSON representation
- stable content hash
- semantic diagnostics and validation errors

## First scoring dimensions

### 1. Schema validity

Check that the produced `BuilderSpec` matches a strict JSON schema.

### 2. Semantic compliance

Check:

- allowed primitive vocabulary
- material vocabulary
- behavior vocabulary
- part-count caps
- instance-count caps
- no arbitrary scripts or mesh payloads

### 3. Determinism

For the same input fixture, repeated builder runs should produce the same canonicalized output and hash.

### 4. Continuity

For `refine` and `remix`, the builder should preserve object identity and inherit stable prior structure unless the change explicitly requires replacement.

### 5. Complexity fitness

Simple prompts should not explode into oversized specs.

## First task set

The initial scaffold should include:

- single-object create: pine tree left of cabin
- grouped layout create: three barrels around campfire
- refine flow: tree keeps prior structure but adds a glow behavior and accent material

These are enough to validate:

- basic create mapping
- grouped instance handling
- continuity against prior builder state

## Language choice

The first benchmark should be Python.

Why:

- `scene-planning-bench` is already Python
- the project is still in validation mode, not production hardening mode
- Python is the fastest place to iterate on scoring, fixtures, and canonicalization rules
- production builder implementation can still move to Go later if the service boundary demands it

## Success criteria

The scaffold is successful if it provides:

- a runnable `uv run scene-builder-bench validate-data`
- a runnable `uv run scene-builder-bench run-local`
- checked-in fixtures and schemas
- deterministic local builder output
- pytest coverage for determinism and runner smoke

## Follow-on work

After the scaffold exists, the next benchmark improvements should be:

- richer refine/remix fixtures
- public/private destructive-rule validation
- stronger golden assertions for exact part structure
- benchmark reuse of `scene-planning-bench` normalized-plan artifacts
- reducer-facing validation of accepted vs rejected builder specs

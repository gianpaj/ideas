# Scene Runtime TypeScript Port Plan

_Drafted: March 27, 2026_

## Purpose

This document defines the first TypeScript port of `scene_runtime`.

The port is intended to:

- live inside this repo for now,
- stay secondary to the Python implementation,
- provide a browser-facing consumer of the runtime contract,
- include a small demo that renders draft previews in the browser,
- use `React Three Fiber` for the first visual implementation.

This port is not yet the production source of truth.

## Source of truth

For the current phase:

- Python remains the source of truth for runtime behavior
- JSON schemas, saved benchmark artifacts, and the Python `scene_runtime` package define the reference contract
- the TypeScript port is a consumer/reference implementation

This means:

- contract changes should still be designed and validated in Python first
- the TypeScript package should follow the Python runtime, not race ahead of it

## Why TypeScript now

The game client will likely be web-based and TypeScript-heavy even if the long-term backend moves to Go or another server language.

That makes a TS port useful now for:

- browser previews of normalized plans
- debugging runtime outputs visually
- validating that the runtime contract is practical on the client side
- reducing future migration risk into the real game/web repo

## Scope

The first TypeScript port should include:

- contract types for parsed response, normalized plan, and render draft output
- client-safe validation helpers and guards
- normalization logic from parsed response to normalized plan
- render-draft helpers for preview
- a small browser demo that loads a saved artifact and renders the draft preview

The first TypeScript port should not include:

- LLM calling logic
- authoritative backend behavior
- multiplayer state management
- scoring and benchmark orchestration
- Python replacement

## Recommended architecture

The first TS port should live as a sibling prototype package inside this repo.

Suggested location:

- `prototype/scene-runtime-ts/`

Suggested structure:

- `src/contracts/`
- `src/normalize/`
- `src/render/`
- `src/loaders/`
- `src/demo/`
- `src/index.ts`

Suggested app/runtime split:

- library code in `src/`
- lightweight browser demo in `demo/` or a minimal app entry inside `src/demo/`

## Why React Three Fiber

`React Three Fiber` is the best first fit for this port because the initial goal is a browser demo that sits inside a web-style app shell rather than a full engine-oriented frontend.

R3F is a good fit here because:

- the first demo needs UI and 3D together
- artifact inspection and debug views will matter
- the render layer is still draft-oriented, not a custom game engine
- the likely surrounding stack for the first web prototype will already be React/TypeScript-friendly

Plain `three.js` would be more manual and lower-level than this first demo needs.

## First package responsibilities

### 1. Contract mirror

Mirror the Python runtime contract in TS:

- `PlanningRequest`
- `PlanningOutcome`
- `NormalizedScenePlan`
- `ObjectIntent`
- `RenderDraftSpec`

Also mirror the model response shape closely enough to consume saved artifact JSON safely.

The TS contract should follow the Python version closely, including:

- `instance_count`
- `layout_hint`
- `render_drafts`
- `diagnostics`

### 2. Normalization mirror

Mirror the current Python normalization behavior:

- `clarification_request -> clarification plan`
- `refusal -> refusal plan`
- create and refine action mapping
- grouped layout handling
- repeated create merging into `instance_count`

The goal is not to invent new behavior in TS.

The goal is to prove that the Python runtime contract can be implemented cleanly in a browser-friendly TypeScript package.

### 3. Render-draft mirror

Mirror the Python render-draft conversion:

- intent -> preview nodes
- grouped instances -> repeated preview nodes
- simple layout interpretation such as triangle spacing
- fallback warnings when layout is missing

This gives the browser demo a deterministic preview surface.

## Demo scope

The first demo should be deliberately small.

Recommended demo behavior:

1. load a saved benchmark task artifact JSON from `prototype/scene-planning-bench/outputs/` or a copied fixture
2. display:
   - parsed response type
   - normalized intent count
   - grouped instance counts
   - render draft count
3. render the draft preview in a simple 3D scene
4. allow switching between a few saved example artifacts

Recommended first examples:

- one simple single-object create
- one grouped layout create such as the barrel triangle
- one clarification example

The first demo does not need:

- live model calling
- prompt submission
- multiplayer state
- backend integration

## Artifact strategy

The TS demo should consume saved artifact JSON produced by the Python benchmark/runtime.

Recommended approach:

- keep a few stable example fixtures checked into the TS prototype package
- optionally also support loading real generated run artifacts from the benchmark output folders

Why:

- stable fixtures keep the demo reproducible
- live artifacts let the demo inspect current model behavior

## Validation strategy

Because Python remains source of truth, the TS port should validate itself against Python outputs.

Recommended checks:

- fixture-based tests against saved normalized plans and render drafts
- parity tests where TS normalization of a parsed response matches a saved Python normalized result
- render helper tests for grouped instance counts and layout interpretation

The goal is behavioral parity, not independent reinterpretation.

## Suggested phases

### Phase 1 — Package scaffold

Deliver:

- TS package scaffold
- build/test setup
- core type definitions

Outcome:

- TS package can import and type-check artifact JSON

### Phase 2 — Runtime contract mirror

Deliver:

- parsed response types
- normalized plan types
- render draft types
- artifact loaders

Outcome:

- TS package can read saved Python runtime artifacts safely

### Phase 3 — Normalization mirror

Deliver:

- create/refine mapping
- grouped layout handling
- repeated-create merge logic

Outcome:

- TS package can normalize parsed responses into the same internal shape as Python

### Phase 4 — Render-draft mirror

Deliver:

- draft node conversion helpers
- preview anchor helpers
- grouped instance preview behavior

Outcome:

- TS package can produce renderable preview data from normalized plans

### Phase 5 — React Three Fiber demo

Deliver:

- minimal web demo
- fixture selector
- draft preview scene
- runtime summary panel

Outcome:

- browser demo can visually inspect the runtime contract

## Risks

Main risks:

- Python and TS implementations drift if parity fixtures are not maintained
- TS port starts inventing behavior before Python contracts stabilize
- demo complexity grows into a proto-game instead of staying a contract viewer

These risks are manageable if the TS package stays intentionally consumer-oriented and fixture-driven.

## Recommendation

Build the TypeScript port as:

- a sibling prototype package in this repo
- a consumer of Python-owned contracts and artifacts
- a React Three Fiber demo for visual inspection of normalized plans and render drafts

The correct mindset is:

- Python discovers and stabilizes the runtime contract
- TypeScript proves that contract is practical in the browser

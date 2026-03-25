# Open Questions and Next Steps

## Open design questions

The concept is already coherent, but several higher-level choices still need to be pinned down.

## 1. Rate limits and spam control

Open question:

- How many new objects can a regular player create per minute?
- Should limits vary by world type, trust level, or host settings?

Recommendation:

- add soft per-player creation limits in public worlds,
- let private worlds be more permissive,
- leave room for trust-based relaxation later.

## 2. Scope of terminal mode

Open question:

- How expressive should the in-world terminal be?
- Is it only a declarative command DSL, or does it eventually allow richer scripts?

Recommendation:

- keep V1 terminal mode highly constrained,
- focus on structured commands for spawn/edit/material/behavior,
- do not expose arbitrary general-purpose scripting first.

## 3. Behavior complexity

Open question:

- How much object behavior should ordinary players be allowed to add?

Recommendation:

- start with a small behavior preset library,
- postpone arbitrary scripting of logic-heavy interactions,
- preserve server-side determinism and moderation simplicity.

## 4. Terrain vs object editing

Open question:

- Is the first version mostly about spawned objects,
- or does it also allow direct editing of terrain / world matter?

Recommendation:

- start with objects first,
- add environmental voxel editing later in a constrained way,
- avoid solving both terrain and object complexity at once in V1.

## 5. World browser and discovery

Open question:

- How are the “most fun” worlds surfaced?

Recommendation:

- combine current players, recent retention, session length, and moderation stability,
- avoid ranking purely by raw concurrency,
- build toward host/world reputation slowly.

## 6. Archive presentation

Open question:

- How should old snapshots feel visually?

Recommendation:

- clearly separate archive mode from live mode,
- use atmospheric cues like timestamp overlays, subtle visual filtering, and a strong “read-only memory” feel.

## 7. Trusted builder roles

Open question:

- Should hosts eventually be able to elevate trusted players?

Recommendation:

- yes, but not required in first playable,
- useful later for large public worlds and moderation delegation.

## 8. Public world curation zones

Open question:

- Beyond the spawn area, should hosts be able to create build zones, gallery zones, or chaos corners?

Recommendation:

- likely yes in V2,
- but not necessary for first prototype if the object rules are already constrained.

## 9. AI model usage strategy

Open question:

- Which model types should be used live versus offline or assistive?

Recommendation:

- use LLM/VLM for intent parsing and structured generation,
- keep deterministic world-native assembly in-engine,
- treat stronger 3D generators as optional assistive tools or future asset-authoring systems.

## Prototype roadmap

## Prototype 0 — Rule sandbox

Goal:

Validate the world rule model without advanced AI.

Features:

- one hosted room or island,
- public/private toggle,
- object spawn,
- grace period,
- move/scale,
- one-object-at-a-time lock,
- 30-second cooldown,
- basic archive snapshot system.

No real 3D generation required yet; objects can come from small templates.

## Prototype 1 — Prompt-first object drafts

Goal:

Validate whether prompt-first rough drafts feel fun.

Features:

- rough draft generation from constrained prompts,
- follow-up refinement prompts,
- material changes,
- simple behavior presets,
- public remix flow.

Key question:

- does creating something recognizable within seconds actually feel magical?

## Prototype 2 — Hosted worlds network

Goal:

Validate that multiple hosts and world discovery make the product more compelling.

Features:

- world browser,
- templates,
- public/private worlds,
- persistence settings,
- reset cadence,
- archive browsing,
- trending worlds.

## Prototype 3 — Richer world-native grammar

Goal:

Increase variety without losing speed.

Features:

- more object categories,
- modular parts,
- more atmosphere/material controls,
- stronger host tools,
- optional trusted builder role.

## Recommended immediate next deliverables

1. write a one-page product pitch,
2. define the world settings schema,
3. define the object schema and state machine,
4. define the prompt-to-object intermediate representation,
5. define the first `SpacetimeDB` schema and reducer boundaries,
6. build a minimal playable hosted room.

## Chosen V1 multiplayer stack

As of **March 24, 2026**, the recommended V1 multiplayer backend is:

- **SpacetimeDB** for authoritative shared state,
- an **external AI worker/service** for prompt-to-draft generation,
- a client renderer/game layer that subscribes to authoritative world updates.

### Why this is now the working decision

This matches the current prototype goals better than keeping the stack undecided.

The first playable is mainly about:

- shared room state,
- object lifecycle and permissions,
- public/private world rule differences,
- edit locks and cooldowns,
- rough-draft prompt creation,
- archive-ready world state.

The prototype is not primarily trying to validate:

- high-speed combat simulation,
- dense custom tick-loop gameplay,
- physics-heavy competitive networking.

That makes a state-oriented multiplayer backend a better fit than a more simulation-centric server approach.

### Working V1 boundary

The intended V1 flow is:

**client prompt or edit intent -> AI worker/service -> validated structured draft -> SpacetimeDB reducer -> subscribed clients**

This keeps:

- AI generation outside the authoritative database runtime,
- authoritative world transitions inside the multiplayer backend,
- the world model aligned with the structured-IR direction already described in the architecture notes.

## Suggested first technical spec documents

The next documents worth writing after this bundle are:

- `world-settings-schema.md`
- `object-state-machine.md`
- `prompt-ir-spec.md`
- `public-world-permission-matrix.md`
- `spacetimedb-v1-schema.md`
- `prototype-v1-scope.md`

All six immediate follow-up specs are now drafted:

- `world-settings-schema.md`
- `object-state-machine.md`
- `prompt-ir-spec.md`
- `public-world-permission-matrix.md`
- `spacetimedb-v1-schema.md`
- `prototype-v1-scope.md`

The next implementation-facing follow-up specs now drafted are:

- `reducer-api-spec.md`
- `ai-worker-contract.md`

## Bottom line

The concept is now strong enough to move from brainstorming into early product and technical specification work.

The clearest immediate focus is:

> Build one small hosted voxel world where players can prompt rough-draft objects into existence, move/scale them during a grace period, and release them into a remixable public sandbox with simple authoritative locking and archive snapshots.

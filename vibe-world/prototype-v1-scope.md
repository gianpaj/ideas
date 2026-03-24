# Prototype V1 Scope

_Drafted: March 24, 2026_

## Purpose

This document defines the first playable implementation scope for Vibe World.

The goal of V1 is to prove that a prompt-first, multiplayer, object-based sandbox feels good in live play.

The product question is:

> Can about 20 anonymous players share a world, prompt rough-draft objects into existence, move and refine them during a grace period, then release them into a remixable sandbox with simple authoritative rules?

## V1 success criteria

V1 is successful if it demonstrates:

- a shared multiplayer room with about 20 concurrent players,
- both public and private world creation,
- prompt-to-draft object generation with real AI,
- visible creator-only grace periods,
- public-world non-destructive remixing,
- private-world destructive editing,
- one-editor-at-a-time locking on existing public objects,
- cooldown after accepted public edits,
- stable enough latency and sync that the world feels coherent.

## V1 non-goals

V1 is not trying to ship:

- direct terrain editing,
- detailed voxel sculpting tools,
- full persistence and economy systems,
- rich social graph or accounts,
- advanced moderation tooling,
- full world discovery and ranking,
- deep behavior scripting,
- combat-first gameplay.

## Core product shape

### World model

V1 supports:

- public rooms,
- private rooms,
- fixed starter environment,
- object-only editing.

V1 does not support:

- terrain carving,
- fully custom world templates,
- complex zone systems.

### Player model

Players join anonymously with temporary nicknames.

V1 supports:

- join room,
- move around,
- see other players,
- create objects,
- remix permitted objects.

V1 does not require:

- account login,
- persistent identity,
- friends systems.

### Object model

Objects are the center of the prototype.

Each object supports:

- prompt-based creation,
- rough-draft appearance,
- creator-only grace period,
- move and scale during grace period,
- follow-up prompt refinement,
- release into public world state,
- remix flow after release,
- archive freezing during snapshots.

## Multiplayer rule scope

### Public worlds

Regular players may:

- create new objects,
- remix public objects,
- make non-destructive changes.

Regular players may not:

- make destructive edits,
- delete shared public structures arbitrarily,
- bypass edit locks.

### Private worlds

Private worlds may allow:

- destructive edits,
- looser experimentation,
- faster collaborative chaos.

### Existing object editing

V1 includes:

- one active editor at a time,
- inactivity timeout,
- cooldown after successful edit.

### New object creation

V1 includes:

- creator-only grace period,
- move and scale during grace period,
- optional rotate if cheap enough,
- automatic or manual release into public state.

## Technical shape

### Backend

The recommended V1 multiplayer stack is:

- `SpacetimeDB` for authoritative shared state,
- external AI worker/service for prompt interpretation and draft generation,
- web client for rendering and interaction.

### AI pipeline

The V1 flow is:

**player prompt -> AI worker -> constrained prompt IR -> validated builder spec -> authoritative object create/edit reducer**

The AI should generate rough drafts, not polished final art.

### Rendering

V1 should use a fixed world and render spawned objects clearly.

The rendering layer should prioritize:

- low friction,
- readable multiplayer diffs,
- clearly blocky/chunky objects,
- fast iteration over high fidelity.

## High-level implementation plan

### Phase 1 — Foundation

Deliver:

- repo and runtime setup,
- `SpacetimeDB` local development loop,
- minimal web client shell,
- anonymous session creation,
- temporary nickname flow.

Outcome:

- one user can enter a world and hold a live connection.

### Phase 2 — Shared room and presence

Deliver:

- world creation and join flow,
- public/private room presets,
- player presence subscriptions,
- player transform sync,
- basic room UI.

Outcome:

- multiple players can join and see each other in the same world.

### Phase 3 — Authoritative object lifecycle

Deliver:

- object schema,
- create object request flow,
- grace period ownership,
- release flow,
- edit lock flow,
- cooldown flow,
- private-world delete/destructive flow.

Outcome:

- the world has enforceable object rules even before AI quality is good.

### Phase 4 — Real AI prompt-to-draft

Deliver:

- AI worker/service,
- prompt IR validator,
- builder spec generation,
- create-object prompt flow,
- refine-object prompt flow,
- failure and timeout handling.

Outcome:

- prompts create recognizable rough drafts in the shared room.

### Phase 5 — Client editing and feedback

Deliver:

- move and scale controls during grace period,
- lock status feedback,
- cooldown feedback,
- attribution display,
- basic object inspection UI.

Outcome:

- players understand what they can edit and when.

### Phase 6 — Snapshots and reset worlds

Deliver:

- world snapshot creation,
- frozen archive records,
- manual and scheduled reset support,
- read-only archive browsing at a minimal level.

Outcome:

- resettable worlds become part of the actual prototype loop.

### Phase 7 — Hardening and playtest

Deliver:

- per-player rate limits,
- reconnect handling,
- stuck-lock cleanup,
- simple moderation guardrails,
- lightweight metrics and logs,
- small group playtests.

Outcome:

- the prototype is stable enough to learn from real sessions.

## Suggested first breakdown after this doc

The next planning layer should break the work into concrete specs and milestones:

- `world-settings-schema.md`
- `object-state-machine.md`
- `prompt-ir-spec.md`
- `public-world-permission-matrix.md`
- `spacetimedb-v1-schema.md`

After that, implementation can be broken into milestone tickets such as:

- backend foundation,
- room presence,
- object lifecycle,
- AI worker integration,
- client controls and UX,
- snapshots and reset flow,
- playtest stabilization.

## Recommended build order

If implementation starts immediately, the recommended order is:

1. backend connection and anonymous join,
2. multiplayer room presence,
3. object lifecycle without AI,
4. AI prompt-to-draft integration,
5. client grace-period editing,
6. snapshots and resets,
7. guardrails and playtests.

This keeps the authoritative rule system stable before AI complexity is layered on top.

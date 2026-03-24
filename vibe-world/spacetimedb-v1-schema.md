# SpacetimeDB V1 Schema

_Drafted: March 24, 2026_

## Purpose

This document defines the first multiplayer data model for Vibe World using **SpacetimeDB**.

The goal of V1 is not to solve full terrain editing or advanced simulation.
The goal is to support:

- hosted public and private worlds,
- anonymous temporary players,
- prompt-first object creation,
- grace periods,
- remix locks,
- cooldowns,
- destructive edits in private worlds only,
- resettable worlds with archive snapshots.

## Architectural boundary

SpacetimeDB is the authoritative multiplayer state layer.

It should own:

- world state,
- player presence,
- object state,
- permissions,
- lifecycle transitions,
- lock and cooldown enforcement,
- snapshot metadata and frozen records.

It should not directly own live prompt generation.

The V1 boundary is:

**client intent -> AI worker/service -> validated draft payload -> SpacetimeDB reducer -> subscribed clients**

## V1 design principles

- Keep the authoritative model object-first, not terrain-first.
- Model world rules explicitly rather than burying them in client logic.
- Make lifecycle transitions first-class.
- Prefer durable rows and reducers over implicit in-memory room state.
- Keep AI output constrained and validated before it changes live state.

## Core entities

### Worlds

Each world is one hosted multiplayer room.

Suggested fields:

- `world_id`
- `name`
- `visibility` = `public | private`
- `host_player_id`
- `destructive_edits_enabled`
- `persistence_mode` = `permanent | temporary | scheduled_reset`
- `reset_interval_seconds`
- `spawn_position`
- `spawn_rotation`
- `created_at`
- `updated_at`
- `is_archived`

Notes:

- Public worlds should default to non-destructive remixing.
- Private worlds may allow destructive edits.
- V1 can keep world settings as a compact ruleset rather than a large policy engine.

### Players

Players are anonymous sessions with temporary nicknames.

Suggested fields:

- `player_id`
- `world_id`
- `nickname`
- `role` = `host | player`
- `connection_id`
- `presence_state` = `connecting | active | disconnected`
- `position`
- `rotation`
- `joined_at`
- `last_seen_at`

Notes:

- V1 should treat reconnects as best-effort session recovery, not full account recovery.
- Player movement can be approximate and frequent, but still validated server-side.

### Objects

Objects are the main editable entities in V1.

Suggested fields:

- `object_id`
- `world_id`
- `version`
- `state` = `draft | grace | public | edit_locked | cooldown | archived | deleted`
- `original_creator_id`
- `latest_editor_id`
- `current_lock_owner_id`
- `category`
- `size_tier`
- `material_preset`
- `behavior_preset`
- `position`
- `rotation`
- `scale`
- `is_public_remixable`
- `is_destructible`
- `created_at`
- `updated_at`
- `grace_expires_at`
- `cooldown_expires_at`

Notes:

- `version` is required so reducers can reject stale edits.
- `state` should reflect the lifecycle clearly enough that clients do not infer it indirectly.
- `is_destructible` should be derived from world rules plus object status in V1, even if stored redundantly for query speed later.

### Object Specs

Objects need a structured payload that separates gameplay state from generation details.

Suggested fields:

- `object_id`
- `prompt_ir`
- `builder_spec`
- `render_spec`
- `latest_prompt_text`
- `updated_at`

Definitions:

- `prompt_ir`: constrained intent payload generated from user prompts
- `builder_spec`: deterministic world-native description used to build the object
- `render_spec`: optional client-facing preview or render description

Notes:

- V1 should not treat `render_spec` as the canonical world model.
- If `json-render` is used, it should live here as a preview-oriented spec, not as the source of truth.

### Object Locks

Locks should be explicit rows, not inferred from object state alone.

Suggested fields:

- `object_id`
- `player_id`
- `lock_type` = `grace | edit | cooldown`
- `granted_at`
- `expires_at`

Notes:

- Grace period is effectively a creator-only lock.
- Edit lock and cooldown should be distinct for clarity and analytics.

### AI Jobs

AI generation should be observable and durable enough to recover from failures.

Suggested fields:

- `job_id`
- `world_id`
- `player_id`
- `target_object_id`
- `job_type` = `create | refine | remix`
- `status` = `pending | running | completed | failed | expired`
- `prompt_text`
- `requested_at`
- `completed_at`
- `error_code`

Notes:

- This can start minimal in V1.
- Even a small job table helps with latency handling and stuck generations.

### World Snapshots

Resettable worlds need stable archive records.

Suggested fields:

- `snapshot_id`
- `world_id`
- `cycle_number`
- `created_at`
- `reason` = `manual_reset | scheduled_reset`

### Snapshot Objects

Suggested fields:

- `snapshot_id`
- `object_id`
- frozen object record
- frozen object spec payload

Notes:

- Archive snapshots should be immutable.
- V1 does not need social interaction inside archives.

## Key reducers

### World reducers

- `create_world`
- `join_world`
- `leave_world`
- `set_world_rules`
- `heartbeat_player`
- `move_player`

### Object creation reducers

- `request_create_object`
- `submit_ai_draft`
- `update_draft_transform`
- `release_object`

### Remix and edit reducers

- `request_edit_lock`
- `submit_object_edit`
- `cancel_edit`
- `delete_object`

### Lifecycle and timer reducers

- `expire_grace_period`
- `expire_edit_lock`
- `expire_cooldown`

### Snapshot reducers

- `create_snapshot`
- `reset_world`

## Subscription model

Each connected client should subscribe to a small set of world-scoped records:

- the current `world` row,
- active `players` in the world,
- live `objects` in the world,
- active `object_locks`,
- recent `ai_jobs` created by that player,
- snapshot summary metadata when needed.

V1 should avoid broad global subscriptions.

## Validation rules

Reducers should enforce the rules documented elsewhere in the idea bundle.

Public world requirements:

- regular players may create new objects,
- regular players may remix public objects,
- regular players may not make destructive edits,
- only one player may edit an existing public object at a time,
- successful edits trigger cooldown.

Private world requirements:

- destructive edits may be enabled,
- experimentation can be looser,
- lock and lifecycle rules can remain simpler but should still be explicit.

Object creation requirements:

- new object starts in `draft` or `grace`,
- creator owns the object during grace period,
- object becomes public when grace expires or is released,
- edits against stale object versions should be rejected.

## AI integration

The AI worker should:

- accept prompt text and world context,
- generate constrained `prompt_ir`,
- validate against allowed size, shape, material, and behavior grammar,
- produce a deterministic `builder_spec`,
- submit the resulting payload through trusted reducers.

The AI worker should not:

- bypass world permissions,
- mutate world state directly,
- define final object lifecycle rules.

## V1 simplifications

To keep the first prototype small, V1 should not include:

- direct terrain editing,
- trusted builder roles,
- complex scripting,
- deep account identity,
- rich inventory or economy systems,
- advanced server-side physics authority.

## Recommended next follow-up docs

- `world-settings-schema.md`
- `object-state-machine.md`
- `prompt-ir-spec.md`
- `public-world-permission-matrix.md`
- `prototype-v1-scope.md`

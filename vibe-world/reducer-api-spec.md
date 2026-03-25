# Reducer API Spec

_Drafted: March 24, 2026_

## Purpose

This document defines the first high-level reducer surface for the Vibe World V1 backend.

The goal is not to lock down final code signatures yet.
The goal is to make the authoritative state transitions concrete enough that implementation can be broken into milestone tickets.

## Design principles

- Reducers are the only path for authoritative state changes.
- Reducers should validate permissions, lifecycle state, and object version.
- Reducers should be small, explicit, and easy to reason about.
- Expiry-based transitions should be handled by explicit timer-driven reducers, not hidden client behavior.

## Reducer groups

### World and player reducers

- `create_world`
- `join_world`
- `leave_world`
- `heartbeat_player`
- `move_player`
- `set_world_rules`

### Object creation and grace reducers

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

## Core reducer definitions

### `create_world`

Purpose:

- create a new public or private world using a preset and initial settings

Inputs:

- `name`
- `template_id`
- `visibility`
- `rule_preset`
- `persistence_mode`
- `reset_interval_seconds`
- `destructive_edits_enabled`
- `object_cooldown_seconds`
- `protected_spawn_enabled`
- `max_players`
- host session identity

Validations:

- world settings must pass schema validation
- public worlds cannot start with invalid destructive defaults
- max players must stay within platform cap

State changes:

- insert world row
- insert host player row

### `join_world`

Purpose:

- let an anonymous player join a live world

Inputs:

- `world_id`
- temporary nickname
- session/connection identity

Validations:

- world must exist
- world must accept joins
- nickname must be valid
- player count must be below cap

State changes:

- insert or reactivate player row

### `leave_world`

Purpose:

- cleanly disconnect a player from live presence

Inputs:

- `player_id`
- session identity

State changes:

- mark player disconnected or remove player row depending on retention policy
- release active edit lock if needed

### `heartbeat_player`

Purpose:

- keep a player session alive

Inputs:

- `player_id`
- timestamp or server-time context

State changes:

- update `last_seen_at`

### `move_player`

Purpose:

- update authoritative player transform

Inputs:

- `player_id`
- `position`
- `rotation`

Validations:

- player must be active in the world
- transform must stay within reasonable bounds

State changes:

- update player transform

### `set_world_rules`

Purpose:

- allow the host to change host-configurable V1 settings

Inputs:

- `world_id`
- partial world settings patch
- host identity

Validations:

- caller must be host
- patched values must pass schema validation

State changes:

- update world settings row

## Object creation and grace reducers

### `request_create_object`

Purpose:

- register the player's intent to create an object and create an AI job

Inputs:

- `world_id`
- `player_id`
- `source_prompt`
- optional placement hint

Validations:

- world must allow creation
- player must pass rate limits
- player must not exceed object caps

State changes:

- insert AI job row in `pending`

Notes:

- this reducer should not create the object yet if the system requires AI output first

### `submit_ai_draft`

Purpose:

- create the authoritative draft object from validated AI output

Inputs:

- trusted worker identity
- `job_id`
- `prompt_ir`
- `builder_spec`
- optional `render_spec`

Validations:

- job must exist and still be valid
- payload must pass IR and builder validation
- target player and world must still be eligible

State changes:

- insert object row in `draft`
- insert object spec row
- update AI job to `completed`
- transition object into `grace` immediately or via follow-up reducer
- create grace lock

### `update_draft_transform`

Purpose:

- let the creator move, scale, or rotate the object during grace period

Inputs:

- `object_id`
- `player_id`
- partial transform update

Validations:

- object must be in `grace`
- caller must be the grace owner

State changes:

- update object transform

### `release_object`

Purpose:

- end grace period early and make the object public

Inputs:

- `object_id`
- `player_id`

Validations:

- object must be in `grace`
- caller must be the grace owner or host with override authority

State changes:

- transition object to `public`
- clear grace lock

## Remix and edit reducers

### `request_edit_lock`

Purpose:

- acquire exclusive edit access on a public object

Inputs:

- `object_id`
- `player_id`
- `base_object_version`

Validations:

- object must be in `public`
- no active conflicting lock may exist
- caller must be allowed to remix

State changes:

- transition object to `edit_locked`
- create edit lock row

### `submit_object_edit`

Purpose:

- apply a validated non-destructive or destructive edit depending on world rules

Inputs:

- `object_id`
- `player_id`
- `base_object_version`
- `prompt_ir`
- `builder_spec`
- optional `render_spec`

Validations:

- caller must own the active edit lock
- object version must match
- edit must satisfy world permissions
- destructive edits must be rejected in public worlds for normal players

State changes:

- update object row and spec row
- increment version
- set latest editor
- clear edit lock
- transition to `cooldown` when required

### `cancel_edit`

Purpose:

- abandon an active edit without changing the object

Inputs:

- `object_id`
- `player_id`

Validations:

- caller must own the active lock

State changes:

- clear edit lock
- return object to `public`

### `delete_object`

Purpose:

- remove a live object when destructive permissions allow it

Inputs:

- `object_id`
- `player_id`

Validations:

- caller must have delete authority in the current world
- archive objects may not be deleted through this reducer

State changes:

- transition object to `deleted`
- clear any active lock

## Timer reducers

### `expire_grace_period`

Purpose:

- end grace period when the timer finishes

Inputs:

- `object_id`

Validations:

- object must still be in `grace`

State changes:

- transition object to `public`
- clear grace lock

### `expire_edit_lock`

Purpose:

- release inactive edit locks

Inputs:

- `object_id`

Validations:

- object must still be in `edit_locked`

State changes:

- clear edit lock
- return object to `public`

### `expire_cooldown`

Purpose:

- end post-edit cooldown

Inputs:

- `object_id`

Validations:

- object must still be in `cooldown`

State changes:

- transition object to `public`

## Snapshot reducers

### `create_snapshot`

Purpose:

- freeze the current live world state into archive records

Inputs:

- `world_id`
- reason

State changes:

- insert snapshot row
- copy live objects into snapshot storage

### `reset_world`

Purpose:

- wipe the live world after snapshot when world rules require reset

Inputs:

- `world_id`
- reason

Validations:

- caller must be host or system timer authority

State changes:

- create snapshot when required
- remove or mark deleted all live objects in the world
- start next live cycle

## Error model

Reducers should fail clearly on:

- permission denied
- invalid world state
- stale object version
- invalid payload
- rate limit exceeded
- object already locked
- object not found

## Recommended related docs

- `spacetimedb-v1-schema.md`
- `object-state-machine.md`
- `prompt-ir-spec.md`
- `ai-worker-contract.md`

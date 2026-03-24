# World Settings Schema

_Drafted: March 24, 2026_

## Purpose

This document defines the first configurable world settings model for Vibe World.

The goal of V1 is not to expose unlimited rule programming.
The goal is to support:

- hosted public and private worlds,
- a small set of world presets,
- a few important rule toggles,
- settings that map cleanly to authoritative multiplayer enforcement.

## Design principles

- Prefer presets plus a few toggles over freeform rule logic.
- Keep public/private differences explicit.
- Keep settings small enough that hosts understand them quickly.
- Only expose settings that the backend can enforce cleanly in V1.

## Top-level schema

Suggested V1 fields:

- `world_id`
- `name`
- `template_id`
- `visibility`
- `rule_preset`
- `persistence_mode`
- `reset_interval_seconds`
- `destructive_edits_enabled`
- `remix_others_objects_enabled`
- `object_cooldown_seconds`
- `protected_spawn_enabled`
- `max_players`
- `created_at`
- `updated_at`

## Field definitions

### `name`

Type:

- string

Rules:

- required
- short human-readable world title

### `template_id`

Type:

- enum or template identifier

Suggested V1 values:

- `floating_island`
- `cozy_room`
- `plaza`
- `obstacle_island`
- `empty_terrain`
- `social_lounge`

Notes:

- V1 can ship with one or two templates even if the schema leaves room for more.

### `visibility`

Type:

- `public | private`

Meaning:

- `public` worlds are discoverable and use non-destructive public remix rules
- `private` worlds are invite-only or restricted and may allow more chaos

### `rule_preset`

Type:

- preset identifier

Suggested V1 values:

- `cozy_public`
- `collaborative_remix`
- `curated_showcase`
- `private_chaos`
- `friends_build_night`

Notes:

- A preset should seed sensible defaults rather than act as an opaque mode.

### `persistence_mode`

Type:

- `permanent | temporary | scheduled_reset`

Meaning:

- `permanent`: world persists until manually reset
- `temporary`: world is disposable and short-lived
- `scheduled_reset`: world resets on a cadence and archives previous cycles

### `reset_interval_seconds`

Type:

- nullable integer

Rules:

- required when `persistence_mode = scheduled_reset`
- null otherwise

Suggested V1 examples:

- `3600`
- `86400`
- `604800`
- `2592000`

### `destructive_edits_enabled`

Type:

- boolean

Rules:

- default `false` for public worlds
- may be `true` for private worlds

Meaning:

- when enabled, permitted players may delete or destructively alter objects

### `remix_others_objects_enabled`

Type:

- boolean

Rules:

- `true` by default for public worlds in V1

Meaning:

- controls whether players can modify other players' released objects at all

Notes:

- V1 public worlds should usually keep this enabled because remixing is central to the concept.

### `object_cooldown_seconds`

Type:

- integer

Suggested V1 values:

- `10`
- `30`
- `60`

Recommended default:

- `30`

### `protected_spawn_enabled`

Type:

- boolean

Meaning:

- enables a small protected host-controlled welcome zone

### `max_players`

Type:

- integer

Suggested V1 values:

- `8`
- `16`
- `20`
- `32`

Recommended V1 target:

- `20`

## Preset defaults

### `cozy_public`

- `visibility = public`
- `destructive_edits_enabled = false`
- `remix_others_objects_enabled = true`
- `object_cooldown_seconds = 30`
- `protected_spawn_enabled = true`

### `collaborative_remix`

- `visibility = public`
- `destructive_edits_enabled = false`
- `remix_others_objects_enabled = true`
- `object_cooldown_seconds = 30`
- `protected_spawn_enabled = false`

### `curated_showcase`

- `visibility = public`
- `destructive_edits_enabled = false`
- `remix_others_objects_enabled = true`
- `object_cooldown_seconds = 60`
- `protected_spawn_enabled = true`

### `private_chaos`

- `visibility = private`
- `destructive_edits_enabled = true`
- `remix_others_objects_enabled = true`
- `object_cooldown_seconds = 10`
- `protected_spawn_enabled = false`

### `friends_build_night`

- `visibility = private`
- `destructive_edits_enabled = true`
- `remix_others_objects_enabled = true`
- `object_cooldown_seconds = 30`
- `protected_spawn_enabled = false`

## Validation rules

The backend should enforce:

- public worlds cannot default to destructive editing in V1
- scheduled reset requires a reset interval
- temporary worlds should not require archive cadence
- max players must stay within allowed platform caps
- only host-level authority may change world settings after creation

## Host-configurable vs system-managed

### Host-configurable in V1

- world name
- template
- visibility
- preset
- persistence mode
- reset cadence
- destructive edits
- cooldown duration
- protected spawn toggle
- max players

### System-managed in V1

- world id
- timestamps
- archive counters
- live cycle state
- platform safety limits

## Relationship to backend model

These settings should map directly to authoritative reducers and validations.

Important downstream effects:

- `visibility` affects discovery and social expectations
- `destructive_edits_enabled` affects delete and destructive edit permissions
- `object_cooldown_seconds` affects object lifecycle timers
- `persistence_mode` and `reset_interval_seconds` affect snapshot scheduling
- `protected_spawn_enabled` affects placement and edit restrictions in spawn zones

## V1 simplifications

To keep the first implementation manageable:

- do not expose fully custom permission scripting
- do not expose per-zone rules beyond optional protected spawn
- do not support trusted builder custom roles yet
- do not support per-object exceptions in the host UI

## Recommended related docs

- `public-world-permission-matrix.md`
- `object-state-machine.md`
- `spacetimedb-v1-schema.md`
- `prototype-v1-scope.md`

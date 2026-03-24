# Prompt IR Spec

_Drafted: March 24, 2026_

## Purpose

This document defines the first **prompt intermediate representation** for Vibe World.

The IR is the boundary between:

- player intent expressed in natural language or command-like input,
- authoritative object creation and remixing in the multiplayer backend.

The IR exists so the system does not depend on:

- raw unconstrained 3D geometry generation,
- direct AI writes into live world state,
- arbitrary scripts,
- dense manual modeling semantics.

## Design principles

- AI should output constrained intention, not final authority.
- The IR should be easy to validate.
- The IR should align with a voxel-native, chunky object grammar.
- The IR should support rough drafts first, refinement second.
- Lifecycle and permission decisions stay outside the IR.

## V1 scope

The V1 IR should support:

- creating a new object,
- refining a draft object,
- remixing an existing public object non-destructively,
- deleting or destructive actions only through server-side permission logic in private worlds.

The V1 IR should not support:

- direct terrain edits,
- arbitrary behavior scripts,
- unrestricted physics authoring,
- freeform mesh dumps,
- full game logic programming.

## Top-level IR shape

Suggested top-level fields:

- `ir_version`
- `request_id`
- `operation`
- `source_prompt`
- `target_world_id`
- `target_object_id`
- `base_object_version`
- `object_intent`
- `safety`

Definitions:

- `operation`: `create | refine | remix`
- `target_object_id`: required for `refine` and `remix`
- `base_object_version`: required when editing an existing object

## Object intent

`object_intent` should describe the object at a gameplay-meaning level.

Suggested fields:

- `category`
- `size_tier`
- `parts`
- `material_palette`
- `behavior_presets`
- `transform_hints`
- `style_tags`

### Category

Suggested V1 categories:

- `prop`
- `furniture`
- `foliage`
- `light`
- `structure`
- `sign`
- `landmark`
- `toy`

### Size tier

Allowed V1 tiers:

- `tiny`
- `small`
- `medium`
- `large`
- `huge`

Notes:

- `huge` can be reserved for host or curated flows later even if the enum exists in V1.

### Parts

Each object should be decomposable into chunky recognizable parts.

Each part should allow:

- `part_id`
- `primitive`
- `dimensions`
- `material`
- `modifiers`
- `attachment`

Allowed V1 primitives:

- `cube`
- `slab`
- `column`
- `stair`
- `wedge`
- `arch`
- `platform`
- `blob`

Suggested modifier vocabulary:

- `taller`
- `wider`
- `hollow`
- `roof`
- `windows`
- `lanterns`
- `pillars`
- `spikes`
- `legs`
- `rounded_blocky`

### Material palette

Allowed V1 materials:

- `stone`
- `moss_stone`
- `neon`
- `glass_block`
- `jelly`
- `cloud`
- `wood`
- `lava_light`
- `void`

The IR should allow:

- one dominant material
- optional accent materials

### Behavior presets

Allowed V1 behavior presets:

- `glow`
- `bob`
- `pulse`
- `spin`
- `bounce`
- `open_close`
- `hover`

Notes:

- Behaviors are presets, not scripts.
- Server validation should cap behavior complexity.

### Transform hints

The IR may suggest:

- spawn position hint
- snap mode
- approximate orientation
- approximate footprint

Notes:

- Final placement authority stays with the game rules and the creator during grace period.

### Style tags

Optional style tags can help preserve vibe without breaking validation.

Examples:

- `cozy`
- `playful`
- `surreal`
- `neon`
- `ruined`
- `mossy`
- `soft_glow`
- `chunky`

## Safety block

Suggested `safety` fields:

- `destructive_intent`
- `risk_flags`
- `estimated_complexity`
- `estimated_part_count`

Purpose:

- support moderation and rule enforcement before live state mutation
- prevent oversized or spammy object generation

## Operation semantics

### `create`

Meaning:

- produce a new rough-draft object intent

Rules:

- must not reference an existing target object
- should produce a complete enough draft for immediate grace-period visibility

### `refine`

Meaning:

- modify the creator-owned draft or currently editable object without changing its identity

Rules:

- must target an existing object
- must include `base_object_version`
- should preserve recognizable continuity with the current object unless the system explicitly allows larger changes

### `remix`

Meaning:

- modify an existing public object in a way that stays within public-world non-destructive rules

Rules:

- must target an existing public object
- must include `base_object_version`
- server must reject destructive changes in public worlds even if the IR suggests them

## Validation rules

The validator should reject IR payloads that:

- exceed allowed size tiers,
- use unknown primitives,
- use unknown materials,
- use unapproved behavior presets,
- attempt terrain operations,
- attempt arbitrary scripting,
- target stale object versions,
- imply destructive edits in a public world.

## Builder boundary

The IR is not the final live object representation.

The conversion flow is:

**prompt -> IR -> validated builder spec -> authoritative object state**

The builder spec should make implicit choices explicit, such as:

- exact dimensions,
- exact part arrangement,
- exact material assignment,
- exact transform defaults.

## Example: create

Example user prompt:

> make a cozy mushroom house with glowing windows

Example V1 IR:

```json
{
  "ir_version": "v1",
  "request_id": "req_123",
  "operation": "create",
  "source_prompt": "make a cozy mushroom house with glowing windows",
  "target_world_id": "world_1",
  "target_object_id": null,
  "base_object_version": null,
  "object_intent": {
    "category": "structure",
    "size_tier": "medium",
    "parts": [
      {
        "part_id": "stem",
        "primitive": "column",
        "dimensions": { "height": "medium", "width": "small" },
        "material": "wood",
        "modifiers": ["rounded_blocky"],
        "attachment": null
      },
      {
        "part_id": "cap",
        "primitive": "blob",
        "dimensions": { "height": "medium", "width": "large" },
        "material": "moss_stone",
        "modifiers": ["roof"],
        "attachment": { "attach_to": "stem", "mode": "top" }
      },
      {
        "part_id": "windows",
        "primitive": "slab",
        "dimensions": { "height": "small", "width": "small" },
        "material": "glass_block",
        "modifiers": ["windows", "lanterns"],
        "attachment": { "attach_to": "stem", "mode": "side_repeat" }
      }
    ],
    "material_palette": {
      "primary": "wood",
      "accents": ["moss_stone", "glass_block"]
    },
    "behavior_presets": ["glow"],
    "transform_hints": {
      "footprint": "medium",
      "orientation": "free"
    },
    "style_tags": ["cozy", "chunky", "soft_glow"]
  },
  "safety": {
    "destructive_intent": false,
    "risk_flags": [],
    "estimated_complexity": "medium",
    "estimated_part_count": 3
  }
}
```

## Example: refine

Example user prompt:

> make it taller and add a little chimney

Example V1 IR:

```json
{
  "ir_version": "v1",
  "request_id": "req_124",
  "operation": "refine",
  "source_prompt": "make it taller and add a little chimney",
  "target_world_id": "world_1",
  "target_object_id": "obj_99",
  "base_object_version": 4,
  "object_intent": {
    "category": "structure",
    "size_tier": "medium",
    "parts": [
      {
        "part_id": "stem",
        "primitive": "column",
        "dimensions": { "height": "larger_than_current", "width": "same" },
        "material": "wood",
        "modifiers": ["taller"],
        "attachment": null
      },
      {
        "part_id": "chimney",
        "primitive": "column",
        "dimensions": { "height": "small", "width": "tiny" },
        "material": "stone",
        "modifiers": [],
        "attachment": { "attach_to": "cap", "mode": "top_offset" }
      }
    ],
    "material_palette": {
      "primary": "wood",
      "accents": ["moss_stone", "stone"]
    },
    "behavior_presets": ["glow"],
    "transform_hints": {},
    "style_tags": ["cozy", "chunky"]
  },
  "safety": {
    "destructive_intent": false,
    "risk_flags": [],
    "estimated_complexity": "medium",
    "estimated_part_count": 2
  }
}
```

## V1 simplifications

To keep the first IR manageable:

- keep the vocabulary small and hand-curated
- prefer semantic dimensions over full numeric geometry in the IR
- let the builder resolve exact voxel/native dimensions
- keep advanced behaviors and terrain operations out of scope

## Recommended next follow-up docs

- `object-state-machine.md`
- `world-settings-schema.md`
- `public-world-permission-matrix.md`
- `spacetimedb-v1-schema.md`
- `prototype-v1-scope.md`

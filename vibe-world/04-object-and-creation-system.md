# Object and Creation System

## Core object philosophy

Objects should be:

- chunky,
- clearly voxel-based,
- quick to create,
- easy to read in multiplayer,
- designed for remixing rather than perfection.

The system should avoid becoming a multiplayer CAD tool.

## Visual style choice

The current direction is explicitly:

- **blocky/chunky and obviously voxel-based**.

Not smoothed.
Not hidden.
Not pretending to be high-detail mesh art.

This supports:

- lower creation friction,
- faster comprehension,
- more legible social editing,
- stronger art direction.

## Prompt-first creation

Object editing is primarily prompt-driven.

The main ways to create or change objects are:

- vibe prompts,
- simple terminal/command input,
- light transform controls.

### What is intentionally not primary

The system should not primarily rely on:

- voxel-by-voxel manual sculpting,
- dense brush painting,
- intricate low-level carving,
- traditional manual 3D authoring workflows.

## Rough-draft generation model

When a player types a prompt such as:

> make a cozy mushroom house

The system should create a **rough draft first**, not a polished final result.

The player then refines it with short follow-up prompts, such as:

- make it taller,
- add glowing windows,
- make the roof steeper,
- use moss stone,
- add a little chimney.

### Why rough drafts are better

Rough drafts:

- lower user expectation pressure,
- make iteration part of the fun,
- tolerate weirdness better,
- show creative process in public,
- reduce the need for one-shot perfection.

## New object lifecycle

### Step 1 — Spawn

The player creates an object by prompt or terminal command.

### Step 2 — Grace period

The object appears and enters a **creator-only grace period**.

During that time, the creator can:

- move it in X/Y/Z,
- resize it,
- optionally rotate it,
- refine it through follow-up prompts,
- adjust it with terminal commands.

### Step 3 — Auto-release

The grace period ends on a **fixed timer**.

Then the object becomes public and remixable under the normal world rules.

## Existing object editing

Once an object is public, it uses the normal public edit lock system:

- one editor at a time,
- inactivity timeout,
- 30-second cooldown after successful edit.

## Terminal / command mode

The terminal mode should give technical players a more precise interface, but remain highly constrained.

This should behave more like a world-specific command DSL than arbitrary general-purpose code.

### Example style

```txt
spawn tower small at 8 0 3
material moss_stone
add windows 3
add roof pointed
behavior glow soft
```

The purpose of terminal mode is precision and composability, not unrestricted scripting power.

## Recommended object constraints

To keep experimentation fun and low-friction, object creation should likely be constrained by:

- size tiers,
- shape grammar,
- material palette,
- behavior presets,
- transform snapping,
- object count / rate limits.

### Size tier examples

- tiny = prop
- small = decoration or furniture
- medium = structure piece
- large = landmark
- huge = likely restricted to hosts or curated flows

## Suggested shape vocabulary

Rather than freeform geometry, the system should be good at assembling and modifying recognizable chunky forms.

### Example primitives

- cube,
- slab,
- column,
- stair,
- wedge,
- arch,
- platform,
- blob.

### Example modifications

- make taller,
- make wider,
- make hollow,
- add roof,
- add windows,
- add lanterns,
- split into pillars,
- add spikes,
- add legs,
- round slightly within blocky style.

## Material vocabulary

A limited but vivid material set can create strong variety without extra complexity.

### Example chunky materials

- stone,
- moss stone,
- neon,
- glass block,
- jelly,
- cloud,
- wood,
- lava light,
- void.

## Behavior presets

Behavior should also start as simple presets rather than arbitrary scripts.

### Example presets

- glow,
- bob,
- pulse,
- spin,
- bounce,
- open/close,
- hover.

## Design principle

Players should edit by **intention**, not by craftsmanship.

The system should reward:

- idea generation,
- social remixing,
- fast iteration,
- atmospheric expression.

It should not require:

- fine manual dexterity,
- detailed low-level modeling skill,
- long placement sessions for basic objects.

## Best V1 interaction loop

1. pick a place,
2. prompt an object,
3. rough chunky draft appears,
4. move/scale it during grace period,
5. refine with short follow-up prompts,
6. grace period ends,
7. object becomes public.

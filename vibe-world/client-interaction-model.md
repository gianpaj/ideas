# Client Interaction Model

_Drafted: March 24, 2026_

## Purpose

This document defines the first player-facing interaction model for the Vibe World client.

The goal of V1 is to make the main loop legible:

- enter a world
- move around with other players
- prompt a rough-draft object into existence
- refine it during grace period
- release it into the shared sandbox
- remix existing objects under clear rules

## Design principles

- The primary loop should feel social and immediate.
- The client should reflect authoritative state clearly.
- The UI should show permissions and lifecycle state without requiring guesswork.
- Prompt-first creation should feel easier than manual building.

## Entry flow

### World creation

The host flow should be simple:

1. choose a template
2. name the world
3. choose public or private
4. choose a preset
5. launch

V1 client requirements:

- compact world creation panel
- clear preset explanations
- obvious private vs public distinction

### Joining a world

Normal players should:

1. pick or receive a world
2. choose a temporary nickname
3. enter the world quickly

V1 client requirements:

- fast join flow
- no account wall
- immediate presence in the room

## Core live HUD

V1 should keep a small HUD that communicates the minimum needed state.

Recommended persistent elements:

- current world name
- world mode: public or private
- player nickname
- lightweight player count
- create prompt entry point
- current object action state when relevant

## Movement and presence

The client should support:

- walking around the shared space
- seeing other players
- understanding who is nearby

Presence cues should be light.
V1 does not need heavy social UI before the creation loop works.

## Creation flow

### Step 1: choose a place

The player moves to a location and decides where to create.

The client should help with:

- rough placement sense
- spawn area restrictions if enabled
- basic placement hinting

### Step 2: enter a prompt

The player opens a prompt entry UI and types a short instruction.

Examples:

- `make a cozy mushroom house`
- `add a neon sign here`
- `make a little floating lantern`

The prompt UI should:

- stay lightweight
- encourage short, intention-level prompts
- make follow-up prompts feel normal

### Step 3: generation feedback

While the AI job is running, the client should show:

- generation in progress
- which object request belongs to the player
- failure state if generation does not complete

V1 does not need elaborate progress bars if state is clear.

### Step 4: grace period editing

Once the draft appears, the creator can:

- move it
- scale it
- optionally rotate it if cheap enough
- refine it with short follow-up prompts

The client should show:

- grace period countdown
- creator ownership clearly
- transform controls only for the creator
- visible but unavailable state for other players

### Step 5: release

The object becomes public when:

- the grace timer ends
- or the creator releases it early

The client should show:

- release action if allowed
- transition from creator-only to public state
- clear end of protected ownership

## Public object remix flow

For existing public objects, the interaction loop should be:

1. inspect object
2. request edit lock
3. edit if granted
4. submit or cancel
5. object enters cooldown if edit succeeds

The client must show:

- whether object is available
- who currently holds the lock
- whether object is in cooldown
- whether edit is forbidden because the world is public and the action is destructive

## Private-world destructive flow

In private worlds, the client may expose destructive actions when room rules allow them.

V1 requirements:

- destructive tools should never look available in public worlds
- destructive actions should feel clearly riskier
- host/world rule differences should be visible in the UI

## Object inspection

Inspect mode should expose:

- object name or summary
- latest editor
- original creator
- current lifecycle state
- cooldown or lock status

Deeper inspection may include:

- edit history
- version number
- underlying style or material summary

## Failure states

The client should handle:

- generation failure
- stale edit rejection
- lost lock
- cooldown denial
- reconnect after disconnect

The user should always get a clear answer:

- try again
- wait
- object changed
- you no longer own this edit

## Archive mode handoff

Archive mode should feel distinct from live mode.

The client should:

- make read-only status obvious
- suppress create/edit controls
- preserve movement and exploration
- show snapshot identity and age

## V1 simplifications

To keep the client small:

- no complex inventory UI
- no advanced social profile UI
- no deep asset browser
- no per-object scripting panels
- no terrain editing controls

## Recommended related docs

- `prototype-v1-scope.md`
- `object-state-machine.md`
- `public-world-permission-matrix.md`
- `archive-ux-spec.md`

# Archive UX Spec

_Drafted: March 24, 2026_

## Purpose

This document defines the first user experience for archived world snapshots in Vibe World.

The archive system is not just storage.
It is part of the product fantasy:

- a world memory
- a frozen record of past live cycles
- a space players can revisit without changing

## Design principles

- Archive mode should feel clearly different from live mode.
- Archive mode should feel atmospheric, not administrative.
- Read-only rules must be obvious.
- The archive should preserve place and mood, not turn into a content forum.

## What archive mode is

Archive mode is:

- read-only
- explorable
- frozen in time
- tied to a prior live cycle

Archive mode is not:

- editable
- reactive
- social-media-like
- a moderation panel

## Entry points

V1 may allow archive access through:

- world browser entry
- host world page
- in-world portal or terminal option later

The entry should show:

- snapshot timestamp
- world name
- cycle number if relevant
- whether the snapshot came from manual or scheduled reset

## Core archive experience

When a player enters archive mode, they should immediately understand:

- this is not the live world
- nothing here can be changed
- this is a preserved memory of a prior state

The UI should communicate:

- snapshot title
- timestamp or age
- read-only status
- simple exit path back to live mode or browser

## Visual treatment

Archive mode should feel distinct but not cheap.

Suggested V1 cues:

- subtle desaturation or color shift
- softer fog or atmosphere
- timestamp overlay
- “archive” or “memory” label in HUD

The effect should say:

- preserved
- quiet
- historical

It should not say:

- broken
- disabled
- debug mode

## Interaction rules

Players may:

- walk around
- look around
- inspect basic object info if allowed

Players may not:

- create objects
- edit objects
- delete objects
- react
- comment
- alter history

## Metadata exposure

V1 should keep archive metadata intentionally light.

Good metadata:

- world name
- snapshot time
- live cycle age
- snapshot reason

Avoid in-V1 archive clutter such as:

- full moderation logs
- reaction feeds
- comment systems
- overloaded per-object history panels

## Object presentation in archive mode

Objects should appear as they existed at snapshot time.

The archive should preserve:

- object placement
- object shape and material
- visible attribution defaults

The archive should not allow:

- lock acquisition
- grace period behavior
- cooldown behavior

Those are live-world mechanics and should be visually suppressed.

## Transition between live and archive

Moving from live mode to archive mode should feel intentional.

Recommended V1 pattern:

- explicit enter action
- clear mode switch
- clear exit action back to live mode or browser

The client should avoid making archive mode feel like lagged or stale live state.

## V1 simplifications

To keep the archive small and clear:

- no archive chat
- no archive reactions
- no archive editing
- no timeline scrubber across many snapshots yet
- no deep archaeology UI beyond simple metadata

## Product role

Archive mode helps the product because it:

- makes resets feel meaningful instead of destructive-only
- turns world cycles into culture and memory
- gives players a reason to revisit old worlds
- makes ephemerality feel intentional

## Recommended related docs

- `02-core-game-rules.md`
- `03-worlds-hosting-and-governance.md`
- `prototype-v1-scope.md`
- `client-interaction-model.md`

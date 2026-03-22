# Core Game Rules

This document captures the current rules agreed so far.

## 1. World types

### Public worlds

Public worlds are collaborative, remixable, and relatively stable.

Regular players can:

- create new objects,
- remix public objects,
- make non-destructive changes,
- explore archived snapshots.

Regular players cannot:

- make destructive edits,
- erase or collapse public structures,
- remove critical world access,
- force dangerous large-scale changes.

### Private worlds

Private worlds are much looser and more chaotic.

They can allow:

- destructive editing,
- faster experimentation,
- fewer social constraints,
- playful grief-with-consent among friends.

## 2. Public object remixing

In public worlds:

- all public objects are remixable,
- remixing must remain non-destructive,
- the world is socially shared rather than strongly owner-protected.

This means objects are treated more like public clay than permanent personal property.

## 3. Object edit exclusivity

Only one player can edit an existing public object at a time.

### Existing public object edit flow

1. player begins editing,
2. object is locked exclusively to that player,
3. if the player goes inactive, the lock expires automatically,
4. if the edit is accepted, the object enters a 30-second lock before the next edit,
5. once that lock ends, another player may edit.

### Idle timeout

If the editor goes inactive, the object should unlock automatically after a short timeout.

### Post-edit cooldown

After a successful edit, the object remains locked for **30 seconds** before anyone else can edit it.

## 4. Attribution

### Visible attribution

By default, an object shows the **latest editor** only.

### Deeper attribution

If inspected, the object can reveal:

- original creator,
- edit history,
- contributor trail,
- version metadata.

This keeps the visible world focused on the present, while retaining provenance underneath.

## 5. New object creation

Players may create brand-new objects anywhere in the world, subject to system-level safety and spam guardrails.

Creation can happen through:

- vibe prompts,
- a terminal/command-style creation interface.

### New object grace period

When a new object is created, it enters a **creator-only grace period**.

During this period:

- only the creator can edit it,
- the creator can move it across 3D space,
- the creator can resize it,
- the object is visible to others,
- the grace period ends automatically on a fixed timer.

After the grace period ends, the object becomes public and remixable under the normal rules.

## 6. Protected spawn / welcome area

A world may optionally include a **small protected spawn/welcome zone**.

This zone is:

- host-controlled,
- non-editable for regular players,
- intended for welcome text, rules, world identity, and orientation.

## 7. Persistence and resets

When a host creates a world, they choose one of the following:

- permanent,
- temporary,
- scheduled reset.

### Scheduled reset cadence examples

Possible reset schedules include:

- every hour,
- every 24 hours,
- every week,
- every month.

### Reset behavior

Resets are **real**.

When a reset occurs:

- the live editable world is wiped,
- nothing carries forward automatically,
- no automatic “best creations” survive into the next live cycle.

## 8. Archive / time machine mode

Reset worlds preserve prior live versions as **read-only explorable snapshots**.

Players can:

- enter old versions,
- walk around,
- experience them as frozen historical spaces.

Players cannot:

- edit,
- react,
- comment,
- inspect extra historical metadata while inside the archive.

The intended feeling is a world-memory or time-machine experience, not a content forum.

## 9. Current rules summary table

### Public world summary

- destructive edits by regular players: **no**
- object remixing: **yes**
- remixing others' objects: **yes**
- destructive changes to others' objects: **no**
- one editor at a time per object: **yes**
- inactivity timeout: **yes**
- 30-second post-edit cooldown: **yes**
- visible credit: **latest editor**
- deep history on inspect: **yes**
- optional protected spawn zone: **yes**
- object creation anywhere: **yes**
- new object grace period: **yes, fixed timer**

### Private world summary

- destructive edits: **can be on**
- world can be highly chaotic: **yes**
- looser experimentation: **yes**

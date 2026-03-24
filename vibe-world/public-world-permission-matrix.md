# Public World Permission Matrix

_Drafted: March 24, 2026_

## Purpose

This document defines the first permission matrix for Vibe World, with emphasis on public-world behavior in V1.

The main goal is clarity.
Players should understand:

- what they are allowed to do,
- what only hosts may do,
- what is forbidden in public worlds,
- how private worlds differ.

## V1 roles

The first prototype only needs a small role model.

### `host`

The creator and owner of the world.

### `player`

A normal participant in the live world.

### `archive_visitor`

A player exploring archived snapshots.

Notes:

- `archive_visitor` is a mode more than a permanent role.
- Moderator and trusted-builder roles can arrive later.

## Permission matrix

Legend:

- `yes`
- `no`
- `conditional`

## Live public world

| Action | Host | Player |
| --- | --- | --- |
| Create a new object | yes | yes |
| See other players' draft objects | yes | yes |
| Refine own object during grace period | yes | yes |
| Move/scale own object during grace period | yes | yes |
| Edit another player's grace-period object | no | no |
| Request edit lock on public object | yes | yes |
| Remix existing public object | yes | yes |
| Make destructive edits to public object | yes, platform constrained | no |
| Delete public object | yes, platform constrained | no |
| Change world settings | yes | no |
| Enable destructive editing | yes, if allowed by world type | no |
| Reset live world | yes | no |
| Explore archive snapshots | yes | yes |
| Edit archive snapshot | no | no |
| Inspect object history | yes | yes |

## Live private world

| Action | Host | Player |
| --- | --- | --- |
| Create a new object | yes | yes |
| See other players' draft objects | yes | yes |
| Refine own object during grace period | yes | yes |
| Move/scale own object during grace period | yes | yes |
| Edit another player's grace-period object | no | no |
| Request edit lock on public object | yes | yes |
| Remix existing released object | yes | yes |
| Make destructive edits | yes | conditional |
| Delete object | yes | conditional |
| Change world settings | yes | no |
| Reset live world | yes | no |
| Explore archive snapshots | yes | yes |
| Edit archive snapshot | no | no |
| Inspect object history | yes | yes |

Notes:

- `conditional` means allowed only if the room preset permits destructive editing.
- V1 should still keep grace-period ownership and explicit lifecycle rules in private worlds.

## Archive snapshot mode

| Action | Host | Archive Visitor |
| --- | --- | --- |
| Enter snapshot | yes | yes |
| Walk around | yes | yes |
| Edit object | no | no |
| Delete object | no | no |
| React/comment | no | no |
| Inspect extra live moderation metadata | no | no |

## Action notes

### Create a new object

Allowed for normal players in both public and private worlds, subject to:

- rate limits
- object count caps
- safety validation

### Grace-period editing

Only the creator may:

- refine the object
- move it
- scale it
- optionally rotate it

This remains true in both public and private worlds.

### Public object remixing

Released public objects are remixable.
In public worlds, remixing must remain non-destructive.

### Destructive edits

In V1:

- public-world destructive edits are forbidden for normal players
- private-world destructive edits may be allowed by room preset
- host actions still remain subject to platform safety and anti-crash constraints

### World settings

Only the host may:

- change the room preset
- change reset cadence
- enable or disable protected spawn
- change max players
- change destructive-edit settings

### Archives

Archives are read-only for everyone in V1.

Players may:

- enter old snapshots
- walk around
- experience frozen historical space

Players may not:

- edit
- delete
- comment
- react

## Enforcement model

These permissions should be enforced server-side, not just in UI.

Enforcement inputs include:

- world settings
- player role
- object lifecycle state
- lock ownership
- current world mode
- target object version

## V1 simplifications

To keep implementation manageable:

- do not add per-user ACLs
- do not add trusted-builder exceptions yet
- do not let archive mode inherit live-world permissions
- do not encode permissions separately in the client as source of truth

## Recommended related docs

- `world-settings-schema.md`
- `object-state-machine.md`
- `spacetimedb-v1-schema.md`
- `prototype-v1-scope.md`

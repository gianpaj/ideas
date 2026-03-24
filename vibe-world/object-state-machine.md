# Object State Machine

_Drafted: March 24, 2026_

## Purpose

This document defines the authoritative lifecycle for Vibe World objects in V1.

The object state machine exists to make multiplayer behavior predictable.
It should answer:

- who can edit an object right now,
- whether an object is still protected by grace period,
- whether a public object is currently locked,
- whether an object can be deleted,
- whether an object is live or frozen in archive state.

## Design principles

- The server is authoritative for all state transitions.
- Lifecycle state should be explicit, not inferred from loose flags.
- Public-world rules and private-world rules should share one model where possible.
- AI generation does not decide lifecycle state by itself.
- Archive copies are immutable.

## V1 states

### 1. `draft`

Meaning:

- the object has been accepted by the authoritative backend,
- the initial generated payload exists,
- the object is not yet fully exposed as a normal shared public object.

Who can edit:

- creator only

Typical entry:

- AI worker submits a validated initial draft

Typical exit:

- enters `grace`

Notes:

- V1 may collapse `draft` and `grace` into a single implementation if the transition is effectively immediate.
- It is still useful to keep `draft` as a conceptual state because generation completion and grace ownership are separate moments.

### 2. `grace`

Meaning:

- the object is visible in the world,
- only the creator may move, scale, rotate if allowed, or refine it,
- other players can see it but cannot take it over.

Who can edit:

- creator only

Typical entry:

- initial draft becomes visible in the live world

Typical exit:

- timer expires and object becomes `public`
- creator manually releases it early and object becomes `public`
- host or moderator removes it in a private/destructive context and object becomes `deleted`

### 3. `public`

Meaning:

- the object is live and remixable under normal world rules

Who can edit:

- any player allowed by world permissions and object rules

Typical entry:

- grace period ends
- cooldown expires
- edit lock is cancelled or expires without a committed edit

Typical exit:

- another player acquires edit access and object becomes `edit_locked`
- object is deleted in a private world or by host-level authority
- world snapshot freezes the object into an archived copy

### 4. `edit_locked`

Meaning:

- one player has the exclusive right to edit the object

Who can edit:

- lock owner only

Typical entry:

- player requests edit lock and the server grants it

Typical exit:

- accepted edit moves object to `cooldown`
- cancelled edit returns object to `public`
- inactivity timeout returns object to `public`
- host/moderator delete in a private/destructive context moves object to `deleted`

### 5. `cooldown`

Meaning:

- the object was successfully edited and is temporarily locked from further edits

Who can edit:

- no regular player

Typical entry:

- accepted public-world edit

Typical exit:

- cooldown timer expires and object returns to `public`

Notes:

- The agreed V1 default is 30 seconds for public objects.
- Private worlds may choose shorter or looser settings later, but V1 can still use the same state.

### 6. `archived`

Meaning:

- this is a frozen historical copy of an object inside a snapshot

Who can edit:

- nobody

Typical entry:

- world reset or archive capture

Typical exit:

- none; `archived` is terminal for the snapshot copy

Notes:

- The live object may be deleted or reset while the archived copy remains explorable.
- Archive copies should not accept reactions, comments, or edits in V1.

### 7. `deleted`

Meaning:

- the live object no longer exists as an editable entity

Who can edit:

- nobody

Typical entry:

- host/moderator deletion
- private-world destructive edit
- world reset wiping live state

Typical exit:

- none; create a new object instead of reviving deleted state

## State transition summary

Primary live flow:

`draft -> grace -> public -> edit_locked -> cooldown -> public`

Alternative live flow:

`draft -> grace -> public`

Archive flow:

`public -> archived`

Private destructive flow:

`grace -> deleted`

`public -> deleted`

`edit_locked -> deleted`

## Transition rules

### Create flow

1. player submits prompt or terminal-style create intent
2. AI worker generates validated draft payload
3. server creates object in `draft`
4. server transitions object to `grace`
5. creator may refine and transform during grace period
6. grace timer expires or creator releases early
7. object transitions to `public`

### Existing public object remix flow

1. player requests lock on a `public` object
2. server grants lock if object is available
3. object transitions to `edit_locked`
4. player submits prompt-based or constrained edit
5. server validates version and permissions
6. if accepted, object transitions to `cooldown`
7. cooldown expires
8. object returns to `public`

### Cancel or stale edit flow

1. object is `edit_locked`
2. player disconnects, times out, cancels, or submits invalid stale edit
3. server clears the lock
4. object returns to `public`

### Snapshot flow

1. world snapshot is created
2. frozen object copies are written into archive storage as `archived`
3. live world may continue or reset depending on world settings

## Public world rules

In public worlds:

- new objects are allowed
- remixing is allowed
- destructive edits are not allowed for regular players
- only one player may hold an edit lock on an existing public object
- accepted edit causes cooldown

## Private world rules

In private worlds:

- destructive edits may be enabled
- delete transitions may be allowed to normal players depending on the room preset
- the same lifecycle model still applies, but enforcement can be looser

## Timers

V1 should treat timers as authoritative server concerns.

Required timers:

- grace period duration
- edit inactivity timeout
- post-edit cooldown duration

Suggested defaults:

- grace period: fixed timer
- edit inactivity timeout: short timeout
- public cooldown: 30 seconds

## Versioning rules

Every live object should have a version number.

Rules:

- accepted edits increment version
- stale edits are rejected
- cooldown state still refers to the updated current version
- archive copies freeze the version they captured

## Visibility and attribution

Visible attribution:

- show latest editor by default

Inspectable attribution:

- original creator
- edit history
- contributor trail
- version metadata

## Reducer mapping

Suggested reducer-to-state mapping:

- `submit_ai_draft`: create `draft`
- `activate_grace_period`: `draft -> grace`
- `release_object`: `grace -> public`
- `expire_grace_period`: `grace -> public`
- `request_edit_lock`: `public -> edit_locked`
- `submit_object_edit`: `edit_locked -> cooldown`
- `cancel_edit`: `edit_locked -> public`
- `expire_edit_lock`: `edit_locked -> public`
- `expire_cooldown`: `cooldown -> public`
- `delete_object`: `grace|public|edit_locked -> deleted`
- `create_snapshot`: live object copy -> `archived`

## V1 simplifications

To keep the first prototype manageable:

- do not support terrain lifecycle here
- do not add soft-owner sub-states beyond current creator and latest editor
- do not treat archive browsing as a second editable world
- do not allow arbitrary user-authored scripted behavior to introduce new states

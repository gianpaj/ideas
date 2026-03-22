# Technical Architecture

## Architectural goal

Support a multiplayer world where many players can create and modify chunky voxel objects and environmental structures in near real time without the world collapsing into desync, grief, or unreadable chaos.

## Core architecture principles

### 1. Server-authoritative world state

The live world should be server-authoritative.

The server should:

- validate all world edits,
- apply accepted changes,
- assign object versions,
- enforce locks and permissions,
- broadcast authoritative deltas to clients.

This is especially important once AI-generated changes can affect geometry, physics, behavior, or large shared spaces.

### 2. Delta synchronization

The system should send **changes**, not full world snapshots, whenever possible.

Relevant examples:

- object created,
- object moved,
- object resized,
- material changed,
- behavior added,
- voxel patch applied,
- object released from grace period.

### 3. World/object versioning

Every world entity should have a version or revision marker.

This allows the server to reject or adapt edits that were generated against stale world state.

### 4. Clear object lifecycle states

The object model should likely include states such as:

- draft,
- grace period,
- public editable,
- edit-locked,
- cooldown locked,
- archived snapshot instance.

## Multiplayer conflict handling

### Existing public object conflicts

The agreed current public-world rule is simple:

- one player edits one object at a time,
- lock expires on inactivity,
- accepted edit causes 30-second cooldown.

This intentionally prioritizes clarity and simplicity over maximal concurrency.

### New object conflict handling

Newly spawned objects avoid immediate conflict through a creator-only grace period.

This prevents instant hijacking and gives the creator time to place and size the object.

## Recommended server-side object flow

### Create flow

1. client submits prompt or terminal command,
2. server parses request and checks permissions,
3. AI or rule system generates a rough draft object spec,
4. server instantiates draft object,
5. object enters grace period and is bound to creator,
6. creator transform deltas are accepted during grace period,
7. timer expires,
8. object becomes public.

### Edit flow

1. client requests edit lock,
2. server grants lock if object available,
3. player submits prompt-based edit request,
4. server generates or validates edit patch,
5. server applies patch,
6. world version increments,
7. server broadcasts delta,
8. object enters 30-second cooldown.

## AI pipeline recommendation

The most robust near-term architecture is:

**player intent → structured intermediate representation → deterministic voxel builder**

Not:

**player prompt → raw unconstrained 3D geometry dumped into world**

### Why

A structured pipeline is safer for:

- multiplayer consistency,
- moderation,
- rollback,
- rate limiting,
- cost control,
- deterministic-ish replication.

### Suggested intermediate representation

Instead of asking the model to output arbitrary geometry, it should output world-native instructions such as:

- object category,
- size tier,
- primitive selection,
- parts to add,
- material palette,
- simple behavior tags,
- transform hints.

Then the engine builds the voxel object from that spec.

## Chunked voxel world representation

Because the art direction is openly voxel-based, the world can likely be represented as a mixture of:

- chunked environmental voxel regions,
- discrete voxel-ish objects with metadata,
- simple behavior components,
- archive snapshots.

A practical architecture could separate:

- **world terrain / architecture voxels**,
- **spawned objects / props**,
- **behavior layer**,
- **presentation layer**.

## Why not rely on one giant text-to-3D model for everything

A fully unconstrained generative pipeline is a poor fit for the core gameplay loop because it creates problems in:

- predictability,
- latency,
- moderation,
- networking,
- rollback,
- object readability,
- conflict handling.

A constrained voxel grammar is much better aligned with the product.

## Archive system

Reset worlds need a dual representation:

### Live version

- editable,
- authoritative,
- current cycle,
- supports creation/remix.

### Archived version

- read-only,
- frozen state,
- walk-only,
- no editing or comments.

Technically, archive snapshots are best treated as stable immutable world versions.

## Permissions model

A clean permissions model could include:

- platform admin,
- host,
- moderator/co-host,
- trusted builder,
- regular player,
- visitor.

V1 does not need all of these exposed immediately, but the backend should probably leave room for them.

## Resource and safety guardrails

Even in permissive worlds, the platform should cap:

- objects created per player per minute,
- max object size,
- behavior complexity,
- large-area edits,
- object count per zone,
- overlapping trap geometry,
- crash-prone behavior scripts.

## Rendering / engine note

A voxel-native engine or subsystem may be appropriate for world geometry, but the core architectural requirement is not a specific renderer. It is a **stable, authoritative, world-native representation** that supports fast structured edits.

This is why voxel or chunk-native representations are attractive, even if some final render choices evolve later.

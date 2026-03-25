# Vibe World — Local Agent Notes

This folder is a design and planning bundle for the `vibe-world` idea.

## Current status

The project is still in the **design / pre-implementation** stage.

The current V1 decisions are:

- multiplayer backend: `SpacetimeDB`
- AI generation: external worker/service, not embedded in the authoritative backend
- V1 editing scope: spawned objects only, no terrain editing
- V1 room types: both public and private
- public rooms: non-destructive remixing
- private rooms: destructive edits may be enabled
- player identity: anonymous temporary nicknames
- target room size: about 20 concurrent players

## Read order

If you need fast context, read these first:

1. `README.md`
2. `01-product-vision.md`
3. `02-core-game-rules.md`
4. `04-object-and-creation-system.md`
5. `05-technical-architecture.md`
6. `prototype-v1-scope.md`
7. `spacetimedb-v1-schema.md`
8. `object-state-machine.md`
9. `prompt-ir-spec.md`
10. `world-settings-schema.md`
11. `public-world-permission-matrix.md`

## Source-of-truth guidance

When docs disagree, prefer:

1. the more recent V1 implementation-oriented specs
2. then `05-technical-architecture.md`
3. then `02-core-game-rules.md`
4. then higher-level vision docs

If you discover a real contradiction, do not silently pick one path and move on.
Update the docs or call out the mismatch clearly.

## Folder structure

Keep the root of this folder focused on:

- concept docs
- gameplay rules
- architecture and implementation specs
- concept assets

Avoid dropping implementation code directly into the root.

If a real prototype starts inside this folder, place it in a dedicated subfolder such as:

- `prototype/`
- `app/`
- `game/`

and keep the design docs at the root.

## Documentation expectations

When changing the design:

- keep `README.md` current
- keep cross-linked spec docs consistent
- update roadmap notes when a decision becomes settled

When implementation starts:

- keep implementation milestones connected to the design docs
- do not let runtime code drift away from the agreed world rules without updating the docs

## Reference checkout

The `json-render/` folder is a local reference checkout used for analysis and inspiration.
It is not the canonical game project and should not be treated as the source of truth for Vibe World architecture.

## Preferred next docs if more planning is needed

- client interaction model
- archive UX spec

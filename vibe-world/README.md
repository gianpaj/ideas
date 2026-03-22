# Vibe World — Current State Bundle

This folder captures the current state of the game concept discussed so far: a multiplayer, prompt-first, voxel-native social sandbox where players create and remix chunky 3D worlds in real time.

## Included documents

- `01-product-vision.md` — product thesis, fantasy, pillars, player fantasy
- `02-core-game-rules.md` — current ruleset for public/private worlds, editing, resets, archives
- `03-worlds-hosting-and-governance.md` — server/world model, host powers, presets, persistence
- `04-object-and-creation-system.md` — voxel object philosophy, grace periods, prompt-first creation, terminal mode
- `05-technical-architecture.md` — authoritative multiplayer stack, conflict handling, object lifecycle, AI pipeline
- `06-research-landscape-3d-voxel-ai.md` — current research findings on 3D/voxel AI models and what is relevant
- `07-open-questions-and-next-steps.md` — unresolved design decisions and recommended prototype roadmap

## Snapshot summary

The current concept is:

- Anyone can create a world/server from a 3D template.
- The creator becomes the host and chooses key rule settings.
- Public worlds are collaborative and remixable, but regular players cannot make destructive edits.
- Private worlds can be much more chaotic, including destructive editing.
- The visual identity is intentionally chunky and openly voxel-based.
- Object creation is primarily prompt-driven, with rough drafts appearing first and light transform-based refinement during a fixed grace period.
- Resettable worlds wipe the live version completely, but preserve prior versions as read-only, explorable “time machine” snapshots.

## Research note

The research bundle reflects public materials reviewed on March 22, 2026. The strongest near-term fit is not a single end-to-end text-to-voxel model, but a constrained system where AI produces structured object operations inside a world-native voxel grammar.

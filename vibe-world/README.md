# Vibe World

This folder is the current design and early implementation-spec bundle for Vibe World: a multiplayer, prompt-first, voxel-native social sandbox where players create and remix chunky 3D worlds in real time.

## Current status

The concept has moved past loose brainstorming and into early implementation planning.

The current V1 decisions are:

- multiplayer backend: `SpacetimeDB`
- AI generation: external worker/service
- V1 editing scope: spawned objects only
- V1 world types: both public and private
- public worlds: non-destructive remixing
- private worlds: destructive edits may be enabled
- player identity: anonymous temporary nicknames
- target room size: about 20 concurrent players

## Recommended reading order

If you want the fastest path from concept to implementation context, read:

1. `01-product-vision.md`
2. `02-core-game-rules.md`
3. `04-object-and-creation-system.md`
4. `05-technical-architecture.md`
5. `prototype-v1-scope.md`
6. `spacetimedb-v1-schema.md`
7. `object-state-machine.md`
8. `prompt-ir-spec.md`
9. `world-settings-schema.md`
10. `public-world-permission-matrix.md`

## Concept Art & Visualizations

### First-Person View (Grace Period UI) — ChatGPT
![First-person perspective showing prompt-driven creation with grace period UI, neon cyberpunk aesthetic](concept-01-chatgpt.png)

**Scene:** Player using `/create` command to build a chunky cyber-tree. Multiple collaborators (AstroCoder, PixelFriend, VibeMaster) visible in shared world. UI shows generation phase, grace period countdown, and multiplayer overlay.

### Overhead Collaborative View — Gemini 3.0 Pro
![Overhead perspective showing full world layout with multiple player creations and structures](concept-02-gemini.png)

**Scene:** Third-person over-the-shoulder view of "GianPaj" actively creating in the "Neon Oasis" world. Shows grace period mechanics, holographic UI panel, multiple collaborating players (AstroCoder, PixlFriend, VibeMaster), and the vibrant voxel environment with the snapshot archive.

**Prompt Details:** See [`image-prompts.md`](image-prompts.md) for the full AI generation prompts used to create these visualizations.

## Document structure

### Concept and product shape

- `01-product-vision.md` — product thesis, fantasy, pillars, and player fantasy
- `03-worlds-hosting-and-governance.md` — world model, host powers, presets, and persistence framing
- `06-research-landscape-3d-voxel-ai.md` — external research and technology landscape

### Rules and gameplay

- `02-core-game-rules.md` — public/private rules, editing, resets, and archive behavior
- `04-object-and-creation-system.md` — object philosophy, grace periods, prompt-first creation, and object grammar

### Architecture and V1 implementation specs

- `05-technical-architecture.md` — authoritative multiplayer stack, object lifecycle, and AI pipeline
- `07-open-questions-and-next-steps.md` — roadmap notes and remaining open design questions
- `prototype-v1-scope.md` — high-level scope and phased implementation plan for the first playable
- `spacetimedb-v1-schema.md` — first multiplayer schema and reducer boundary proposal
- `object-state-machine.md` — authoritative live object lifecycle
- `prompt-ir-spec.md` — first constrained prompt intermediate representation
- `world-settings-schema.md` — host-configurable world settings for V1
- `public-world-permission-matrix.md` — action-by-role permission model for public/private/archive contexts

### Support files

- `image-prompts.md` — prompts used to generate concept images
- `AGENTS.md` — local guidance for future agents and implementation work

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

## Repository note

The `json-render/` directory is a local reference checkout used for analysis.
It is not part of the Vibe World source of truth and is ignored from version control.

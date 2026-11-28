# Agent Note: Multiplayer agent docs, history in Postgres and Yjs for live typing

Status: proposed — chosen in the MLP plan, not yet validated by the transport spike

## Problem

The product is a shared thread where people and an agent co-write documents.
It has to answer "which turn changed this paragraph", restore any past
state, diff any two states, and let several people type in one document at
once. Two engineers build it, and the client is a web browser.

## Proposal

Two separate mechanisms.

- **History.** Postgres is the source of truth. A revision is a row holding
  the editor's JSON for the whole document plus its cause: a run for agent
  edits, a user for human edits. A `block_changes` row records each block a
  revision changed. A run links to its input messages through `run_inputs`.
- **Live typing.** Yjs 13 through Tiptap's collaboration extension and
  Hocuspocus. It carries keystrokes and cursors. The server reads it to cut
  revisions. It is never queried as history.

The plan is in
[multiplayer-agent-docs/PLAN.md](../../../../multiplayer-agent-docs/PLAN.md).

## Alternatives considered

- **A central authority ordering ProseMirror steps, no CRDT.** It gives an
  exact linear log and lets the server reject an edit made against old text.
  It lost because the team would write and test the sync server itself.
  `prosemirror-collab` is a client plugin with an example authority, last
  published in 2023, and Tiptap removed it from its bundle as unused. The
  argument for it, that CRDT libraries cannot record which message changed
  what, does not hold: no library on either side gives that without the
  revision table.
- **Block rows with one editor per paragraph.** A document is rows of
  blocks, each with a version and a compare-and-swap on write. No CRDT and
  no step log. It lost because two people cannot type in the same paragraph,
  and applying remote block replacements into a live editor is custom sync
  code too. It is the fallback if the spike fails.
- **The CRDT's own history as product history** (Loro or Automerge). Both
  store a message on every change and have the best fork and diff calls.
  Their ProseMirror bindings are thin or beta, and attribution and branching
  would depend on library internals.
- **Yjs 14.** It adds attribution and plans a suggestion mode. It is a
  release candidate, and Tiptap and Hocuspocus require Yjs 13.
- **Markdown as the stored snapshot.** Simple to diff and to hand to the
  model. Tiptap's Markdown extension is in beta and drops block ids and
  comment anchors, so a restore would break attribution.
- **Git-backed Markdown.** A second consistency domain, and commits are too
  coarse to name the turn behind a change.

## Acceptance criteria

- A SQL query returns the turn and requester that last changed a block.
- Restore brings back an old revision with its block ids intact.
- The five transport spike tests in the plan pass.
- A person and the agent editing one document never lose an accepted edit.

## Risks

- y-prosemirror handles concurrent paragraph split and merge poorly,
  according to ProseMirror's author. The spike tests it.
- A move to Yjs 14 will come. Keeping history in Postgres limits it to the
  transport.
- Full snapshots per revision assume documents stay under about 100 KB.

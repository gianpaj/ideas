# Plan: Minimum Lovable Product

Status: proposed, awaiting the decisions in section 2.

The concept is in [README.md](README.md). Package versions and licences were
read from the npm registry on 2026-11-27.

## 1. What ships

Three people and an agent argue a plan into shape in one thread. The document
sits beside the chat. The agent's edits wait as proposals that anyone can
accept or reject. Anyone can click a paragraph and see which turn changed it
and who asked.

In scope:

1. Workspace, sign-in, invite by link.
2. Threads with several people and one agent. Every viewer and late joiner
   sees the same streamed turn.
3. Documents beside the thread, with live co-editing and cursors.
4. Agent edits as proposals. Accept or reject each one, or all from a turn.
5. Comments on document ranges and on messages. The agent replies to each.
6. History per document. Each revision names its cause. Restore and diff.
7. Uploads (PDF, image, Markdown) and web search as agent context.
8. Unread state and mention emails.

Not in the MLP: fork and merge, connectors, several agents per thread,
people typing in suggestion mode, offline editing, a mobile layout, export
beyond Markdown, the desktop shell (it follows the web beta, section 4).

## 2. Decisions this plan assumes

Reply with numbers to change any of them. Each one names what it moves.

1. **Users have no Git repository.** Product people, founders, designers.
   If the first users are engineers with repos, Delta already covers most of
   this and the plan needs a different opening.
2. **Two people can type in one paragraph at once.** Yjs carries live typing.
   If one editor per paragraph is acceptable, block rows replace Yjs and
   milestone 2 shrinks by about a week.
3. **A document belongs to one thread.** Several threads over one document
   changes the schema before milestone 2.
4. **Agent edits wait for approval.** No direct-apply switch in the MLP.
5. **A message sent mid-turn is folded into the running turn** at the next
   tool boundary. Stop is a separate button. Nobody's message cancels
   another person's turn.
6. **Fork waits.** The snapshot schema keeps it cheap to add.
7. **Content types:** headings, paragraphs, lists, checklists, code blocks,
   tables, images, links. No embeds or diagrams.
8. **The workspace pays.** One model vendor, a monthly token budget per
   workspace, a hard stop at the budget.
9. **A deploy may interrupt a running turn.** The thread shows what the turn
   finished and a Retry button.
10. **No SSO, zero-retention, residency or self-hosting in year one.**
11. **Desktop is a shell around the web client**, built after the web beta.

## 3. Architecture

```text
web client (React SPA, Tiptap editor, chat)
   │  one WebSocket for thread events      │  one WebSocket per open document
   ▼                                       ▼
┌──────────────── one Node process ─────────────────┐
│ HTTP API · thread room · Hocuspocus · run worker  │
└───────────────────────┬───────────────────────────┘
                        ▼
                    Postgres
```

One Node process and one Postgres. Zed's open-source collaboration server is
deployed as a single pod (`replicas: 1` in its Kubernetes template), which
is the evidence that this shape is enough to start.

| Part | Choice | Why |
| --- | --- | --- |
| Client | React 19, Vite 8, static build | A static bundle loads the same way in a browser and in a desktop shell |
| Editor | Tiptap 3.35 (MIT) with `@tiptap/extension-unique-id` (MIT) | Tiptap's documented path. Every top-level block gets a stable id |
| Live typing | Yjs 13 through `@tiptap/extension-collaboration` and Hocuspocus 4.9 (MIT) | Reconnect, resync, cursors and persistence hooks already exist. Yjs carries keystrokes and is never the history |
| Agent writes | Hocuspocus `openDirectConnection` plus `@hocuspocus/transformer` | The agent edits the same document object people do, inside the server |
| Database | One Postgres on a host that allows direct connections | Source of truth for everything except keystrokes in flight |
| Auth | Better Auth 1.7 (MIT) with its organization plugin | Users and workspaces live in our Postgres |
| Agent | Anthropic TypeScript SDK, Messages API, streaming, our own loop | Every tool reads or writes our database, and run events must reach many viewers. Managed Agents adds a hosted sandbox this agent does not use |
| Model | `claude-opus-5-5` by default, set per workspace | Prompt caching on the thread and document prefix keeps long turns cheap |
| Hosting | Any host that keeps one Node process and its WebSockets alive | Serverless functions do not fit a long-lived socket |

### How "which turn changed this paragraph" works

1. A revision is a row holding the editor's JSON for the whole document.
   Markdown is derived for the model and for export, never stored as truth.
   Tiptap's Markdown extension is in beta and drops block ids and comment
   anchors on a round trip.
2. The server cuts a revision when an agent tool call lands, when someone
   accepts a proposal, and when a person stops typing for 30 seconds or
   sends a message.
3. On each revision the server compares block ids and content hashes with
   the previous revision and writes one `block_changes` row per changed
   block.
4. Clicking a paragraph reads the newest `block_changes` row for that block,
   then its revision, then its run, then the run's input messages and who
   sent them. A human edit shows its author instead.

This gives block-level attribution from plain SQL. Character-level blame is
out of scope.

### Agent proposals

A proposal is a row with a block id, the quoted text, the replacement and
the run id. The client draws it as a card on the live text. Accepting it
applies an ordinary edit through the server and cuts a revision carrying the
run id. A proposal whose quote no longer matches turns `stale` and the agent
can be asked to redo it. Nothing is stored as marks inside the document.

Agent tools: `read_document` (Markdown with block ids), `propose_edit` (find
and replace inside a block), `propose_insert` (after a block),
`propose_rewrite` (one section), `reply_to_comment`, and Anthropic's web
search tool. Each tool call carries the revision the agent read. A quote that
is missing or ambiguous returns an error holding the block's current text.

### Tables

`users`, `workspaces`, `memberships`, `threads`, `messages` (per-thread
counter, client nonce), `documents`, `revisions` (JSON snapshot, cause),
`block_changes`, `proposals`, `comments`, `runs` (status, lease, heartbeat),
`run_inputs` (run, message, position), `run_events`, `uploads`,
`read_state`, `usage`.

### What the server must do

| Duty | Rule |
| --- | --- |
| Authorise every message | Check the thread role on each write, not only at connect. Stamp the author on the server |
| Order chat messages | Per-thread counter bumped in the insert transaction |
| Make resends safe | Client nonce with a unique index. On a repeat, compare a content hash and reject a mismatch |
| Reconnect | A written protocol. The client sends what it has, receives what it missed, and resends what was never confirmed. Backoff with jitter |
| Persist documents | Hocuspocus store hook writes the Yjs state and cuts revisions by the rules above |
| Own agent runs | `runs` row with status, lease owner, lease expiry and a heartbeat that expires. One running run per thread |
| Fence a run that lost its lease | Every write from a run checks, in the same transaction, that the run is still running and still owned. Stop works through the same check |
| Survive a crash mid-turn | Persist each complete model response and its tool results before the next request, unedited. Key document tools by run and tool call id. An interrupted run shows Retry |
| Stream a turn to every viewer | Fan out in process. Persist coalesced chunks every 100 to 250 ms, never a row per token. A late joiner reads stored events, then follows live |
| Handle a stale agent write | Resolve the quote against the live document. Missing or ambiguous returns an error with the block's current text. A match in a block that changed since the read still lands as a proposal, flagged |
| Report delivery and wake separately | A stored message and "an agent will answer" are two results |
| Cap spend and rate | Token budget per workspace, message rate per connection, bounded outbound queues |
| Keep presence in memory | With a 30 second grace on disconnect |

Deferred: a second node, another region, a durable execution engine, Redis,
compacting old revisions, resuming a model stream mid-response.

## 4. Web first, desktop on the same code

The desktop app is the web client inside a shell. No second client exists.

Rules the web client follows from day one so the shell stays cheap:

1. The client is a static bundle. No page depends on server rendering.
2. All data arrives through the HTTP API and the two WebSockets.
3. Sign-in works by redirect, so a shell can run it in the system browser
   and return through a deep link.
4. Notifications, file open and file save go through one small module with a
   browser implementation.
5. The app is installable as a PWA, which gives a dock icon before any shell
   exists.

The shell is Electron 45 loading the hosted client. One browser engine on
every platform matters for an editor, and Electron's auto-update is the
well-worn path. Tauri 2.12 is the alternative if download size matters more.
It uses the system webview, which is Safari's engine on macOS, and that
engine has to work for web users anyway.

The shell adds a window, deep links (`app://thread/<id>`), native
notifications, and auto-update. About one week after the web beta.

## 5. Milestones

Estimate for two engineers who know React and Postgres. It moves most with
decision 2 and with how proposals behave under concurrent typing.

| # | Weeks | Work | Done when |
| --- | --- | --- | --- |
| 0 | 1 | Transport spike (below), repo skeleton, deploy pipeline | The five spike tests pass on Yjs, or decision 2 changes |
| 1 | 2 | Sign-in, workspaces, invites, threads, messages, thread room, reconnect, presence | Three browsers chat in one thread. Killing the server loses no sent message and duplicates none |
| 2 | 2 | Documents, live co-editing, block ids, revisions, `block_changes`, history list, restore, diff | Two people type in one paragraph. Restore brings back an old revision with its block ids |
| 3 | 3 | Runs with lease and fencing, streamed events, agent tools, proposals, accept and reject, stale handling, mid-turn fold-in, Stop, token budget | A late joiner sees a running turn from its start. A proposal against changed text goes stale. Stop halts writes within one tool call |
| 4 | 2 | Comments on ranges and messages, agent replies, uploads, web search, unread state, mention email | A comment stays on its text through edits by others. The agent answers each comment in its thread |
| 5 | 2 | Paragraph click to cause, permissions, share links, crash and deploy drills, an eval set for the edit tools | Clicking any paragraph names the turn and requester. A deploy mid-turn leaves a Retry button and no half-applied edit |
| 6 | 1 to 2 | Private beta fixes, Electron shell | A signed build opens a thread from a deep link |

About twelve weeks to a private beta on the web, fourteen with the shell.

### The transport spike

Three browser tabs and a server-side agent writer on one document.

1. Kill the server mid-edit. No accepted edit is lost and none is applied
   twice.
2. Sleep a tab for an hour with unsent edits. Write down what the user sees.
3. The agent rewrites a section while a person types in it. Write down the
   outcome.
4. A 40-step agent edit lands while two people type. Measure time to
   converge.
5. Split a paragraph in one tab while another types in it.

Keep Yjs if every failure can be explained to a user in one sentence.

## 6. Risks

1. **Proposals under concurrent typing.** People edit a block while a
   proposal for it is open. The stale rule is the fallback. The eval set in
   milestone 5 measures how often the agent's quote fails to match.
2. **y-prosemirror paragraph split and merge.** ProseMirror's author calls
   its handling poor. Spike test 5 covers it. If it fails, fall back to one
   editor per paragraph.
3. **Yjs 14.** Tiptap and Hocuspocus pin Yjs 13. Yjs 14 is a release
   candidate that adds attribution, with suggestion mode planned in its
   ProseMirror binding. A migration will come.
   Keeping history in Postgres limits it to the transport.
4. **Demand for provenance.** Evidence is thin (README, "Evidence that
   should worry us"). The revision label is cheap. Paragraph click lands in
   milestone 5 so it can be cut.
5. **Agent cost.** A 100 KB document is about 25,000 tokens per request
   before caching. The budget in decision 8 is the guard.
6. **Delta ships more for prose.** Zed already uses it for docs. The opening
   is people without a repository (decision 1).
7. **The estimate.** Tracked changes took CKEditor's team twice its
   estimate. Proposals as rows avoid that feature, and the estimate assumes
   they hold.

## 7. Decision records

- [History and live typing](../.agents/notes/proposed/product/2026-11-27-multiplayer-agent-docs-history-and-transport.md)
- [MLP scope](../.agents/notes/proposed/product/2026-11-27-multiplayer-agent-docs-mlp-scope.md)

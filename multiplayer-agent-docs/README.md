# Multiplayer agent docs: one thread where people and an agent write plans together

**Stage:** Concept with a proposed MLP plan (not built)
**Date:** 2026-11-27
**Audience:** Small teams without a Git repository who write plans, specs and research notes
**Working name:** none yet. The folder name is a placeholder.

## Purpose

Teams write plans with AI in private chats, then paste the result into a
shared document. The reasoning stays in one person's chat and the document
carries no record of why it says what it says.

This product puts the conversation and the document in one place. Several
people and one agent talk in a thread. The document sits beside it. The
agent's edits wait as proposals. Anyone can click a paragraph and see which
turn changed it and who asked.

No code editing. Web first. The desktop app is the same client in a shell.

## The moment it has to deliver

Three people and an agent argue a plan into shape in one thread. Nobody
copies text between a chat and a document. A week later, someone asks why
the scope section says what it says, clicks the paragraph, and reads the
exchange that produced it.

## Where the idea comes from

Zed's [Delta](https://delta.dev) does this for code. People and coding
agents share a thread, the repository's working tree is replicated live to
every participant, and edits are recorded beside the messages that caused
them. Zed says it uses Delta for prose too: "We now use Delta for pretty
much everything from internal docs and planning to website copy and blog
posts. (We keep our internal docs in a repo, too. I let the agent handle the
Git part.)"
([post](https://delta.dev/blog/please-stop-sending-me-google-docs))

Delta's limits for a non-engineering team, from its own docs:

- A thread's files need a Git repository with a configured remote. A thread
  without a project has no files.
- Sign-in is GitHub OAuth only.
- Markdown has a source and preview toggle. There is no suggestion mode.
- Every invitee joins as an editor.

What this idea keeps from Delta's public design:

1. One shared thread with people and an agent as participants.
2. Comments on a document range or on a message, which the agent answers one
   by one.
3. Every document change linked to what caused it.
4. Named senders, with the agent acting under the requester's permissions.

What it drops: worktrees, Git, terminals, sandboxes, runners on user
machines, a native UI toolkit, offline editing.

## Two rules it changes on purpose

**A message sent mid-turn is folded in, not a takeover.** Delta's docs say
"Sending a prompt takes over any turn that's running in the thread,
including a teammate's. Coordinate before you start work."
([plugin docs](https://delta.dev/docs/cli/claude-code)) Here a second
person's message joins the running turn at the next tool boundary, and Stop
is a separate button.

**The cause of a change is a turn, not a message.** In Delta one send
"submits every draft at the end of the thread, from every author". A turn
can therefore have several people behind it. The data model links each
revision to a run, and each run to its input messages.

## What exists already

No product found gives all three of a shared multi-person agent thread,
changes linked to their cause, and branching a thread with its documents to
people without a repository. Checked 2026-11-27.

| Product | Shared thread with an agent | Change linked to its cause | Branch thread and documents | What is missing |
| --- | --- | --- | --- | --- |
| [Zed Delta](https://delta.dev/docs/agents/threads) | Yes | Partial. Diff from a message and rewind. "Agent Blame" is listed as coming soon | Yes. Merge brings files, not conversation | Needs a Git repository and GitHub sign-in |
| [Claude Docs](https://support.claude.com/en/articles/16923645-get-started-with-claude-docs) | Partial. `@Claude` in comment threads. The chat is private per person | Partial. "Every change is attributed to whoever made it, whether that's a person or Claude" | No | A shared conversation |
| [Tana](https://tana.inc/learn/features/docs) | Yes | Partial. A document lists "which chats and meetings changed it" | No | Paragraph-level cause, branching |
| [Manus](https://manus.im/docs/features/branch) | Yes | Partial. File versions per reply | Partial. Private to the owner, no merge | A co-edited document |
| [Dust](https://docs.dust.tt/docs/user-documentation/agents/branch-a-conversation.md) | Yes | No | Partial. A summary plus copied files | A co-edited document and its history |
| Notion | Partial. AI chats are personal | Partial. Person, AI or integration | No | A shared conversation |
| Google Docs with Gemini | No. Gemini is a per-user side tool | Suggestions per author | No | A team thread |
| [Every Proof](https://every.to/on-every/introducing-proof) | No | Partial. Human or AI | No | Chat, workspace |

## Evidence that should worry us

Demand for provenance and branching is thin.

- Proof's author says provenance "was less important than I thought".
  ([transcript](https://every.to/podcast/transcript-how-we-use-proof-a-collaborative-editor-for-humans-and-ai))
- "I just do not care to see people's LLM conversations. Those are not the
  artifacts. The changes are."
  ([Hacker News](https://news.ycombinator.com/item?id=49763605))
- Amp removed forking: "we want Amp to be simple as well as powerful."
  ([post](https://ampcode.com/news/stick-a-fork-in-it))

In favour:

- "a separate collaborative doc and a chat linked to that doc would work way
  better", written as a critique of Delta's layout.
  ([Hacker News](https://news.ycombinator.com/item?id=49279849))
- Cursor users call its blame view "much less useful without prompt info".
  ([forum](https://forum.cursor.com/t/cursor-blame-missing-agent-conversation-summary/150719))

Both sides want a short reason beside a change, not a transcript. The plan
ships the cheap version first, a label on each revision naming the turn and
requester, and leaves forking out of the first release.

## Design in one paragraph

One Node process and one Postgres. A React client with the Tiptap editor.
Yjs carries live typing and is never the history. History is a snapshot of
the document per revision in Postgres, with a record of which blocks each
revision changed. Agent edits are proposal rows, drawn as cards over the
text and applied on accept. The agent is a plain Messages API tool loop
running as a leased background job whose events every viewer can replay.

Details, decisions and milestones are in [PLAN.md](PLAN.md). Sources are in
[references/sources.md](references/sources.md).

## Open decisions

[PLAN.md](PLAN.md) section 2 lists eleven assumptions. The three that move
the most work:

1. Whether two people must be able to type in one paragraph at once.
2. Whether the first users are people without a Git repository.
3. Whether a document belongs to one thread or to many.

## Basis

Zed's public posts and docs, the open-source
[`delta-claude`](https://github.com/zed-industries/delta-claude) plugin
(AGPL-3.0, read for behaviour, no code reused), Zed's open-source `collab`
server (GPL-3.0, read for its deployment shape), the npm registry, and the
vendor pages linked above.

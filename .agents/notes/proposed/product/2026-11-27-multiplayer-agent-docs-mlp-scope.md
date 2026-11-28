# Agent Note: Multiplayer agent docs, MLP scope

Status: proposed — scope set in the MLP plan, awaiting the decisions in its section 2

## Problem

Teams write plans with AI in private chats, then paste results into a shared
document. The reasoning stays in one person's chat, and the document carries
no record of why it says what it says. The first release has to prove that a
shared thread beside a living document fixes this, with two engineers and
about three months.

## Proposal

Ship eight capabilities:

1. Workspace, sign-in, invite by link.
2. Threads with several people and one agent, streamed to every viewer.
3. Documents beside the thread with live co-editing.
4. Agent edits as proposals stored as rows, accepted or rejected one by one
   or per turn.
5. Comments on document ranges and on messages. The agent replies to each.
6. History where each revision names the turn and requester behind it, with
   restore and diff.
7. Uploads and web search as agent context.
8. Unread state and mention emails.

Rules: @mention summons the agent, a message sent mid-turn is folded into
the running turn, Stop is a separate button, the agent acts with the
requester's permissions, the workspace has a token budget.

The web client is a static bundle. The desktop app is that client in a
shell, built after the web beta.

The plan is in
[multiplayer-agent-docs/PLAN.md](../../../../multiplayer-agent-docs/PLAN.md).
The history model is in
[the history and transport note](2026-11-27-multiplayer-agent-docs-history-and-transport.md).

## Alternatives considered

- **Fork a thread with its documents in the first release.** It is the
  feature no near product has for people without a repository. It lost
  because demand evidence is thin, Amp removed forking for simplicity, and
  the snapshot schema makes it cheap to add later.
- **Merge back with fork.** Merging prose branches that conflict in meaning
  is unsolved, and whether people merge or only compare is unknown.
- **A new message cancels the running turn**, as Delta does. Delta's docs
  tell people to coordinate before they start, which admits the cost.
- **A visible queue of turns.** Predictable, but a second person waits
  minutes. Folding the message in at the next tool boundary is one append to
  the request.
- **Agent edits applied directly.** Faster. Several people share the
  document, so edits wait for approval. A switch can follow.
- **Proposals as marks inside the document**, using
  `prosemirror-suggest-changes`. The library has not published in a year and
  documents no collaboration support. Marks sharing a document with comment
  anchors are where Every's Proof still has open bugs.
- **People typing in suggestion mode.** Not needed to hold agent edits for
  approval.
- **Connectors at launch.** They force the question of whose credentials the
  agent uses in a group.
- **An agent that speaks unprompted.** ChatGPT retired group chats, and
  Mattermost labels ambient agents experimental.
- **A native desktop client.** A second client to build. A shell around the
  web client reaches the same users.

## Acceptance criteria

- Three people and the agent take a plan from blank to agreed in one thread
  without leaving the product.
- Clicking a paragraph names the turn that changed it and who asked.
- A late joiner sees a running turn from its start.
- A deploy mid-turn leaves a Retry button and no half-applied edit.

## Risks

- People may not care about provenance. The revision label ships first, and
  paragraph click can be cut.
- Proposals may go stale often when people type in the same block.
- Zed's Delta already serves engineers who keep documents in a repository.
- The estimate of twelve weeks to a web private beta assumes proposals as
  rows hold up.

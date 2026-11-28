# Sources

Read on 2026-11-27.

## Zed Delta, public material

- [Introducing Delta](https://zed.dev/blog/introducing-delta) and
  [public beta](https://zed.dev/blog/delta-public-beta)
- [Please Stop Sending Me Google Docs](https://delta.dev/blog/please-stop-sending-me-google-docs).
  Zed using Delta for internal docs, planning and blog posts
- [Fine-grained version control for agents](https://delta.dev/blog/fine-grained-version-control-for-agents).
  One Cloudflare Durable Object per thread, a WebSocket per thread, deltas
  saved and then pushed to everyone
- [Delta 101](https://delta.dev/docs/delta-101). "Sending another message
  during generation stops the current response and immediately sends the new
  message"
- [Claude Code plugin](https://delta.dev/docs/cli/claude-code). "Sending a
  prompt takes over any turn that's running in the thread, including a
  teammate's"
- [Collaborate in a thread](https://delta.dev/docs/collaboration/collaborate-thread).
  Drafts visible to all, one send submits every author's draft, the sender
  pays, invitees join as editors
- [Threads](https://delta.dev/docs/agents/threads) and
  [Review and sync](https://delta.dev/docs/agents/review-and-sync). Fork
  copies the conversation and worktrees. Merge brings file changes only
- [Build a plugin](https://delta.dev/docs/cli/build-a-plugin). Per-producer
  sequence numbers, receipts, takeover and fenced records
- [Data storage](https://delta.dev/docs/privacy-and-security/data-storage)
- [Roadmap](https://delta.dev/roadmap)

## Open source read for behaviour

- [`zed-industries/delta-claude`](https://github.com/zed-industries/delta-claude),
  AGPL-3.0-only, commit `2d84069`. No code reused
- [`zed-industries/zed`](https://github.com/zed-industries/zed) `crates/collab`,
  GPL-3.0-or-later, commit `e5f6778`. Single pod, server id per boot, 30
  second reconnect grace, client backoff with jitter
- [Eg-walker paper](https://arxiv.org/abs/2409.14252), which Zed says its
  design resembles

## Libraries

- [Tiptap](https://tiptap.dev) 3.35.1, MIT. Its collaboration extension
  requires Yjs 13. [Pricing](https://tiptap.dev/pricing) for the hosted
  add-ons
- [Hocuspocus](https://github.com/ueberdosis/hocuspocus) 4.9.0, MIT
- [Yjs](https://github.com/yjs/yjs) 13.6.33 stable. Version 14 is at
  release candidate 30
- [`prosemirror-collab`](https://prosemirror.net/docs/guide/#collab) 1.3.1,
  last published 2023-05-17. The alternative considered for live typing
- [`@handlewithcare/prosemirror-suggest-changes`](https://github.com/handlewithcarecollective/prosemirror-suggest-changes)
  0.1.8, last published 2025-11-18. The suggestion library this plan avoids
- [Automerge](https://automerge.org/blog/) 3.5.0 and
  [Loro](https://github.com/loro-dev/loro) 1.19.1. Both store a message on
  every change. Their editor bindings are beta or thin
- [Better Auth](https://www.better-auth.com) 1.7.28, MIT
- [Electron](https://www.electronjs.org) 45.5.0 and
  [Tauri](https://tauri.app) 2.12.6

## Arguments about the sync choice

- [Lies I was told about collaborative editing, part 2](https://www.moment.dev/blog/lies-i-was-told-pt-2)
  and [Collaborating with AI is hard](https://www.moment.dev/blog/collab-with-ai-is-hard),
  Moment
- [Collaborative text editing without CRDTs or OT](https://mattweidner.com/2025/05/21/text-without-crdts.html),
  Matt Weidner
- Marijn Haverbeke on ProseMirror's algorithm not being "40 lines of code",
  [Hacker News](https://news.ycombinator.com/item?id=47409647)
- Kevin Jahns on guaranteed sync,
  [Hacker News](https://news.ycombinator.com/item?id=47430369)

## Near products

- [Claude Docs](https://support.claude.com/en/articles/16923645-get-started-with-claude-docs)
- [Tana docs](https://tana.inc/learn/features/docs)
- [Manus Branch](https://manus.im/docs/features/branch)
- [Dust, branch a conversation](https://docs.dust.tt/docs/user-documentation/agents/branch-a-conversation.md)
- [Every Proof](https://every.to/on-every/introducing-proof)
- [GitHub Next Chopin](https://githubnext.com/projects/chopin/), a prototype
- [Ink & Switch Patchwork](https://www.inkandswitch.com/patchwork/notebook/2024-version-control/07/)
  and [Upwelling](https://www.inkandswitch.com/upwelling/), research on
  branching prose

## Model API

- [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28),
  for connectors after the MLP

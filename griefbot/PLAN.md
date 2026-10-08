# Griefbot — MVP Implementation Plan

**Status:** Planning
**Last updated:** 2026-06-24
**Branch:** `claude/griefbot-mvp-webapp-usvakp`
**Companion docs:** [`DESIGN.md`](./DESIGN.md) · [`ETHICS.md`](./ETHICS.md)

---

## 1. What We're Building (MVP-1)

A self-hostable, open-source web app where a grieving user is welcomed by **Will**
(the counselling helper), creates a **Persona** of a loved one from a few texts /
screenshots + a short questionnaire (+ optional avatar image), and then has a
**real-time voice conversation** with that Persona in the browser.

Built on three pillars from the brief:

| Pillar | Choice for MVP-1 |
|--------|------------------|
| Inworld-style character engine ("Inworld clone") | A thin **persona/brain layer** we own: character card + memory retrieval + safety policy. Pluggable so a full open Inworld-clone runtime can replace it later. |
| Real-time speech-to-speech APIs | **OpenAI Realtime API** as the default hosted path; **Gemini Live** as a fallback; **fully-local pipeline** (Whisper STT → local LLM → local TTS) as the privacy/self-host path. |
| LiveKit | **LiveKit Cloud or self-hosted SFU** for browser↔agent audio, plus the **LiveKit Agents (Python) framework** to host the Persona agent and bridge to the realtime model. |

MVP-1 explicitly **excludes**: animated/video avatars, voice cloning, mobile native
apps, multi-user/shared Personas. See `DESIGN.md §7 Non-Goals`.

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Browser — Next.js + React (web app)                          │
│  • Onboarding/consent UI + "Will" chat                       │
│  • Persona builder (upload, OCR review, questionnaire)       │
│  • Conversation room: mic capture, voice playback,          │
│    live transcript, avatar image, session timer + exit       │
│  • LiveKit JS SDK (WebRTC)                                    │
└───────────────┬─────────────────────────────────────────────┘
                │ WebRTC media (Opus audio)  +  data channel
                ▼
┌─────────────────────────────────────────────────────────────┐
│ LiveKit SFU (cloud or self-hosted)                           │
└───────────────┬─────────────────────────────────────────────┘
                │ subscribes to user audio track / publishes TTS
                ▼
┌─────────────────────────────────────────────────────────────┐
│ LiveKit Agent (Python worker)  — one per active session      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Persona engine ("Inworld clone" layer)                  │ │
│  │  • character card (personality, voice, do/don't)        │ │
│  │  • memory retrieval over the user's source material     │ │
│  │  • safety policy (crisis detection, boundary phrases)   │ │
│  │  • prompt assembly for the realtime model               │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Realtime runtime (pluggable):                           │ │
│  │   A) OpenAI Realtime  B) Gemini Live  C) local pipeline │ │
│  └─────────────────────────────────────────────────────────┘ │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│ App API (Next.js route handlers / FastAPI)                   │
│  • auth, token minting for LiveKit rooms                      │
│  • profile/consent/session CRUD                              │
│  • OCR + ingestion pipeline                                   │
│  • subscription + 2-year continuity policy                    │
└───────────────┬─────────────────────────────────────────────┘
        ┌───────┴────────┬───────────────┬─────────────────┐
        ▼                ▼               ▼                 ▼
   Postgres         Object store     Vector index      KMS / user
 (profiles,        (encrypted        (memory          key material
  sessions,         blobs: imgs,      retrieval)       — see §6)
  consent)          voice, OCR)
```

### Why this shape
- **Persona engine separate from the model.** The character + safety policy live in
  *our* code, not in a vendor prompt, so guardrails are enforceable and the realtime
  provider is swappable (hosted ↔ local) without changing the persona.
- **LiveKit Agents** gives us a battle-tested room/worker model and first-class
  integrations with realtime providers, plus built-in turn detection and barge-in.
- **Pluggable realtime runtime** is what lets the same open-source app run fully
  local for the privacy-maximalist self-hoster and hosted for everyone else.

## 3. Tech Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Web app | Next.js (App Router) + React + TypeScript + Tailwind | SSR for marketing/onboarding; client room component. |
| Realtime transport | LiveKit (Cloud or self-hosted) + LiveKit JS SDK | WebRTC; data channel for transcripts/state/safety events. |
| Agent runtime | Python + LiveKit Agents | One worker per session; hosts persona engine. |
| Realtime model | OpenAI Realtime (default) / Gemini Live (fallback) / local | Local = Whisper.cpp + open LLM (e.g. Llama/Qwen) + Piper/XTTS. |
| Persona/brain | In-house persona layer (LangChain-free, thin) | Character card + retrieval; designed to be replaced by a full Inworld-clone runtime. |
| Memory retrieval | pgvector (Postgres) | Same DB; embeddings over OCR'd/uploaded text. |
| App API | Next.js route handlers + a small FastAPI service for agent control | Mint LiveKit tokens, manage sessions. |
| DB | Postgres | Profiles, consent ledger, sessions, billing. |
| Object store | S3-compatible (MinIO for self-host) | Encrypted blobs (images, voice, OCR text). |
| OCR | Tesseract (self-host) / cloud OCR (hosted) | For screenshots of conversations. |
| Auth | Email + passkeys (e.g. Lucia/Auth.js) | Minimal PII. |
| Encryption | libsodium/age + envelope encryption; client-side keys | See §6. |
| Deploy | Docker Compose (self-host) + Helm chart (later) | One-command "tech friend" deploy. |
| Payments | Stripe (hosted only) | Self-host needs no payment. |

## 4. Components & Build Order

### M0 — Spike (de-risk the hard parts) — ~1 week
- [ ] LiveKit room: browser mic → LiveKit Agent → **OpenAI Realtime** → voice back.
      Measure end-to-end latency; target **< 1.0s** perceived response, **< 700ms**
      to first audio.
- [ ] Prove barge-in / turn detection feels natural.
- [ ] Spike the **local pipeline** (Whisper → small LLM → Piper) to confirm the
      self-host path is viable, even if slower.
- **Exit criteria:** a throwaway page where you can hold a spoken conversation with
  a hard-coded persona at acceptable latency.

### M1 — Persona engine + builder — ~2 weeks
- [ ] **Ingestion:** upload text + image; OCR screenshots; user reviews/edits the
      extracted text (consent + accuracy checkpoint).
- [ ] **Questionnaire:** guided "who were they" form → structured persona traits.
- [ ] **Character card assembly:** merge text style signals + questionnaire into a
      persona definition (tone, vocabulary, relationships, do/don't, gentle topics).
- [ ] **Memory retrieval:** embed source material into pgvector; retrieve per-turn.
- [ ] **Avatar:** optional image upload, shown during conversation.
- **Exit criteria:** a created Persona that audibly reflects the source material.

### M2 — Onboarding "Will" + safety — ~2 weeks
- [ ] Will chat flow: honest framing, grief-services panel up front, how-to-start.
- [ ] **Consent ledger:** relationship affirmation, rights to material, nature/limits
      acknowledgement — recorded, timestamped (see ETHICS).
- [ ] **Safety policy in the agent:** crisis-language detection → Will hand-off +
      resources; persistent "AI representation" labelling; bounded session + closing
      grounding moment.
- [ ] "Ask Will" affordance inside a session (tune Persona / be heard).
- [ ] Real-human support contact path.
- **Exit criteria:** ETHICS checklist green for a first private beta.

### M3 — Accounts, privacy, deploy — ~2 weeks
- [ ] Auth + minimal accounts.
- [ ] **Encryption** at rest with client-held keys; export + permanent delete (§6).
- [ ] **Self-host:** `docker compose up` brings up app + LiveKit + Postgres + MinIO +
      local model option; documented "deploy for a friend" guide.
- [ ] **Hosted:** Stripe subscription; the **2-year continuity policy** (§7).
- [ ] Open-source the repo (license, CONTRIBUTING, security policy).
- **Exit criteria:** a stranger can self-host from the README; hosted billing works.

### M4 — Private beta polish — ~1–2 weeks
- [ ] Latency tuning, voice selection, transcript export.
- [ ] Free-trial limits enforced (decision from §8).
- [ ] Observability, rate limits, abuse protection.

**Rough total to private beta: ~8–9 weeks** for a small team.

## 5. Data Model (Postgres, sketch)

- **user**: id, email, auth, created_at
- **consent**: id, user_id, persona_id, type (`relationship` | `rights` | `nature_limits`), text_shown, accepted_at
- **persona**: id, user_id, name, relationship, character_card (jsonb), voice_id, avatar_blob_id, created_at, **continuity_state** (`active` | `dormant_2yr` | `reaffirmed`)
- **source_item**: id, persona_id, kind (`text` | `screenshot` | `voice`), blob_id, ocr_text (encrypted), included (bool)
- **memory_chunk**: id, persona_id, source_item_id, text (encrypted), embedding (vector)
- **session**: id, user_id, persona_id, started_at, ended_at, duration_s, ended_reason, safety_events (jsonb)
- **subscription**: id, user_id, plan, status, current_period_end

## 6. Privacy & Encryption (the honest version)

The notes demand E2E encryption and a clear "where does my data live" answer. The
genuinely hard part is that **a hosted realtime model must process plaintext audio**
to respond. We do not paper over this; we offer a spectrum and state it plainly.

**Trust model, strongest → most convenient:**

1. **Fully local self-host (no third party sees anything).** App + LiveKit + local
   STT/LLM/TTS all on hardware the user/their tech friend controls. No audio or text
   ever leaves the box. This is the "verify our code, deploy it yourself" path.
2. **Self-host with a hosted realtime model.** Source material and Persona stay
   encrypted on the user's infra; only live conversation audio is streamed to the
   model provider under **zero-retention / no-training** terms, ephemerally.
3. **Our hosted service.** Same code we publish. At rest, all source material,
   OCR text, memory chunks, avatars, and voice samples are **encrypted with
   envelope encryption under a key derived from the user's credentials** (client
   side where possible); our operators cannot read content. Live audio transits the
   realtime provider as in (2).

**Commitments:**
- At-rest encryption of all sensitive blobs and text; keys not co-located with data.
- **One-click permanent delete** and **export** of everything.
- Plain-language privacy explanation in onboarding (Will literally says it).
- We will **not market "end-to-end encrypted"** in a way the hosted realtime hop
  contradicts; the local path is what earns the strongest claim, and we point
  privacy-maximalists there.

> Decision needed (§8): how much client-side key custody for MVP-1 vs. fast-follow.

## 7. The 2-Year Continuity Policy

From the notes — encode as **care, not lockout**:

- A Persona stays `active` while the subscription is current.
- A Persona reaches **2 years since creation** → it enters a **`dormant_2yr`** soft
  state. To converse with it again, the user must **send an explicit email to
  support** (a deliberate, human re-affirmation) → state becomes `reaffirmed` and
  the old Persona is talkable again.
- A user who has created a **newer** Persona can keep subscribing and talking to the
  new one freely, but the **old (2yr+) Persona stays dormant** until the explicit
  re-affirmation step.
- **Intent:** discourage *default* indefinite attachment, contain long-tail
  storage/compute, and make keeping a years-old companion a conscious choice. We
  surface it gently ("It's been two years with [name]. If you'd like to keep this
  companion available, just email us — there's no rush.") and **never delete**
  source material as part of this; dormancy is about live conversation, not erasure.

## 8. Open Questions / Decisions Needed

| # | Question | Owner | Blocking? |
|---|----------|-------|-----------|
| 1 | **Free-trial limits** — caps on uploads (count/chars), session minutes, or # of Personas? Must be enough to *feel* it. | Product | M4 |
| 2 | Default realtime provider for hosted: OpenAI Realtime vs. Gemini Live (latency, cost, retention terms). | Eng | M0 |
| 3 | Use a full existing **open Inworld-clone** runtime vs. our thin persona layer for MVP-1. | Eng | M1 |
| 4 | Degree of **client-side key custody** for MVP-1 vs. fast-follow. | Eng/Sec | M3 |
| 5 | Voice cloning — MVP-2 or deferred until consent tooling is solid? | Product/Ethics | post-MVP |
| 6 | Grief-services resource list — sourcing & region coverage. | Product | M2 |
| 7 | Make the 2-year rule feel like a ritual, not a billing gate — exact UX/email flow. | Product | M3 |

## 9. Cost Sketch (hosted, per active conversation)

| Item | Basis | Rough cost |
|------|-------|-----------|
| Realtime model (speech-to-speech) | per audio minute | dominant cost; ~$0.06–0.30/min depending on provider |
| LiveKit | per participant-minute | small at MVP scale (free tier covers beta) |
| OCR + embeddings (one-time at build) | per Persona | cents |
| Storage | encrypted blobs | cents/Persona/month |

Realtime audio minutes are the cost driver → session time-boxing (already wanted for
*ethical* reasons) doubles as cost control. Local self-host shifts cost to the user's
hardware and is ~free to run.

## 10. Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Emotional harm / deepening denial | Med–High | ETHICS-first design, Will framing, bounded sessions, crisis routing. |
| "E2E" claim vs. realtime hop reality | High | Honest spectrum (§6); reserve strongest claim for local path. |
| Latency breaks the "really them" feeling | Med | M0 spike gates the build; tune turn detection/barge-in. |
| Voice/likeness rights & consent | Med | Consent ledger; defer cloning; still-image avatar only in MVP. |
| Realtime provider retention/training terms | Med | Contractual zero-retention; local fallback as backstop. |
| Cost runaway on heavy users | Low–Med | Session caps + trial limits + per-minute monitoring. |

## 11. Definition of Done (MVP-1 private beta)

- A user can self-host the whole stack from the README, fully local.
- Hosted user: Will onboarding → build Persona from texts/screenshots + questionnaire
  → hold a sub-second voice conversation → end with grounding + resources.
- All ETHICS checklist items pass.
- Export + permanent delete work.
- 2-year continuity policy implemented (even if not yet triggerable in beta).
- Repo is public with license, security policy, and deploy guide.
</content>

# Griefbot — Thinnest Validation Design

**Status:** Approved design (brainstorming complete) — ready for an implementation plan
**Date:** 2026-06-24
**Branch:** `claude/griefbot-mvp-webapp-usvakp`
**Scope:** "A — Thinnest validation" (concierge / Wizard-of-Oz study)
**Companion docs:** [`../DESIGN.md`](../DESIGN.md) · [`../ETHICS.md`](../ETHICS.md) · [`../PLAN.md`](../PLAN.md) (parked: full-build plan, future scope)

> Produced via the brainstorming skill. Decisions were made interactively; this
> doc is the record. Implementation planning is the next step (writing-plans),
> **not** part of this document.

---

## 0. Locked Decisions (from brainstorming)

| Fork | Decision |
|------|----------|
| Core modality | **Voice-first, real-time** (LiveKit + realtime speech-to-speech) |
| Voice identity | **Consented voice cloning** (user attests rights; deceased cannot consent) |
| Deployment target | **Hosted-first** (open repo later; one-click self-host deferred) |
| Persona engine | **Inworld for voice** (realtime speech-to-speech + cloning) **+ thin in-house persona brain** (character card + RAG over uploaded messages + grief/crisis safety), swappable. LiveKit for transport. |
| MVP scope | **A — Thinnest validation:** supervised, operator-run prototype, not a self-serve product |

Context that drove the engine decision: Inworld pivoted (2025–2026) away from a
character engine to a **real-time voice platform** (Realtime TTS-2, Realtime
Speech-to-Speech API, voice cloning, an "Agent Runtime," and open-source TTS).
There is **no off-the-shelf open-source "Inworld persona brain" to clone** — the
persona/brain is realized in OSS via patterns/components (SillyTavern Character
Cards V2 + world-info/vector memory; Letta/MemGPT for memory). So we use Inworld
as the **voice engine** and own a **thin persona layer** ourselves.

---

## 1. The One Question We're Validating

> **When a grieving person speaks with a voice persona built from their loved
> one's real texts plus a cloned voice, does it genuinely feel like them — and is
> the experience meaningful rather than harmful?**

Everything else is deferred until we have a confident yes.

**Secondary learnings:**
- What breaks the illusion (timbre, word choice, latency, factual gaps)?
- Which input carries the most signal — texts, the questionnaire, or the voice?
- What is the emotional aftermath (comfort, closure, distress, denial)?

---

## 2. What It Is

A **supervised, operator-run prototype**, not a self-serve app. A facilitator
(one of us) is present for the entire session. Product guardrails that a real
service would build (the "Will" chatbot, consent flows, accounts, billing,
automated crisis detection) are **performed by a human + script/paper**, not
engineered. We build only the irreducible core: *real-time voice conversation
with a person-specific persona.*

This is a concierge MVP: maximize learning per unit of engineering.

---

## 3. Participant Experience (one session, ~45 min)

1. **Pre-session (async, operator-assisted):** participant provides
   - a few text messages / **screenshots of conversations**,
   - a short **personality questionnaire** (temperament, humour, pet names,
     things they'd say / never say, gentle topics),
   - a **voice sample** they attest they have the right to use.
   Operator builds the persona and registers the cloned voice.
2. **In-session intro (human-delivered):** facilitator reads the honest framing
   aloud (AI representation; not a replacement; grief isn't the enemy; not
   therapy), hands over written grief/crisis resources, captures consent + rights
   attestation, and stays reachable throughout.
3. **The conversation:** participant opens a web page → joins a LiveKit room →
   speaks aloud with the persona (Inworld speech-to-speech, cloned voice), with a
   **live transcript** on screen and an **optional avatar image**. Facilitator can
   end the session at any time.
4. **Grounding close + debrief:** facilitator closes the session gently, then runs
   a structured interview (see §8).

---

## 4. What We Actually Build (minimal technical surface)

- **One web page** (LiveKit JS SDK): join room, mic capture, voice playback, live
  transcript, optional avatar image. No routing, no account UI.
- **One LiveKit Agent** (Python) that:
  - loads a **character card** built from the texts + questionnaire,
  - performs light **RAG over the uploaded messages** for per-turn memory,
  - drives **Inworld realtime speech-to-speech** using the **cloned voice**.
- **A small operator script/notebook** to: ingest texts/screenshots (OCR by hand
  if needed), generate the character card, and register the cloned voice with
  Inworld.

**Deliberately absent:** auth, any database beyond local files, payments,
self-host packaging, the built "Will" chatbot, automated safety systems.

### Component sketch

```
Browser (single page, LiveKit JS)
   │  WebRTC audio + transcript data channel
   ▼
LiveKit room (cloud)
   ▼
LiveKit Agent (Python)
   ├─ character card  (texts + questionnaire → persona definition)
   ├─ RAG over uploaded messages  (per-turn memory)
   └─ Inworld realtime speech-to-speech  (cloned voice in/out)

Operator tooling (local notebook): OCR + card generation + voice-clone registration
Storage: local files, encrypted; purged after debrief by default
```

---

## 5. Operator Runbook (the manual half)

- **Per-participant checklist:** collect material → record rights attestation →
  build character card → register cloned voice → **dry-run the persona once**
  before the participant arrives.
- **Facilitator script** covering: intro framing, consent + rights capture, crisis
  handling steps, session end, and the debrief questions.

---

## 6. Ethics — Non-Negotiables Even at Thinnest Scope

Thin scope lowers the *engineering* bar, not the *ethics* bar. With a human in
the loop, safeguards may be manual but must be present every session:

- Honest framing + grief/crisis resources delivered **every** session (scripted).
- **Rights attestation** for the cloned voice/likeness recorded **before** any
  cloning occurs.
- Live human supervision is the crisis safeguard; the facilitator ends the session
  if distress escalates.
- **Tiny, vetted participant pool** — no strangers off the internet; screen out
  anyone in acute/early grief.
- **Delete everything** (texts, voice sample, cloned voice, recordings) after the
  study unless the participant explicitly asks to keep it.

These mirror the binding requirements in [`../ETHICS.md`](../ETHICS.md), adapted
to a supervised study.

---

## 7. Data Handling

- Minimal collection; stored locally and **encrypted at rest**.
- Cloned voice registered with Inworld under **zero-retention / no-training** terms.
- **Default purge** of all participant data after the debrief.

---

## 8. How We Learn (success signal)

Structured post-session interview + a few ratings:
- **"Did it feel like them?"** (1–5)
- Emotional valence (comfort ↔ distress) and whether it felt net-positive.
- "Would you want this?" (yes/no + why).
- Open-ended: "what broke the spell" / "what landed."

**Go/no-go for scope B (lean private-beta MVP):** a clear majority of a small
participant group report it felt meaningfully like their person **and** report a
net-positive (not harmful) experience.

---

## 9. Explicitly Out of Scope

Accounts · the built "Will" chatbot · automated crisis detection · payments ·
2-year continuity policy · self-host UX · voice-matching library · mobile ·
multi-persona · scale/performance work.

---

## 10. Open Questions (to resolve in planning)

| # | Question | Leaning |
|---|----------|---------|
| 1 | How many participants for a credible signal? | 5–8 |
| 2 | Recruit from our own circle vs. screened volunteers? | TBD |
| 3 | Record audio for analysis, or transcript-only? | TBD (privacy vs. learning) |
| 4 | Inworld voice-clone minimum sample length / quality? | Confirm in a short spike |
| 5 | Character-card format — adopt Character Card V2, or a minimal bespoke schema? | TBD |

---

## 11. Next Step

Transition to **implementation planning** (writing-plans) for scope A only:
the single web page, the LiveKit + Inworld agent, the operator tooling, and the
facilitator runbook. No implementation work begins before that plan exists.
</content>

# Griefbot — A Compassionate Voice Companion for Remembering

**Status:** Idea → design in [`DESIGN.md`](./DESIGN.md), MVP plan in [`PLAN.md`](./PLAN.md)
**Date started:** 2026-06-24
**Branch:** `claude/griefbot-mvp-webapp-usvakp`

---

## 1. The Idea

A **griefbot** is an AI companion that lets a grieving person have a real-time,
voice-first conversation with a respectful, clearly-labelled *representation* of
someone they have lost. It is built from things the person actually left behind —
messages, letters, voice notes, stories told by family — and is framed
explicitly as a **memorial keepsake and grief-processing aid**, never as the real
person and never as a claim that the person "lives on."

This folder contains the product concept and an MVP implementation plan that
delivers a working web app using:

- an **Inworld-style character engine** (an open "Inworld clone") for the
  persona/brain — personality, memories, knowledge, safety guardrails;
- **real-time speech-to-speech model APIs** (e.g. OpenAI Realtime, Gemini Live)
  for natural, low-latency spoken conversation;
- **LiveKit** (WebRTC transport + the LiveKit Agents framework) to carry audio
  between the browser and the agent and to host the agent process.

## 2. Why It Matters (and Why It's Hard)

Grief tech is one of the most emotionally powerful — and most ethically loaded —
applications of conversational AI. Done carelessly it can deepen denial, exploit
vulnerable people, or put words in a dead person's mouth. Done carefully it can
be a gentle, bounded ritual: a way to hear a familiar turn of phrase again, to
say the thing left unsaid, to feel briefly accompanied.

The product's entire design is therefore organized around **honesty, consent,
and bounded use**, not maximal realism. See [`ETHICS.md`](./ETHICS.md) — it is a
first-class design document, not an afterthought.

## 3. What the MVP Is

A web app where a user can:

1. **Create a "memory profile"** of a loved one by uploading source material
   (text excerpts, anecdotes, a short personality questionnaire, optionally a
   voice sample they have the right to use).
2. **Have a live voice conversation** with the persona built from that profile,
   in the browser, with sub-second response latency.
3. **See and trust the framing** — they're welcomed by **Will**, a counselling
   helper who sets honest expectations and surfaces real grief services up front;
   persistent "AI representation, not the real person" labelling; and easy
   off-ramps to a real human for support.

The product is **open source** and can be **self-hosted** ("get a tech friend to
deploy it and verify the code") or used via a paid hosted subscription — the same
code either way.

What the MVP is **not**: a deepfake video avatar, a claim of consciousness, an
"always-on" relationship, or anything monetizing dependency.

## 4. Core User Flows

| Flow | Description |
|------|-------------|
| Welcome (Will) | The counselling helper sets honest expectations, shows real grief services, and explains how to start. |
| Onboarding & consent | User affirms relationship, rights to source material, and acknowledges the nature/limits of the tool. |
| Build memory profile | Upload a few texts / screenshots of conversations; answer a guided "who were they" questionnaire; optional avatar image. |
| Voice conversation | Press-to-talk or open-mic conversation in the browser via LiveKit; persona responds in voice, avatar shown if uploaded. |
| Ask Will / real human | If the Companion "isn't working well," step out to Will to tune it — or reach a real person for tech support. |
| Session boundaries | Sessions are time-boxed and end with a grounding/closing moment and support resources. |
| Manage & delete | View source material, edit the profile, and delete everything permanently. |

## 5. High-Level Architecture

```
Browser (Next.js web app)
   │  WebRTC audio (mic in / voice out)
   ▼
LiveKit Cloud / self-hosted SFU  ──────────────┐
   │  audio track                              │
   ▼                                           │
LiveKit Agent (Python worker)                  │ data channel: transcripts,
   ├─ Persona/Character engine ("Inworld clone")│  state, safety events
   │    • personality + memories + guardrails   │
   │    • retrieval over the memory profile     │
   └─ Realtime speech-to-speech model API ──────┘
        (STT + LLM + TTS, or unified realtime)

Persistence: Postgres (profiles, sessions, consent) + object store (audio/voice)
            + vector index (memory retrieval)
```

The persona engine sits *between* the user and the raw model: it owns the
character definition and the safety policy, and the realtime API is the
voice/reasoning runtime it drives. This separation is what keeps the persona
consistent and the guardrails enforceable.

## 6. Documents in This Folder

| File | Purpose |
|------|---------|
| [`README.md`](./README.md) | This concept overview |
| [`DESIGN.md`](./DESIGN.md) | Product design: main goal, onboarding ("Will"), persona creation, tech principles |
| [`PLAN.md`](./PLAN.md) | MVP implementation plan: stack, milestones, components |
| [`ETHICS.md`](./ETHICS.md) | Safety, consent, and ethical design requirements (binding) |
| [`notes/`](./notes/) | Raw founder brainstorms |

## 7. Status & Next Steps

- [x] Concept and MVP plan drafted
- [ ] Validate ethical framing with input from grief professionals
- [ ] Choose Inworld-clone engine vs. minimal in-house persona layer
- [ ] Spike: LiveKit Agent + realtime API end-to-end latency
- [ ] Build MVP per milestones in `PLAN.md`
</content>
</invoke>

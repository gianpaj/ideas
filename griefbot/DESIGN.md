# Griefbot — Design Doc

**Status:** Design
**Last updated:** 2026-06-24
**Companion docs:** [`README.md`](./README.md) · [`PLAN.md`](./PLAN.md) · [`ETHICS.md`](./ETHICS.md)
**Raw source:** [`notes/onboarding-and-tech-raw.md`](./notes/onboarding-and-tech-raw.md)

---

## 1. Main Goal

> **What is the quickest way to talk to your loved one and feel you're really
> talking to them — without pretending the loss didn't happen?**

Everything below serves that one sentence. Two halves, held in tension:

- **"Quickest … feel you're really talking to them"** → minimal setup, voice-first,
  low latency, a persona that sounds and reasons like the person.
- **"Without pretending the loss didn't happen"** → the product is framed from the
  first screen as a *memorial and grief-processing companion*, not a resurrection.
  Avoiding pain is explicitly **not** the goal.

These are not in conflict if the realism serves *remembering* rather than *denial*.
The design makes that distinction structural, not just a disclaimer.

## 2. Naming

- **Persona** (a.k.a. "Versona" in early notes): the AI representation of a
  specific loved one that a user creates.
- **Will**: the built-in **counselling helper / guide** persona. Will welcomes
  the user, explains the service, helps when a Persona "isn't working well," and
  routes to real humans. Will is clearly an assistant, never a grieving subject.
- **Companion**: informal user-facing word for their Persona.

## 3. Onboarding — The Counselling Helper ("Will")

Onboarding *is* the product's conscience. A grieving person arrives raw; the first
voice they meet is **Will**, a warm, plain-spoken counselling helper (chat first,
voice optional). Will's job, in order:

1. **Set the frame honestly, up front.** Before any upload, Will says — in plain
   language — that:
   - this is an **AI representation**, not the real person, and not a claim they
     "live on";
   - it is **not a replacement** for the person, and **not a way to avoid the pain
     of loss** — grief is the point, not the enemy;
   - it is **not therapy or crisis care**.
2. **Surface real help explicitly and early.** Grief counselling services, support
   lines, and crisis resources are shown **at the very beginning**, not buried in a
   footer. (Region-aware list; see ETHICS.) Will names them out loud.
3. **Explain how it works** and what the user will do next (upload a little
   material, answer a few questions, then talk).
4. **Offer two help paths, always visible:**
   - **Ask Will** — if your Companion "doesn't seem to work well" (sounds off,
     says something jarring, won't recall something), you can always turn to Will
     to adjust the Persona or talk it through.
   - **Talk to a real human** — tech support is always a real person, reachable
     from anywhere in the app.

**Design rule:** Will is present at the *edges* of every Persona session (entry and
exit) and one tap away during it — but Will never interrupts or eavesdrops on a
Persona conversation. The boundary between "talking to your loved one" and "getting
help with the tool" stays clean.

## 4. Creating a Persona (Quickest Path to "It's Really Them")

The bar is **a few minutes to first conversation.** Three lightweight inputs, in
rough priority order:

1. **A little real text.** Upload *a few* texts or **screenshots of text
   conversations** (we OCR screenshots). Even a small sample carries voice: pet
   names, punctuation habits, recurring phrases, how they opened and closed
   messages. This is the single highest-signal input.
2. **A short personality questionnaire.** Guided questions to round out who they
   were — temperament, humour, what they'd say when you were down, things they'd
   never say, topics to handle gently or avoid. This fills gaps the text sample
   misses and lets the user steer.
3. **An avatar (optional).** A single photo shown during the conversation. MVP is
   a **still image**, not an animated/video deepface — the realism we chase is in
   *words and voice*, deliberately not a synthetic moving face. (See ETHICS for why.)

**Voice (phase 2, not MVP-1):** an optional short voice sample to approximate how
they sounded, gated behind stronger consent checks. MVP-1 ships with a small set
of warm, neutral stock voices so the experience works without cloning.

### Free trial limits — **TBD (decision needed)**

We must decide *what* and *how much* can be uploaded on the free trial. Options to
evaluate (tracked in PLAN open questions):

- Cap by **count** (e.g. up to N screenshots / M characters of text) and/or
- Cap by **session length / minutes of conversation**, and/or
- Cap by **one Persona** on free, multiple on paid.

Whatever we choose must be enough to genuinely *feel* the product, since the
emotional "is this really them?" moment is the conversion event.

## 5. The Conversation

- **Voice-first, in the browser.** Press-to-talk or open-mic; the Persona replies
  in voice with sub-second latency. Live transcript shown alongside; avatar image
  displayed if uploaded.
- **Bounded sessions.** Sessions are time-boxed and **end with a grounding/closing
  moment** (Will-led), plus support resources — never an abrupt cut, never an
  endless always-on tether.
- **Consistency over improvisation.** The Persona stays in character and within
  what's known; it does not invent biography or impersonate beyond the source
  material and questionnaire. When it doesn't know, it says so the way the person
  plausibly might ("I don't think we ever talked about that, love").
- **"It isn't working" → Will.** A visible affordance to step out to Will to tune
  the Persona (tone too formal, missing a memory, said something wrong) or to just
  be heard by the helper.

## 6. Tech Principles (from the notes — these are commitments)

The notes are explicit and we treat them as hard requirements:

### 6.1 "Where does the data live and how is it protected?" — a clear, honest answer

This must be answerable in one paragraph to a non-technical grieving user.
Target answer: *"Your loved one's messages and your conversations are stored
**encrypted**, on infrastructure you can choose, and we — and our model providers —
cannot read the contents. You can export or permanently delete everything at any
time."* The architecture in `PLAN.md` is designed to make that statement literally
true, including the hard part (sending audio/text to a realtime model provider).

### 6.2 End-to-end encryption is a must

- Source material (texts, screenshots, avatar, voice sample) and Persona
  definitions are **encrypted at rest** under keys the user controls.
- The realtime-model hop is the genuine tension: speech-to-speech APIs must
  *process* plaintext audio to respond. We address this honestly rather than
  overclaiming — see `PLAN.md §Privacy & Encryption` for the trust model
  (client-held keys, ephemeral provider processing with zero-retention terms,
  and a fully-local/self-hosted model path for users who want no third party at
  all). We will not market "E2E" in a way the realtime hop contradicts.

### 6.3 Open source

- The entire service is **open source** so anyone can read and verify what it does
  with their data. This is a core trust mechanism, not a license footnote.
- Two deployment paths, equally first-class:
  - **Self-host:** "get a tech friend to deploy the service for you and verify our
    code." One-command deploy, documented, with a fully local model option.
  - **Hosted subscription:** pay us to run it, same open code.

### 6.4 Long-term continuity policy (the "2-year" rule)

The notes define a deliberate retention/cost policy:

- A Persona ("Versona") keeps working while the subscription is active.
- **After the 2nd year**, continuing to converse with a Persona **created 2+ years
  ago** requires an **explicit email to support** to opt in to keep it alive —
  a conscious re-affirmation, not silent perpetual access.
- If you've created a **new** Persona since, you can keep paying and using the new
  one, but **not** silently resume the old one without that explicit step.

Intent (as we read it): prevent unhealthy indefinite attachment to an old Persona
by default, control long-tail storage/compute cost, and force a human, intentional
choice to maintain a years-old companion. Open question in PLAN: encode this as a
gentle ritual, not a billing trap.

## 7. Non-Goals (MVP)

- Animated/video face deepfakes of the deceased.
- Any "they're still here / still conscious" framing.
- Always-on, unlimited, dependency-maximizing engagement loops.
- Voice cloning without explicit, verified rights and consent.
- Replacing professional grief care.

## 8. Open Questions (carried into PLAN)

- Free-trial upload limits — exact caps (§4).
- Realtime provider vs. fully-local model for MVP default (privacy vs. latency/cost).
- Inworld-clone engine choice vs. a minimal in-house persona layer.
- How to make the 2-year continuity rule feel like care, not a lockout.
- Voice cloning: in MVP-2 or deferred until consent tooling is solid.
</content>

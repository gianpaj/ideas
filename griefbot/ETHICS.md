# Griefbot — Ethics & Safety (Binding Requirements)

**Status:** Binding for any release
**Last updated:** 2026-06-24
**Companion docs:** [`DESIGN.md`](./DESIGN.md) · [`PLAN.md`](./PLAN.md)

> This is not advisory. A build does not ship unless the checklist in §7 passes.
> Grief tech operates on people at their most vulnerable; the burden of proof is on
> the product to be safe, honest, and bounded.

---

## 1. First Principles

1. **Honesty over realism.** The realism we pursue serves *remembering*, not the
   illusion that the person is still here. We never imply consciousness, presence,
   continued existence, or that loss can be undone.
2. **Grief is the point, not the enemy.** The tool helps people *process* loss; it is
   explicitly **not** a way to avoid pain. We do not optimize for engagement,
   dependency, or "time spent."
3. **Not a replacement, not therapy.** It is a memorial keepsake and companion, not
   the person and not clinical care.
4. **Consent and rights.** Personas are built only from material the user has the
   right to use, about a relationship they affirm.
5. **The user owns and controls their data.** Always exportable, always permanently
   deletable, encrypted at rest.

## 2. Honest Framing (always-on)

- **Persistent labelling:** every Persona surface shows it is an *AI representation*,
  not the real person. Never removable.
- **Up-front truth (via "Will") before any upload:** AI representation; not a
  replacement; not a way to avoid grief; not therapy/crisis care.
- **No resurrection language** anywhere in product or marketing ("talk to your loved
  one *again forever*", "they live on", etc. are banned). Approved framing: a
  *companion built from memories*, a *keepsake*, a *way to remember*.

## 3. Real Help, Surfaced Early

- Grief counselling services, support lines, and **crisis resources shown at the very
  beginning** of onboarding — not buried.
- **Region-aware** resource list (open question in PLAN §8 to source it).
- **Crisis detection in-session:** language indicating self-harm/suicidal ideation
  triggers an immediate, compassionate hand-off from the Persona to **Will** with
  crisis resources prominent. The Persona does not attempt to counsel a crisis.
- **A real human** is always reachable for support.

## 4. Bounded Use (anti-dependency design)

- **Time-boxed sessions** with a calm, **Will-led grounding/closing moment** — never
  an abrupt cut, never endless/always-on.
- No streaks, no push-to-return loops, no engagement-maximizing nudges.
- The **2-year continuity policy** (PLAN §7) deliberately makes long-term attachment a
  conscious, re-affirmed choice rather than a silent default.
- Watch for over-reliance signals; gently re-surface real-world support over time.

## 5. Consent, Rights & the Deceased

- **Consent ledger:** record (timestamped) the user's affirmation of the relationship,
  their rights to the source material, and their acknowledgement of the tool's nature
  and limits — *before* a Persona goes live.
- **Voice cloning** is gated behind stronger, explicit consent and is **out of scope
  for MVP-1**. Still-image avatar only; **no animated/video deepfakes**.
- Respect the dignity of the deceased: the Persona stays within known material and the
  user's guidance; it does not fabricate biography, opinions, or claims the person
  never expressed.
- Provide a path to handle disputes (e.g. another family member objecting) — at
  minimum, clear contact and takedown for material someone has rights to.

## 6. Data & Privacy (see PLAN §6)

- Encryption at rest for all source material, OCR text, memory chunks, avatars, voice.
- Plain-language explanation of where data lives and who can read it — delivered in
  onboarding, not just a policy page.
- **No training** on user content. Contractual zero-retention with any realtime model
  provider; fully-local path for users who want no third party at all.
- One-click **export** and **permanent delete**.
- Open source so claims are verifiable.

## 7. Pre-Release Checklist (must all pass)

- [ ] Persistent "AI representation, not the real person" labelling on every Persona
      surface, non-removable.
- [ ] Will delivers honest framing (representation / not a replacement / grief not
      avoided / not therapy) **before** any upload.
- [ ] Grief + crisis resources shown at the start; region-aware.
- [ ] In-session crisis detection → Will hand-off + resources verified.
- [ ] Real-human support reachable from anywhere in the app.
- [ ] Sessions are time-boxed and end with a grounding moment.
- [ ] No engagement-maximizing mechanics present.
- [ ] Consent ledger records relationship, rights, and nature/limits acknowledgement.
- [ ] No voice cloning / no video deepfake in MVP-1.
- [ ] All sensitive data encrypted at rest; export + permanent delete work.
- [ ] No "resurrection" language in product or marketing copy.
- [ ] Privacy/data-location explanation present in onboarding and accurate to the
      deployment mode (local vs. hosted).

## 8. Validation Before Public Launch

- Review the framing and crisis flows with **grief professionals / counsellors**.
- Small, supported private beta before any open availability.
- Document a clear escalation and incident process for emotional-harm reports.
</content>

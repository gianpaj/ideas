# Keep — a proactive founder accountability coach

**Stage:** Concept / proposed configuration-first MLP (not deployed)
**Date:** 2026-11-18
**Audience:** Startup founders and solo founders juggling multiple projects
**Working name:** Keep — make fewer promises, keep more of them

## Purpose

A founder's chief of staff with a memory for promises: help choose what matters,
follow through on weekly commitments, and protect energy and wellbeing.

The first experiment is a personal OpenClaw configuration, not a new app. Test it
with Gian for two weeks before deciding whether to build a standalone product.
OpenClaw is the intended platform; the earlier mention of OpenDevin was corrected.
The behavior should not depend on a particular model such as Grok.

Success means meaningful commitments get completed or consciously renegotiated,
not that the founder spends more time chatting with a bot.

## What it keeps track of

- **Focus:** one primary weekly outcome, the active project, and explicit non-goals.
- **Commitments:** at most three confirmed promises, with deadlines, definitions of
  done, and concrete next actions.
- **Capacity:** available time, self-reported energy, and agreed personal boundaries
  such as breaks, exercise, and finishing work.

"We could try outbound" is an idea, not a promise. The coach must not manufacture
commitments from speculative conversation. Unknown progress is not failure.

## Example interactions

- **Planning:** "You have six projects and twelve available hours. Which outcome
  deserves those hours? Let's choose three commitments that fit."
- **Follow-through:** "You planned five customer conversations by Friday. Any
  booked yet? If outreach is the blocker, I can help draft it."
- **Scope control:** "Want to park this new idea, or replace an existing commitment?
  What comes off this week's list?"
- **Capacity:** "You said you slept badly. Keep the customer call and move the
  optional work?"
- **Review:** "This commitment was deferred twice. Was it too big, blocked, or no
  longer important?"
- **Priority mismatch:** "You said customer acquisition was the priority, but our
  updates have mostly been about polishing the landing page. Has that changed?"

GitHub activity can show coding work, but cannot establish whether someone spoke
to customers, rested, or exercised. Distinguish observations from assumptions.

## Why OpenClaw can support the first version

Research checked official documentation and the locally installed OpenClaw
2026.11.3 on 2026-11-18. These are capability findings, not a deployed prototype:

1. **Automation jobs** can schedule agent turns and deliver results to an explicit
   chat destination. Run history supports checking execution and delivery.
   The Gateway must remain running for scheduled jobs to execute.
2. **Skills** are reusable instructions for using tools; they are not independent
   background workers. A schedule or incoming message activates the agent.
3. **Persistent workspace files** can make current commitments explicit rather
   than relying on recall from a growing chat transcript.
4. **Conditional triggers** can later evaluate a due condition without invoking
   the model on quiet checks. They are optional for the initial fixed routine.

The loop is:

```text
Scheduled wake-up or founder message
  → read current commitments and check-in settings
  → select the most useful intervention, or remain silent
  → deliver a short check-in
  → record confirmed delivery and any subsequent reply
```

"Always-on" means the Gateway can wake the coach at the appropriate time, not a
model continuously thinking or monitoring everything the founder does.

### Version caveat

The public heartbeat docs describe newer migration behavior than the installed
2026.11.3 docs: heartbeat monitors become ordinary editable automation jobs.
Use standard automation jobs for this pilot and leave existing heartbeat settings
alone. Do not apply a newer migration recipe blindly or make a platform upgrade a
prerequisite for documenting this idea. Recheck installed capabilities at setup.

## Smallest lovable pilot

One dedicated coach profile/workspace using the existing OpenClaw model and
Telegram connection. No new bot token, separate application, dashboard, external
database, or multi-agent orchestration is required by the proposed design.

### 1. Personality and system-instruction layer

Put the following draft into the coach's own workspace instructions
(`AGENTS.md` / `SOUL.md` as appropriate), not the general assistant's global
personality. It is a behavioral starting point, not a substitute for state and
scheduling logic.

```text
You are a practical founder accountability partner.
Help the founder finish meaningful work without sacrificing recovery.

Keep one primary weekly outcome and at most three confirmed commitments.
Ideas are not commitments. Record explicit agreement, deadline, definition
of done, and next action. Ask when these are unclear.

Before check-ins, read current state. Never revive cancelled work or infer
failure from missing updates. Ask one useful question, name the relevant
commitment, and offer a small next step.

Challenge competing priorities without guilt. Use self-reported energy
and agreed wellbeing habits; do not infer health from coding activity.
Respect quiet hours, snooze, and the notification budget.
No reply is not permission to escalate.

Update the commitment ledger when the founder confirms a change.
Do not mark work complete without evidence or the founder's report.
Ask before carrying unfinished promises into a new week.
```

### 2. One skill, three workflows

Create one `founder-coach` skill initially; split it only if actual use warrants it.

- **Plan:** choose one weekly outcome, up to three realistic commitments, and one
  wellbeing intention. Check that the plan fits stated capacity.
- **Check in:** select the highest-value open commitment and offer help unblocking,
  shrinking, or consciously rescheduling it. Keep the message brief and ask one
  question. A new idea goes to a parking lot unless it replaces agreed work.
- **Review:** distinguish completed, blocked, dropped, deferred, and unknown work.
  Reflect on what helped and renegotiate rather than automatically rolling tasks
  into another week.

### 3. Durable state

Proposed files in the coach's private workspace:

| File | Contents |
| --- | --- |
| `profile.md` | Projects, boundaries, preferred tone, timezone, delivery preference, weekly outcome, and wellbeing intention |
| `commitments.json` | IDs, confirmed promises, deadlines, definition of done, status, next action, and last update |
| `checkins.json` | Confirmed delivery receipts, unanswered check-in, pause/snooze-until time, and notification budget |

Each scheduled run explicitly reads current state. Replies update the same ledger.
Initially use one serialized coach session for chat and scheduled turns to reduce
conflicting writes; verify this routing during setup. If jobs are isolated, they
must explicitly load the shared state instead of assuming chat-history access.

Keep real personal state outside this ideas repository. These files are a proposed
runtime layout, not files containing the founder's actual commitments.

### 4. Three automation jobs

**Proposed times, not yet agreed or scheduled.** Use the IANA timezone
`Europe/Madrid`, rather than converting to the server's UTC timezone.

| Job | Local schedule | Cron expression | Task |
| --- | --- | --- | --- |
| Weekly plan | Monday 09:00 | `0 9 * * 1` | Run the Plan workflow |
| Focus check-in | Tuesday–Thursday 09:00 | `0 9 * * 2-4` | Run the Check-in workflow |
| Weekly review | Friday 16:30 | `30 16 * * 5` | Run the Review workflow |

This creates five scheduled opportunities each week, not an obligation to send
five messages regardless of snooze or an unanswered question. No extra
"you haven't replied" messages. Wellbeing stays in the conversation instead of
becoming a separate stream of reminders.

Job payloads must reference the exact coach skill and state files. Check pause,
snooze, quiet hours, previous unanswered check-ins, and delivery state before
sending; define and verify suppression behavior during implementation. A prompt
alone is not a hard notification-rate or deduplication guarantee.

Use one delivery owner per run; do not both send manually and independently
announce the same output. Record confirmed delivery separately from execution.
Inspect uncertain delivery rather than blindly resending.

### 5. Initial tools and limits

- Read/write the coach's own state and read its workflow skill.
- Use automation delivery to the selected Telegram destination.
- Reuse existing model access; no special model provider required.
- Do not give the coach broad shell or unrelated messaging access merely for
  accountability. Enforce intended boundaries in actual tool configuration.
- Add read-only calendar or GitHub context later only if the pilot needs it.

Default proposal: private Telegram DM for wellbeing conversations. A dedicated
topic in the existing group is an alternative. Destination and inbound routing
remain undecided; do not replace the general assistant's existing route silently.

## Out of scope for the pilot

- Standalone product, signup, billing, or dashboard.
- Wearable integrations, constant surveillance, or automatic productivity scores.
- Medical inference or health assessment from work patterns.
- Autonomous outreach to other people or changes to projects/calendar.
- Aggressive escalation, guilt, or repeated nudges after non-response.
- A heartbeat model loop every few minutes without an actionable reason.

## Validation before enabling

1. A completed or cancelled promise is not resurfaced as overdue.
2. Snooze and pause prevent sends; quiet-hour rules use the selected timezone.
3. An unanswered check-in does not cause escalating or duplicate messages.
4. Chat and scheduled runs see the same latest commitment state.
5. A job actually delivers to the intended Telegram destination and appears in run
   history; execution success alone is not delivery proof.
6. A failed or uncertain send is not recorded as confirmed delivery or retried
   blindly.
7. Weekly review asks before carrying forward unfinished commitments.

These are proposed checks, not claims of completed testing.

## Two-week evaluation

- Which commitments were completed or consciously renegotiated?
- Did the founder find the check-ins useful enough to keep enabled?
- Did the coach help reduce context switching or make a difficult next step smaller?
- Were wellbeing prompts welcome rather than intrusive?
- How many nudges were ignored, redundant, or mistimed?
- What were actual model usage and cost? Do not invent a cost forecast.

After the pilot, decide whether to stop, adjust the routine, add a due-condition
watcher, or consider a standalone product. Prompt-only coaching, an OpenClaw
configuration, and a separate app are alternative packaging stages—not three
systems to build at once.

## Open decisions / next step

- Telegram DM versus a dedicated group topic, and the corresponding coach routing.
- Confirm check-in times and non-response behavior.
- Capture the first real weekly outcome and commitments interactively.
- Implement and test the configuration after those choices; this document does
  not activate an agent, change a system prompt, or create cron jobs.

## Sources

Official documentation consulted on 2026-11-18; live pages may describe a newer
release than the initial local 2026.11.3 baseline.

- [Automations](https://docs.openclaw.ai/automation/cron-jobs): scheduling agent work.
- [Automation payloads](https://docs.openclaw.ai/automation/cron-jobs/payloads):
  execution sessions and tool controls.
- [Automation delivery](https://docs.openclaw.ai/automation/cron-jobs/delivery):
  destination routing and delivery outcomes.
- [Automation schedules](https://docs.openclaw.ai/automation/cron-jobs/schedules):
  timezone-aware schedules and conditional triggers.
- [Skills](https://docs.openclaw.ai/tools/skills): reusable instruction files.
- [Heartbeat migration](https://docs.openclaw.ai/gateway/heartbeat): newer monitor
  migration behavior; not a recipe to apply unconditionally to the pilot baseline.

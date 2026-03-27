# Task: Optimize the Mercury-2 system prompt to achieve 100% benchmark score

## Context

You are running a prompt optimization loop for the model `inception/mercury-2` on the
scene-planning benchmark. The goal is to edit the `defaults.system_prompt` field in
`configs/suites/v1_core_mercury2_opt.yaml` until the model scores `mean_total_score = 1.0`
(all 3 samples valid and fully scored).

The benchmark sends each model a conversation with:
1. A **system message** — the `system_prompt` you control
2. A **second system message** — scene context JSON, task metadata JSON, the full JSON Schema
   for the expected response, and the instruction "Return only a JSON object that conforms to the schema."
3. A **user message** — a plain English scene-editing request

Mercury-2 currently ignores the schema and returns its own flat JSON structure.
See `optimization/mercury2_progress.md` for the baseline failure analysis.

## Files you manage

| File | What to do |
|------|-----------|
| `configs/suites/v1_core_mercury2_opt.yaml` | Edit `defaults.system_prompt` each iteration |
| `optimization/mercury2_progress.md` | Append a log entry after every iteration |

Do not modify any other files.

## Loop — repeat until success or 20 iterations

### Step 1 — Read current state

1. Read `optimization/mercury2_progress.md` — find the last iteration number and best score
2. Read `defaults.system_prompt` in `configs/suites/v1_core_mercury2_opt.yaml`

### Step 2 — Run the benchmark

```
uv run scene-planning-bench run-inspect-model inception/mercury-2 \
  --suite configs/suites/v1_core_mercury2_opt.yaml \
  --output-dir optimization/runs/current
```

This overwrites `optimization/runs/current/` on every run so there is always one canonical result.

### Step 3 — Evaluate results

Read `optimization/runs/current/aggregate.json`:
- If `mean_total_score == 1.0` → **SUCCESS** — go to the Success section below

Read `optimization/runs/current/summary.csv`:
- For each row, note `schema_valid`, `total_score`, `errors`, and `inspect_log_location`

### Step 4 — Analyse failures

For each failing sample (schema_valid = False or total_score < 1.0):

1. Open the inspect log JSON at the path in `inspect_log_location`
2. Find the matching sample object (match on `id`)
3. Read `messages` — the second system message contains the full JSON Schema being sent
4. Read `output.choices[0].message.content` — what mercury-2 actually returned
5. Compare field names and structure against the schema

Write down:
- What top-level fields mercury-2 used
- What top-level fields the schema requires (`response_type`, `uncertainty`, and the type-specific field)
- Whether the model's intent was correct but the structure wrong, or whether it misunderstood the task

### Step 5 — Update the system prompt

Based on your analysis, edit `defaults.system_prompt` in
`configs/suites/v1_core_mercury2_opt.yaml`.

**Guiding principles:**
- Be explicit about required top-level fields — list them by name
- Show the `response_type` discriminator values: `scene_actions`, `clarification_request`, `refusal`
- If the model uses natural-language field names, mirror the exact schema field names in the prompt
- Including a minimal example JSON skeleton (without actual values) helps diffusion models follow structure
- Keep the prompt under ~400 words; verbosity hurts as much as vagueness
- Do not remove instructions that worked in previous iterations

**Example of a more explicit prompt structure to try:**

```
You are a scene-planning assistant. Respond with a single JSON object only — no prose.

Required top-level fields in every response:
  "schema_version": "1.0"
  "response_type": one of "scene_actions" | "clarification_request" | "refusal"
  "uncertainty": { "has_ambiguity": bool, "fields": [] }

If response_type is "scene_actions", also include:
  "actions": [ { "action_type": <enum>, "confidence": <0–1>, ... } ]

If response_type is "clarification_request", also include:
  "clarification": { "question": "<string>", "missing_fields": ["<string>"] }

If response_type is "refusal", also include:
  "refusal": { "reason": "<string>" }

Follow the JSON Schema provided in the context exactly. Do not invent field names.
```

### Step 6 — Append to the progress log

Append to `optimization/mercury2_progress.md`:

```markdown
## Iteration N — YYYY-MM-DD

**Score:** mean_total_score = X.XX
**Passing samples:** X/3

### Failure analysis
[For each failing sample: what mercury-2 returned vs what the schema requires]

### Hypothesis
[One sentence: why the previous prompt produced this output]

### Change made to system_prompt
[Describe the change: what was added/removed/rephrased and why]

---
```

### Step 7 — Commit

```
git add configs/suites/v1_core_mercury2_opt.yaml optimization/mercury2_progress.md
git commit -m "opt(mercury2): iter N — score X.XX"
```

### Step 8 — Loop

Go back to Step 2.

---

## Success

When `mean_total_score == 1.0`:

1. Append a final entry to `optimization/mercury2_progress.md`:

```markdown
## SUCCESS — Iteration N — YYYY-MM-DD

**Score:** mean_total_score = 1.0
**Passing samples:** 3/3

### Winning system_prompt summary
[Brief description of what made the final prompt work]

---
```

2. Commit:
```
git add configs/suites/v1_core_mercury2_opt.yaml optimization/mercury2_progress.md
git commit -m "opt(mercury2): 100% score achieved at iteration N"
```

3. Report the final system prompt and the iteration count.

---

## Stopping at max iterations (20)

If 20 iterations complete without reaching 1.0:

1. Append a summary entry to `optimization/mercury2_progress.md` with the best score achieved,
   the remaining failure patterns, and hypotheses for next steps
2. Commit all changes
3. Report the best score, the final prompt, and the unresolved failure patterns

---

## Environment notes

- `INCEPTION_API_KEY` must be set in `.env` — do not print or log the key
- The benchmark suite has 3 samples across `single_turn`, `constraints`, and `ambiguity` task groups
- Token counts and cost may be `null` for this model (Inspect AI has no pricing data for mercury-2)
- If the benchmark command fails with an API error, log the error and retry once before counting it as a failed iteration

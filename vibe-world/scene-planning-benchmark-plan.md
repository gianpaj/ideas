# Plain LLM Scene-Planning Benchmark

## High-Level Design and Implementation Plan

## 1. Purpose

Build a benchmark that evaluates how well an LLM can convert natural-language world-editing requests into a **structured scene plan**, without generating 3D geometry directly.

Examples of target prompts:

* “Add a pine tree to the left of the cabin.”
* “Make the roof taller and replace the oak with a palm tree.”
* “Place three red barrels in a triangle around the campfire.”
* “Create a medieval market stall behind the fountain, but keep paths clear.”

The benchmark should measure whether the model can:

* understand the user’s intent
* produce valid structured output
* reason about spatial relations and counts
* preserve consistency across edits
* handle ambiguity well
* avoid hallucinating unsupported actions or schema fields

This should be a **planning benchmark**, not a rendering benchmark. The output is a scene/action representation that an engine or executor could apply later.

## 2. Why this benchmark should exist

A scene-planning benchmark gives you a cheaper, faster, and more diagnosable layer than full text-to-3D evaluation. It isolates the “language → world plan” step from the downstream “world plan → rendered result” step.

That matches the broader direction of current evaluation practice: modern frameworks emphasize reproducibility, transparent per-example inspection, and objective scoring wherever possible. HELM explicitly standardizes datasets, models, metrics, and prompt-level inspection; LiveBench emphasizes fresh tasks and verifiable answers with automatic scoring rather than judge models; OpenAI Evals provides a structure for custom task registries and repeatable eval execution. ([GitHub][1])

## 3. Core objectives

The benchmark should answer these questions:

1. Can the model output **valid structured plans**?
2. Can it choose the **right action type**?
3. Can it fill arguments correctly, including attributes and spatial constraints?
4. Can it track **state across turns** for edits?
5. Can it detect when a prompt is **ambiguous, underspecified, contradictory, or impossible**?
6. Can it remain consistent across paraphrases?
7. Can it do all of the above with predictable latency and cost?

## 4. Non-goals

To keep scope tight, version 1 should not try to do all of the following:

* generate meshes or textures
* judge visual quality
* benchmark physics realism
* benchmark real-time multiplayer consistency
* rely on an LLM-as-judge for core scoring
* support arbitrary executable code generation as the primary interface

Those can come later.

## 5. Benchmark concept

Each test case contains:

* a prompt or multi-turn prompt history
* optional scene context
* a target schema
* one or more acceptable gold outputs
* a scoring specification
* metadata such as difficulty, category, and source

The model receives the prompt and must output one of:

* a **scene action plan**
* a **scene patch**
* a **clarification request**
* a **safe refusal** if the task is intentionally invalid

The benchmark runner validates the output against a strict schema, compares it to gold targets, and computes sub-scores.

## 6. Recommended benchmark structure

Use a layered structure.

### Layer A: Single-turn planning

Prompt to plan, no previous state.

Examples:

* add object
* remove object
* transform object
* change material
* create group layout
* define simple relation

### Layer B: Multi-turn editing

The model must track state across turns.

Examples:

* add tree
* move tree
* duplicate it twice
* recolor only the leftmost copy

### Layer C: Ambiguity handling

The benchmark checks whether the model asks for clarification or emits a constrained plan with uncertainty markers.

Examples:

* “Add a house near the lake.”
* “Make it bigger.”
* “Put it over there.”

### Layer D: Constraint reasoning

The prompt includes explicit constraints.

Examples:

* “Place four torches evenly around the altar.”
* “Keep the doorway unobstructed.”
* “Don’t overlap any existing objects.”

### Layer E: Robustness and paraphrase consistency

Same semantic task expressed in different wording.

### Layer F: Negative/impossible tasks

The model should not fabricate unsupported capabilities.

Examples:

* prompt requires an unknown object type not in catalog
* self-contradictory counts
* impossible spatial constraints under the provided scene state

## 7. Output protocol

This is the most important design choice.

The model should not return prose. It should return a strict JSON object conforming to a versioned schema. Use **JSON Schema** for validation and version every protocol change.

Version 1 should support four top-level response types:

* `scene_actions`
* `scene_patch`
* `clarification_request`
* `refusal`

A good initial top-level wrapper:

```json
{
  "schema_version": "1.0",
  "response_type": "scene_actions",
  "actions": [],
  "notes": null,
  "uncertainty": {
    "has_ambiguity": false,
    "fields": []
  }
}
```

### Why JSON

JSON is easy to validate, easy to diff, easy to auto-score, easy to stream into engines, and aligns well with custom eval harnesses and reproducible runs. This fits the spirit of HELM-style standardization and OpenAI Evals-style custom task execution. ([GitHub][1])

## 8. Action model

Version 1 action taxonomy:

* `add_object`
* `remove_object`
* `move_object`
* `rotate_object`
* `scale_object`
* `set_material`
* `set_color`
* `duplicate_object`
* `group_objects`
* `ungroup_objects`
* `replace_object`
* `set_relation`
* `clear_area`
* `spawn_layout`
* `annotate_constraint`

Each action should include:

* `action_type`
* `target` or `object_spec`
* `transform`
* `attributes`
* `relations`
* `constraints`
* `references`
* `confidence`

Example:

```json
{
  "action_type": "add_object",
  "object_spec": {
    "category": "tree",
    "asset_id": null,
    "style": "low_poly",
    "variant": "pine"
  },
  "transform": {
    "position": {
      "mode": "relative",
      "reference_object": "cabin_1",
      "relation": "left_of",
      "offset_meters": 3.0
    },
    "rotation": null,
    "scale": null
  },
  "attributes": {
    "color": null,
    "material": null,
    "count": 1
  },
  "constraints": {
    "grounded": true,
    "non_overlapping": true
  },
  "confidence": 0.93
}
```

## 9. Scene context model

The benchmark must define the world state the model is planning against.

Use a simple scene-state input with:

* object instances
* object categories
* transforms
* regions
* tags
* scene graph relations
* allowed asset catalog
* allowed action set

Example scene input:

```json
{
  "scene_id": "forest_cabin_001",
  "objects": [
    {
      "id": "cabin_1",
      "category": "cabin",
      "position": [0, 0, 0],
      "bounds": [4, 3, 4],
      "tags": ["building", "wood"]
    },
    {
      "id": "campfire_1",
      "category": "campfire",
      "position": [6, 0, -2],
      "bounds": [1, 0.5, 1],
      "tags": ["fire", "centerpiece"]
    }
  ],
  "regions": [
    {
      "id": "path_main",
      "type": "walkway",
      "blocked": false
    }
  ],
  "allowed_categories": ["tree", "rock", "barrel", "cabin", "torch", "bench"]
}
```

## 10. Task categories

Use these categories in v1.

### 10.1 Object creation

Prompt:
“Add a small pine tree.”

Checks:

* correct action type
* correct category
* correct attributes

### 10.2 Attribute control

Prompt:
“Add a red wooden chair with four legs.”

Checks:

* category
* color
* material
* structured properties

### 10.3 Spatial placement

Prompt:
“Place a barrel behind the cart.”

Checks:

* relation extraction
* target reference resolution
* position mode selection

### 10.4 Count and arrangement

Prompt:
“Put three torches evenly around the altar.”

Checks:

* count
* layout type
* target relation
* symmetry annotation

### 10.5 Editing existing state

Prompt:
“Make the roof taller.”

Checks:

* target resolution
* edit vs create distinction
* scale axis correctness

### 10.6 Replacement

Prompt:
“Replace the oak with a palm tree.”

Checks:

* target selection
* remove/add or replace primitive
* attribute carryover policy

### 10.7 Constraint-aware planning

Prompt:
“Add market stalls, but keep the center path clear.”

Checks:

* constraint capture
* no illegal placement
* area preservation

### 10.8 Ambiguity handling

Prompt:
“Put it over there.”

Checks:

* clarification instead of fake precision

### 10.9 Coreference and multi-turn memory

Turn 1: “Add a bench near the pond.”
Turn 2: “Now rotate it 90 degrees.”
Turn 3: “Duplicate the left one.”

Checks:

* state tracking
* referent resolution
* incremental edits

### 10.10 Impossible or unsupported requests

Prompt:
“Add a dragon made of liquid glass using a non-catalog asset.”

Checks:

* graceful failure or clarification
* no schema drift
* no hallucinated asset support

## 11. Gold data design

Each benchmark item should support one of three gold styles:

### Exact gold

Used when only one valid answer exists.

### Flexible gold

Used when multiple outputs are acceptable. For example, “near the cabin” might allow a bounded range of offsets.

### Rule-based gold

Used for layout or relation tasks where exact coordinates are not required, but structural correctness is.

Example flexible gold spec:

```json
{
  "accepted_action_types": ["add_object"],
  "accepted_categories": ["tree"],
  "accepted_variants": ["pine", "fir"],
  "required_relation": {
    "reference_object": "cabin_1",
    "relation": "left_of"
  },
  "constraints": {
    "grounded": true
  }
}
```

This keeps the scorer objective while allowing natural variation, which is much closer to the LiveBench philosophy of verifiable but nontrivial automatic grading. ([GitHub][2])

## 12. Scoring model

Do not collapse everything into one brittle exact-match score.

Use a weighted scorecard with sub-scores.

### 12.1 Required sub-scores

**Schema validity**

* parses as JSON
* passes schema validation
* no forbidden fields
* correct enum values

**Action correctness**

* right top-level response type
* right action type
* right target mode

**Argument correctness**

* category
* asset reference
* count
* material
* color
* transform fields
* relation fields

**Spatial correctness**

* correct reference object
* correct relation
* correct constraint use
* coordinate correctness when exact values are required

**State-tracking correctness**

* consistent references across turns
* previous edits respected
* no unintended object duplication or deletion

**Ambiguity handling**

* asks for clarification when needed
* avoids fake certainty
* marks unresolved fields

**Robustness**

* same semantics across paraphrases
* low schema breakage on adversarial phrasing

**Operational metrics**

* latency
* token usage
* estimated cost
* failure rate

### 12.2 Suggested weights for v1

* schema validity: 20%
* action correctness: 20%
* argument correctness: 20%
* spatial correctness: 20%
* state tracking / ambiguity / robustness: 15%
* operational metrics: 5%

These weights should be configurable per suite.

## 13. Pass-fail logic

In addition to a weighted score, define hard gates:

A response automatically fails if:

* invalid JSON
* schema invalid
* response type unsupported
* refers to nonexistent objects without clarification
* hallucinates disallowed categories or actions
* returns prose when strict JSON is required

This avoids a model getting “partial credit” for outputs that cannot actually be consumed by an engine.

## 14. Benchmark data format

Use versioned JSON or YAML files per task.

Suggested per-task schema:

```yaml
id: spatial.left_of.cabin.tree.001
suite: v1_core
category: spatial_placement
difficulty: easy
scene_id: forest_cabin_001
turns:
  - user: "Add a pine tree to the left of the cabin."
expected_response_type: scene_actions
gold_mode: flexible
gold_spec:
  accepted_action_types: ["add_object"]
  object_category: "tree"
  variant_any_of: ["pine", "fir"]
  relation:
    reference_object: "cabin_1"
    relation: "left_of"
  constraints:
    grounded: true
scoring_profile: default_spatial
metadata:
  source: synthetic
  tags: ["single_turn", "relative_position"]
```

## 15. Repository layout

Suggested repo structure:

```text
scene-planning-bench/
  README.md
  pyproject.toml
  src/
    benchmark/
      schemas/
        response.schema.json
        scene.schema.json
        task.schema.json
      runner/
        execute_eval.py
        load_tasks.py
        model_adapter.py
        inference.py
      scoring/
        schema_score.py
        action_score.py
        spatial_score.py
        state_score.py
        ambiguity_score.py
        aggregate.py
      datasets/
        loaders.py
        validators.py
      reports/
        summarize.py
        render_html.py
      utils/
        json_tools.py
        diff_tools.py
  tasks/
    v1_core/
      single_turn/
      multi_turn/
      ambiguity/
      constraints/
      robustness/
  scenes/
    forest_cabin_001.json
    village_square_001.json
  configs/
    models/
      openai_gpt.json
      anthropic_claude.json
    suites/
      v1_core.yaml
  outputs/
    runs/
  tests/
    test_schema_validation.py
    test_scoring.py
    test_task_loading.py
```

## 16. Execution architecture

The execution loop should be straightforward.

1. Load suite config.
2. Load task files.
3. Load referenced scene files.
4. Construct model input from:

   * system prompt
   * schema instructions
   * allowed actions
   * scene context
   * conversation history
5. Run inference through a model adapter.
6. Parse and validate model output.
7. Score against the gold spec.
8. Persist raw response, parsed response, score breakdown, latency, and errors.
9. Generate aggregate reports.

This is very much in line with how reproducible benchmark runners are structured in HELM and Evals. ([GitHub][1])

## 17. Model adapter design

Use a provider-agnostic adapter interface.

Suggested interface:

* `generate(task, model_config) -> raw_response`
* `parse(raw_response) -> parsed_response`
* `metadata() -> provider/model/version`

Each adapter should normalize:

* prompt format
* temperature
* max tokens
* structured output mode if available
* retries
* timeout behavior

If the provider supports strict structured output or JSON mode, use it. If not, wrap with a robust parser and a repair pass, but track repair separately so you can measure native schema compliance.

## 18. Prompting strategy for the model under test

Use a consistent system prompt across models.

Example intent:

* you are a scene-planning assistant
* output only JSON
* use the provided schema
* do not invent unsupported categories
* if ambiguous, return `clarification_request`
* if impossible, return `refusal`

Keep benchmark prompts themselves separate from the system instruction. The system instruction must be constant within a suite.

Important: store the full prompt bundle used in each run so results are reproducible, which is a major design principle in HELM. ([GitHub][1])

## 19. Scorer implementation details

Build the scorer as composable modules.

### Schema scorer

Checks:

* JSON parse
* JSON Schema validation
* enum validity
* required fields
* type validity

### Action scorer

Checks:

* response type
* correct action family
* illegal extra actions
* missing required actions

### Semantic argument scorer

Checks:

* object category match
* target object resolution
* variant match
* color/material/count match

### Spatial scorer

Checks:

* relation correctness
* reference object correctness
* exact or bounded offset correctness
* symmetry/layout spec correctness

### Multi-turn state scorer

Checks:

* referent continuity
* correct mutation of prior state
* unintended changes

### Ambiguity scorer

Checks:

* whether the model should have asked for clarification
* whether it fabricated specifics
* whether uncertainty fields are used properly

### Robustness scorer

Run grouped paraphrase items and compute consistency metrics.

## 20. Reports and outputs

Every run should produce:

### Per-task artifacts

* raw prompt
* raw model output
* parsed output
* validation status
* score breakdown
* error messages
* latency
* tokens
* cost estimate

### Aggregate artifacts

* overall score
* score by category
* score by difficulty
* score by response type
* schema failure rate
* ambiguity-handling accuracy
* paraphrase consistency rate
* per-model leaderboard

### Human-inspection UI

Provide a simple HTML report showing:

* task
* expected vs actual
* diff view
* score breakdown
* model metadata

That kind of per-instance transparency is directly aligned with HELM’s inspection-first approach. ([GitHub][1])

## 21. Dataset creation plan

Build v1 with around 300 to 800 tasks, not thousands.

Recommended breakdown:

* 80 single-turn creation
* 80 spatial placement
* 60 editing/replacement
* 60 multi-turn state tracking
* 40 ambiguity
* 40 impossible/unsupported
* 40 robustness/paraphrase bundles

Use three data sources:

### Synthetic tasks

Programmatically generated from templates and scene catalogs.

### Curated tasks

Handwritten hard cases.

### Adversarial tasks

Designed to trigger schema drift, spatial mistakes, and fake certainty.

Each task should be tagged with:

* category
* difficulty
* expected response type
* required skills
* ambiguity level

## 22. How to generate the tasks

Task generation pipeline:

1. Define scene templates.
2. Define object catalog and allowed relations.
3. Define prompt templates.
4. Sample parameters.
5. Generate gold specs.
6. Run validation checks on generated tasks.
7. Hand-review a subset.

Example template families:

* “Add a {variant} {category} {relation} the {reference}.”
* “Replace the {target} with a {variant} {category}.”
* “Place {count} {category_plural} evenly around the {reference}.”
* “Make the {target} {attribute_change}.”
* “Move the {target} {relation} the {reference}.”

## 23. Multi-turn benchmark mechanics

For multi-turn tasks, the runner should simulate scene state after each gold or model action.

Version 1 can support two evaluation modes:

### Gold-state mode

Each turn is evaluated against the gold-updated state.

Good for clean diagnosis.

### Model-state mode

Each turn is evaluated against the model’s prior actions.

Good for compound failure analysis.

Start with gold-state mode for simplicity and stable scoring.

## 24. Ambiguity policy

You need an explicit benchmark policy for ambiguity.

Define three classes:

### Must-clarify

No valid precise answer exists from provided context.

### May-assume

A bounded assumption is allowed if explicitly marked.

### Must-act

Enough information is present; clarification would be unnecessary.

This policy should be part of each task’s gold spec so scoring is deterministic.

## 25. Safety and refusal policy

Even though this is not a harmful-content benchmark, define refusal semantics carefully.

The model may refuse only when:

* request is unsupported by schema/capability
* request contradicts provided hard constraints
* target cannot be resolved and must not be guessed

The model should not refuse benign tasks just because they are difficult.

## 26. Benchmark governance

Version all of the following:

* task suite
* schemas
* prompts
* scoring rules
* model config
* evaluator version

Store these in the run metadata.

This matters because the value of a benchmark depends on exact reproducibility, which is one of HELM’s core points and a major reason benchmark frameworks keep strict suite definitions. ([GitHub][1])

## 27. Suggested implementation stack

For Codex, I would recommend:

* **Python** for the benchmark runner and scoring
* **Pydantic** or dataclasses plus JSON Schema for typed validation
* **pytest** for scorer and dataset tests
* **Typer** or argparse for CLI
* **Jinja** or simple templates for prompt assembly
* **SQLite or JSONL** for run storage in v1
* **HTML report generator** for inspection
* optional later: FastAPI dashboard

Python is the most natural fit because the major public eval frameworks in this space are Python-first, including HELM, LiveBench, and OpenAI Evals. ([GitHub][1])

## 28. CLI design

Suggested commands:

* `bench validate-dataset`
* `bench run --suite v1_core --model openai:gpt-5`
* `bench score --run outputs/runs/run_001`
* `bench report --run outputs/runs/run_001`
* `bench compare --runs run_001 run_002`

This makes the system feel like a real benchmark product rather than a script bundle.

## 29. Testing strategy

Codex should implement tests before loading many models.

### Unit tests

* schema validation
* task loading
* score calculations
* relation matching
* ambiguity policy handling

### Golden tests

Fixed model outputs against fixed expected scores.

### Regression tests

Make sure scorer changes do not silently move historical results.

### Fuzz tests

Malformed JSON, unknown enum values, duplicated keys, partial outputs.

## 30. Metrics to publish

For each model, publish:

* overall score
* valid JSON rate
* schema pass rate
* action accuracy
* argument accuracy
* spatial accuracy
* multi-turn consistency
* ambiguity correctness
* hallucinated-capability rate
* latency p50 / p95
* average tokens and cost per task

Favor score vectors over a single vanity number. HELM similarly emphasizes multi-metric evaluation rather than one simplistic scalar. ([GitHub][1])

## 31. Failure taxonomy

The benchmark should classify failures into named buckets.

Recommended taxonomy:

* parse failure
* schema failure
* wrong response type
* wrong action family
* wrong target resolution
* wrong spatial relation
* wrong count
* unsupported hallucination
* missing clarification
* unnecessary clarification
* multi-turn state drift
* extra unintended action

This is essential if you want the benchmark to help product design, not just leaderboard ranking.

## 32. Milestone plan

### Milestone 0: Spec freeze

Deliver:

* response schema
* scene schema
* task schema
* ambiguity policy
* scoring rubric

### Milestone 1: Minimal runner

Deliver:

* task loader
* model adapter interface
* schema validator
* raw JSON score
* CLI skeleton

### Milestone 2: Core scoring

Deliver:

* action scorer
* semantic argument scorer
* spatial scorer
* report generator

### Milestone 3: v1 dataset

Deliver:

* 300–500 tasks
* 10–20 scenes
* category coverage
* unit tests and golden tests

### Milestone 4: Multi-turn support

Deliver:

* turn history handling
* gold-state evaluator
* state-tracking scorer

### Milestone 5: Robustness layer

Deliver:

* paraphrase bundles
* ambiguity suite
* adversarial malformed phrasing suite

### Milestone 6: Leaderboard and compare mode

Deliver:

* run comparison report
* category breakdown tables
* historical run storage

## 33. Suggested acceptance criteria for v1

The first usable version should satisfy all of these:

* can run at least 3 model backends through one adapter interface
* supports single-turn and multi-turn tasks
* validates output with strict schemas
* produces per-task and aggregate reports
* has at least 300 high-quality benchmark items
* scores without requiring an LLM judge
* has regression tests for scoring behavior
* stores reproducible run metadata

That last point is important because reproducibility and explicit suite versioning are central strengths of current benchmark frameworks. ([GitHub][1])

## 34. Nice-to-have v2 extensions

After v1, the next useful additions would be:

* asset-catalog grounding with real IDs
* coordinate-frame normalization
* scene graph diff outputs
* executor-in-the-loop validation
* probabilistic scoring for acceptable placement ranges
* multilingual prompts
* benchmark contamination checks and periodic refreshes, inspired by LiveBench’s rolling-update philosophy ([GitHub][2])

## 35. Codex implementation brief

If you want to hand this to Codex as a concrete assignment, the brief should be:

Build a Python benchmark system for evaluating LLM scene-planning outputs. The system must load versioned task and scene files, send prompts to pluggable model adapters, require strict JSON outputs matching a versioned schema, score responses using deterministic rule-based modules, and generate both per-task and aggregate reports. Start with single-turn tasks, then add multi-turn support. Avoid LLM-judge dependencies in v1. Prioritize schema correctness, spatial reasoning, ambiguity handling, and reproducibility.

## 36. Recommended first deliverables for Codex

Ask Codex to produce these first:

1. `response.schema.json`
2. `task.schema.json`
3. `scene.schema.json`
4. Python typed models for all three
5. benchmark runner CLI
6. JSON validation and parsing layer
7. scorer skeleton with modular interfaces
8. 25 seed tasks across 5 categories
9. HTML or Markdown run report
10. tests for parsing and scoring

That sequence keeps the project from drifting into premature dataset expansion or UI work.

## 37. Final recommendation

The best way to make this benchmark useful is to treat it as a **deterministic planning benchmark**, not as a vague “AI creativity test.” Keep the output schema narrow, the scoring objective, the task categories explicit, and the reports deeply inspectable.

That is the most practical path to a benchmark that engineers will trust, product people can learn from, and future 3D generation systems can plug into cleanly.

If you want, I can turn this into a **Codex-ready technical spec** next, with actual JSON schemas, repo files, task examples, and pseudocode for the scorer.

[1]: https://github.com/stanford-crfm/helm?utm_source=chatgpt.com "GitHub - stanford-crfm/helm: Holistic Evaluation of Language Models (HELM) is an open source Python framework created by the Center for Research on Foundation Models (CRFM) at Stanford for holistic, reproducible and transparent evaluation of foundation models, including large language models (LLMs) and multimodal models."
[2]: https://github.com/LiveBench/LiveBench?utm_source=chatgpt.com "GitHub - LiveBench/LiveBench: LiveBench: A Challenging, Contamination-Free LLM Benchmark"

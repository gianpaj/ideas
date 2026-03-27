# Mercury-2 Prompt Optimization Progress

Model: `inception/mercury-2`
Suite: `configs/suites/v1_core_mercury2_opt.yaml`
Target: `mean_total_score = 1.0` (3/3 samples passing)

---

## Baseline — 2026-03-27

**Score:** mean_total_score = 0.0
**Passing samples:** 0/3

### Observed failure patterns

mercury-2 ignores the JSON Schema sent in the second system message and returns its own flat structure:

| Task | Expected top-level fields | Mercury-2 returned |
|------|--------------------------|-------------------|
| add_house_near_lake | `response_type`, `uncertainty`, `clarification` | `clarification_request` (string, not object) |
| add_pine_tree_left_of_cabin | `response_type`, `uncertainty`, `actions[{action_type, ...}]` | `operation`, `object`, `relative_to`, `direction` (flat, non-schema fields) |
| three_red_barrels | `response_type`, `uncertainty`, `actions[...]` | `placements` (non-schema field) |

Root cause: the model reads the natural-language system prompt instead of the JSON Schema. The phrase "return a clarification_request" causes it to use `clarification_request` as a literal field name.

---

# Scene Planning Benchmark

## Codex-ready technical spec

## 1. Goal

Build a deterministic benchmark that evaluates whether an LLM can transform natural-language scene-editing requests into **strict structured JSON plans**.

The benchmark does **not** generate 3D geometry. It evaluates:

* schema compliance
* action selection
* object/category/attribute extraction
* spatial reasoning
* multi-turn state tracking
* ambiguity handling
* robustness across paraphrases

## 2. Implementation constraints

### Must-have

* Python implementation
* strict JSON-only outputs from models
* JSON Schema validation
* deterministic scoring without LLM judges in v1
* pluggable model adapters
* single-turn and multi-turn tasks
* reproducible run artifacts

### Should-have

* HTML report
* CLI
* task and scene registries
* grouped paraphrase evaluation
* golden tests

## 3. Repository layout

```text
scene-planning-bench/
  README.md
  pyproject.toml
  .gitignore

  configs/
    suites/
      v1_core.yaml
    models/
      openai_gpt5.yaml
      anthropic_claude.yaml
      mock_model.yaml

  schemas/
    response.schema.json
    scene.schema.json
    task.schema.json
    scoring-profile.schema.json

  scenes/
    forest_cabin_001.json
    village_square_001.json
    pond_garden_001.json

  tasks/
    v1_core/
      single_turn/
        spatial.left_of.cabin.tree.001.json
        create.red_chair.001.json
      multi_turn/
        bench_rotation_chain.001.json
      ambiguity/
        put_it_over_there.001.json
      constraints/
        torches_around_altar.001.json
      unsupported/
        liquid_glass_dragon.001.json
      paraphrase_sets/
        add_pine_tree_left_of_cabin.set.json

  src/
    bench/
      __init__.py
      cli.py
      runner.py
      registry.py
      types.py
      prompts.py
      state.py
      serialization.py

      adapters/
        __init__.py
        base.py
        openai_adapter.py
        anthropic_adapter.py
        mock_adapter.py

      validation/
        __init__.py
        json_parse.py
        schema_validate.py

      scoring/
        __init__.py
        aggregate.py
        schema_score.py
        action_score.py
        argument_score.py
        spatial_score.py
        ambiguity_score.py
        state_score.py
        robustness_score.py
        failure_taxonomy.py

      reports/
        __init__.py
        json_report.py
        html_report.py
        compare_report.py

      utils/
        __init__.py
        io.py
        clocks.py
        hashing.py
        diff.py
        ids.py

  tests/
    test_schema_validation.py
    test_task_loading.py
    test_scene_loading.py
    test_schema_score.py
    test_action_score.py
    test_spatial_score.py
    test_state_score.py
    test_ambiguity_score.py
    test_runner_smoke.py
    fixtures/
      sample_valid_response.json
      sample_invalid_response.json
      sample_scene.json
      sample_task.json

  outputs/
    .gitkeep
```

---

## 4. Data model overview

There are 4 primary artifact types:

1. **scene**
2. **task**
3. **response**
4. **scoring profile**

### 4.1 Scene

Defines the scene state and allowed catalog.

### 4.2 Task

Defines prompt turns, target response mode, gold spec, and scoring profile.

### 4.3 Response

The model output under evaluation.

### 4.4 Scoring profile

Weights and hard-fail conditions.

---

## 5. Core protocol

Every model response must be valid against `response.schema.json`.

Top-level allowed response types:

* `scene_actions`
* `scene_patch`
* `clarification_request`
* `refusal`

For v1, support all four in schema, but benchmark tasks can require only a subset.

---

## 6. JSON Schemas

## 6.1 `schemas/response.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/response.schema.json",
  "title": "Scene Planning Response",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "response_type", "uncertainty"],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "1.0"
    },
    "response_type": {
      "type": "string",
      "enum": [
        "scene_actions",
        "scene_patch",
        "clarification_request",
        "refusal"
      ]
    },
    "actions": {
      "type": "array",
      "items": { "$ref": "#/$defs/action" }
    },
    "patch": {
      "$ref": "#/$defs/scenePatch"
    },
    "clarification": {
      "$ref": "#/$defs/clarification"
    },
    "refusal": {
      "$ref": "#/$defs/refusal"
    },
    "notes": {
      "type": ["string", "null"],
      "maxLength": 1000
    },
    "uncertainty": {
      "$ref": "#/$defs/uncertainty"
    }
  },
  "allOf": [
    {
      "if": {
        "properties": { "response_type": { "const": "scene_actions" } },
        "required": ["response_type"]
      },
      "then": {
        "required": ["actions"],
        "properties": {
          "patch": false,
          "clarification": false,
          "refusal": false
        }
      }
    },
    {
      "if": {
        "properties": { "response_type": { "const": "scene_patch" } },
        "required": ["response_type"]
      },
      "then": {
        "required": ["patch"],
        "properties": {
          "actions": false,
          "clarification": false,
          "refusal": false
        }
      }
    },
    {
      "if": {
        "properties": { "response_type": { "const": "clarification_request" } },
        "required": ["response_type"]
      },
      "then": {
        "required": ["clarification"],
        "properties": {
          "actions": false,
          "patch": false,
          "refusal": false
        }
      }
    },
    {
      "if": {
        "properties": { "response_type": { "const": "refusal" } },
        "required": ["response_type"]
      },
      "then": {
        "required": ["refusal"],
        "properties": {
          "actions": false,
          "patch": false,
          "clarification": false
        }
      }
    }
  ],
  "$defs": {
    "uncertainty": {
      "type": "object",
      "additionalProperties": false,
      "required": ["has_ambiguity", "fields"],
      "properties": {
        "has_ambiguity": { "type": "boolean" },
        "fields": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "clarification": {
      "type": "object",
      "additionalProperties": false,
      "required": ["question", "missing_fields"],
      "properties": {
        "question": { "type": "string", "minLength": 1, "maxLength": 500 },
        "missing_fields": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "refusal": {
      "type": "object",
      "additionalProperties": false,
      "required": ["reason_code", "message"],
      "properties": {
        "reason_code": {
          "type": "string",
          "enum": [
            "unsupported_capability",
            "unknown_target",
            "contradictory_constraints",
            "out_of_catalog",
            "insufficient_context"
          ]
        },
        "message": { "type": "string", "minLength": 1, "maxLength": 500 }
      }
    },
    "scenePatch": {
      "type": "object",
      "additionalProperties": false,
      "required": ["operations"],
      "properties": {
        "operations": {
          "type": "array",
          "items": { "$ref": "#/$defs/patchOp" }
        }
      }
    },
    "patchOp": {
      "type": "object",
      "additionalProperties": false,
      "required": ["op", "path"],
      "properties": {
        "op": {
          "type": "string",
          "enum": ["add", "remove", "replace"]
        },
        "path": { "type": "string", "minLength": 1 },
        "value": {}
      }
    },
    "action": {
      "type": "object",
      "additionalProperties": false,
      "required": ["action_type", "confidence"],
      "properties": {
        "action_type": {
          "type": "string",
          "enum": [
            "add_object",
            "remove_object",
            "move_object",
            "rotate_object",
            "scale_object",
            "set_material",
            "set_color",
            "duplicate_object",
            "group_objects",
            "ungroup_objects",
            "replace_object",
            "set_relation",
            "clear_area",
            "spawn_layout",
            "annotate_constraint"
          ]
        },
        "target": { "$ref": "#/$defs/targetRef" },
        "object_spec": { "$ref": "#/$defs/objectSpec" },
        "transform": { "$ref": "#/$defs/transformSpec" },
        "attributes": { "$ref": "#/$defs/attributesSpec" },
        "relations": {
          "type": "array",
          "items": { "$ref": "#/$defs/relationSpec" }
        },
        "constraints": { "$ref": "#/$defs/constraintsSpec" },
        "layout": { "$ref": "#/$defs/layoutSpec" },
        "confidence": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        }
      }
    },
    "targetRef": {
      "type": "object",
      "additionalProperties": false,
      "required": ["selector_type", "value"],
      "properties": {
        "selector_type": {
          "type": "string",
          "enum": ["object_id", "tag", "category", "coreference"]
        },
        "value": { "type": "string", "minLength": 1 }
      }
    },
    "objectSpec": {
      "type": "object",
      "additionalProperties": false,
      "required": ["category"],
      "properties": {
        "category": { "type": "string", "minLength": 1 },
        "asset_id": { "type": ["string", "null"] },
        "variant": { "type": ["string", "null"] },
        "style": { "type": ["string", "null"] },
        "tags": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "transformSpec": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "position": { "$ref": "#/$defs/positionSpec" },
        "rotation": { "$ref": "#/$defs/rotationSpec" },
        "scale": { "$ref": "#/$defs/scaleSpec" }
      }
    },
    "positionSpec": {
      "oneOf": [
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["mode", "coordinates"],
          "properties": {
            "mode": { "const": "absolute" },
            "coordinates": {
              "type": "array",
              "prefixItems": [
                { "type": "number" },
                { "type": "number" },
                { "type": "number" }
              ],
              "items": false
            }
          }
        },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["mode", "reference_object", "relation"],
          "properties": {
            "mode": { "const": "relative" },
            "reference_object": { "type": "string", "minLength": 1 },
            "relation": {
              "type": "string",
              "enum": [
                "left_of",
                "right_of",
                "in_front_of",
                "behind",
                "on_top_of",
                "under",
                "inside",
                "near",
                "around",
                "center_of"
              ]
            },
            "offset_meters": { "type": ["number", "null"] }
          }
        }
      ]
    },
    "rotationSpec": {
      "type": "object",
      "additionalProperties": false,
      "required": ["euler_degrees"],
      "properties": {
        "euler_degrees": {
          "type": "array",
          "prefixItems": [
            { "type": "number" },
            { "type": "number" },
            { "type": "number" }
          ],
          "items": false
        }
      }
    },
    "scaleSpec": {
      "oneOf": [
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["uniform"],
          "properties": {
            "uniform": { "type": "number", "exclusiveMinimum": 0 }
          }
        },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["xyz"],
          "properties": {
            "xyz": {
              "type": "array",
              "prefixItems": [
                { "type": "number", "exclusiveMinimum": 0 },
                { "type": "number", "exclusiveMinimum": 0 },
                { "type": "number", "exclusiveMinimum": 0 }
              ],
              "items": false
            }
          }
        }
      ]
    },
    "attributesSpec": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "color": { "type": ["string", "null"] },
        "material": { "type": ["string", "null"] },
        "count": { "type": ["integer", "null"], "minimum": 1 },
        "size": { "type": ["string", "null"] }
      }
    },
    "relationSpec": {
      "type": "object",
      "additionalProperties": false,
      "required": ["reference_object", "relation"],
      "properties": {
        "reference_object": { "type": "string", "minLength": 1 },
        "relation": {
          "type": "string",
          "enum": [
            "left_of",
            "right_of",
            "in_front_of",
            "behind",
            "on_top_of",
            "under",
            "inside",
            "near",
            "around",
            "facing"
          ]
        }
      }
    },
    "constraintsSpec": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "grounded": { "type": "boolean" },
        "non_overlapping": { "type": "boolean" },
        "keep_path_clear": { "type": "boolean" },
        "preserve_existing_objects": { "type": "boolean" }
      }
    },
    "layoutSpec": {
      "type": "object",
      "additionalProperties": false,
      "required": ["layout_type"],
      "properties": {
        "layout_type": {
          "type": "string",
          "enum": ["line", "circle", "triangle", "grid", "ring", "arc"]
        },
        "count": { "type": "integer", "minimum": 1 },
        "reference_object": { "type": ["string", "null"] },
        "radius_meters": { "type": ["number", "null"], "exclusiveMinimum": 0 }
      }
    }
  }
}
```

---

## 6.2 `schemas/scene.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/scene.schema.json",
  "title": "Scene Definition",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "scene_id",
    "coordinate_system",
    "objects",
    "regions",
    "allowed_categories",
    "allowed_actions"
  ],
  "properties": {
    "scene_id": { "type": "string", "minLength": 1 },
    "coordinate_system": {
      "type": "object",
      "additionalProperties": false,
      "required": ["up_axis", "forward_axis", "units"],
      "properties": {
        "up_axis": { "type": "string", "enum": ["x", "y", "z"] },
        "forward_axis": { "type": "string", "enum": ["x", "y", "z", "-x", "-y", "-z"] },
        "units": { "type": "string", "enum": ["meters"] }
      }
    },
    "objects": {
      "type": "array",
      "items": { "$ref": "#/$defs/objectInstance" }
    },
    "regions": {
      "type": "array",
      "items": { "$ref": "#/$defs/region" }
    },
    "allowed_categories": {
      "type": "array",
      "items": { "type": "string" },
      "uniqueItems": true
    },
    "allowed_actions": {
      "type": "array",
      "items": { "type": "string" },
      "uniqueItems": true
    }
  },
  "$defs": {
    "vec3": {
      "type": "array",
      "prefixItems": [
        { "type": "number" },
        { "type": "number" },
        { "type": "number" }
      ],
      "items": false
    },
    "objectInstance": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "category", "position", "rotation", "bounds", "tags"],
      "properties": {
        "id": { "type": "string", "minLength": 1 },
        "category": { "type": "string", "minLength": 1 },
        "variant": { "type": ["string", "null"] },
        "position": { "$ref": "#/$defs/vec3" },
        "rotation": { "$ref": "#/$defs/vec3" },
        "bounds": { "$ref": "#/$defs/vec3" },
        "tags": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "region": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "type", "bounds"],
      "properties": {
        "id": { "type": "string", "minLength": 1 },
        "type": { "type": "string", "minLength": 1 },
        "bounds": {
          "type": "object",
          "additionalProperties": false,
          "required": ["center", "size"],
          "properties": {
            "center": { "$ref": "#/$defs/vec3" },
            "size": { "$ref": "#/$defs/vec3" }
          }
        },
        "blocked": { "type": "boolean" }
      }
    }
  }
}
```

---

## 6.3 `schemas/task.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/task.schema.json",
  "title": "Benchmark Task",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "task_id",
    "suite",
    "category",
    "difficulty",
    "scene_id",
    "turns",
    "expected_response_type",
    "gold_mode",
    "gold_spec",
    "scoring_profile",
    "metadata"
  ],
  "properties": {
    "task_id": { "type": "string", "minLength": 1 },
    "suite": { "type": "string", "minLength": 1 },
    "category": {
      "type": "string",
      "enum": [
        "object_creation",
        "attribute_control",
        "spatial_placement",
        "count_layout",
        "editing",
        "replacement",
        "constraints",
        "ambiguity",
        "multi_turn",
        "unsupported",
        "paraphrase"
      ]
    },
    "difficulty": {
      "type": "string",
      "enum": ["easy", "medium", "hard"]
    },
    "scene_id": { "type": "string", "minLength": 1 },
    "turns": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/turn" }
    },
    "expected_response_type": {
      "type": "string",
      "enum": [
        "scene_actions",
        "scene_patch",
        "clarification_request",
        "refusal"
      ]
    },
    "gold_mode": {
      "type": "string",
      "enum": ["exact", "flexible", "rule_based"]
    },
    "gold_spec": { "$ref": "#/$defs/goldSpec" },
    "scoring_profile": { "type": "string", "minLength": 1 },
    "metadata": {
      "type": "object",
      "additionalProperties": false,
      "required": ["source", "tags"],
      "properties": {
        "source": { "type": "string" },
        "tags": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    }
  },
  "$defs": {
    "turn": {
      "type": "object",
      "additionalProperties": false,
      "required": ["role", "content"],
      "properties": {
        "role": {
          "type": "string",
          "enum": ["user", "assistant", "system"]
        },
        "content": { "type": "string", "minLength": 1 }
      }
    },
    "goldSpec": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "accepted_action_types": {
          "type": "array",
          "items": { "type": "string" }
        },
        "required_category": { "type": ["string", "null"] },
        "variant_any_of": {
          "type": "array",
          "items": { "type": "string" }
        },
        "required_target": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "selector_type": { "type": "string" },
            "value": { "type": "string" }
          }
        },
        "required_relation": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "reference_object": { "type": "string" },
            "relation": { "type": "string" }
          }
        },
        "required_attributes": {
          "type": "object",
          "additionalProperties": true
        },
        "required_constraints": {
          "type": "object",
          "additionalProperties": true
        },
        "must_clarify": { "type": "boolean" },
        "allowed_reason_codes": {
          "type": "array",
          "items": { "type": "string" }
        },
        "count_range": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "min": { "type": "integer" },
            "max": { "type": "integer" }
          }
        },
        "layout_requirements": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "layout_type": { "type": "string" },
            "reference_object": { "type": ["string", "null"] }
          }
        }
      }
    }
  }
}
```

---

## 6.4 `schemas/scoring-profile.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/scoring-profile.schema.json",
  "title": "Scoring Profile",
  "type": "object",
  "additionalProperties": false,
  "required": ["profile_name", "weights", "hard_fail_conditions"],
  "properties": {
    "profile_name": { "type": "string" },
    "weights": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "schema_validity",
        "action_correctness",
        "argument_correctness",
        "spatial_correctness",
        "state_or_ambiguity",
        "operational"
      ],
      "properties": {
        "schema_validity": { "type": "number", "minimum": 0 },
        "action_correctness": { "type": "number", "minimum": 0 },
        "argument_correctness": { "type": "number", "minimum": 0 },
        "spatial_correctness": { "type": "number", "minimum": 0 },
        "state_or_ambiguity": { "type": "number", "minimum": 0 },
        "operational": { "type": "number", "minimum": 0 }
      }
    },
    "hard_fail_conditions": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "invalid_json",
          "schema_invalid",
          "unsupported_response_type",
          "disallowed_category",
          "disallowed_action",
          "hallucinated_target"
        ]
      }
    }
  }
}
```

---

## 7. Example scene files

## 7.1 `scenes/forest_cabin_001.json`

```json
{
  "scene_id": "forest_cabin_001",
  "coordinate_system": {
    "up_axis": "y",
    "forward_axis": "z",
    "units": "meters"
  },
  "objects": [
    {
      "id": "cabin_1",
      "category": "cabin",
      "variant": "wood",
      "position": [0, 0, 0],
      "rotation": [0, 0, 0],
      "bounds": [4, 3, 4],
      "tags": ["building", "wood"]
    },
    {
      "id": "oak_1",
      "category": "tree",
      "variant": "oak",
      "position": [8, 0, 1],
      "rotation": [0, 15, 0],
      "bounds": [2, 6, 2],
      "tags": ["nature"]
    },
    {
      "id": "campfire_1",
      "category": "campfire",
      "variant": null,
      "position": [6, 0, -2],
      "rotation": [0, 0, 0],
      "bounds": [1, 0.5, 1],
      "tags": ["fire", "centerpiece"]
    }
  ],
  "regions": [
    {
      "id": "path_main",
      "type": "walkway",
      "bounds": {
        "center": [2, 0, 4],
        "size": [2, 0.1, 10]
      },
      "blocked": false
    }
  ],
  "allowed_categories": [
    "tree",
    "rock",
    "barrel",
    "bench",
    "campfire",
    "cabin",
    "torch",
    "chair"
  ],
  "allowed_actions": [
    "add_object",
    "remove_object",
    "move_object",
    "rotate_object",
    "scale_object",
    "set_material",
    "set_color",
    "duplicate_object",
    "replace_object",
    "spawn_layout",
    "annotate_constraint"
  ]
}
```

---

## 8. Example task files

## 8.1 Single-turn spatial task

### `tasks/v1_core/single_turn/spatial.left_of.cabin.tree.001.json`

```json
{
  "task_id": "spatial.left_of.cabin.tree.001",
  "suite": "v1_core",
  "category": "spatial_placement",
  "difficulty": "easy",
  "scene_id": "forest_cabin_001",
  "turns": [
    {
      "role": "user",
      "content": "Add a pine tree to the left of the cabin."
    }
  ],
  "expected_response_type": "scene_actions",
  "gold_mode": "flexible",
  "gold_spec": {
    "accepted_action_types": ["add_object"],
    "required_category": "tree",
    "variant_any_of": ["pine", "fir"],
    "required_relation": {
      "reference_object": "cabin_1",
      "relation": "left_of"
    },
    "required_constraints": {
      "grounded": true
    },
    "count_range": {
      "min": 1,
      "max": 1
    }
  },
  "scoring_profile": "default_spatial",
  "metadata": {
    "source": "synthetic",
    "tags": ["single_turn", "spatial", "relative_position"]
  }
}
```

### One valid model answer

```json
{
  "schema_version": "1.0",
  "response_type": "scene_actions",
  "actions": [
    {
      "action_type": "add_object",
      "object_spec": {
        "category": "tree",
        "asset_id": null,
        "variant": "pine",
        "style": null,
        "tags": []
      },
      "transform": {
        "position": {
          "mode": "relative",
          "reference_object": "cabin_1",
          "relation": "left_of",
          "offset_meters": 3
        }
      },
      "attributes": {
        "color": null,
        "material": null,
        "count": 1,
        "size": null
      },
      "constraints": {
        "grounded": true,
        "non_overlapping": true,
        "keep_path_clear": false,
        "preserve_existing_objects": true
      },
      "confidence": 0.96
    }
  ],
  "notes": null,
  "uncertainty": {
    "has_ambiguity": false,
    "fields": []
  }
}
```

---

## 8.2 Constraint/layout task

### `tasks/v1_core/constraints/torches_around_altar.001.json`

```json
{
  "task_id": "torches.around.altar.001",
  "suite": "v1_core",
  "category": "count_layout",
  "difficulty": "medium",
  "scene_id": "village_square_001",
  "turns": [
    {
      "role": "user",
      "content": "Put three torches evenly around the altar."
    }
  ],
  "expected_response_type": "scene_actions",
  "gold_mode": "rule_based",
  "gold_spec": {
    "accepted_action_types": ["spawn_layout", "add_object"],
    "required_category": "torch",
    "required_relation": {
      "reference_object": "altar_1",
      "relation": "around"
    },
    "count_range": {
      "min": 3,
      "max": 3
    },
    "layout_requirements": {
      "layout_type": "triangle",
      "reference_object": "altar_1"
    }
  },
  "scoring_profile": "default_layout",
  "metadata": {
    "source": "curated",
    "tags": ["layout", "count", "constraint"]
  }
}
```

---

## 8.3 Ambiguity task

### `tasks/v1_core/ambiguity/put_it_over_there.001.json`

```json
{
  "task_id": "ambiguity.put_it_over_there.001",
  "suite": "v1_core",
  "category": "ambiguity",
  "difficulty": "easy",
  "scene_id": "pond_garden_001",
  "turns": [
    {
      "role": "user",
      "content": "Put it over there."
    }
  ],
  "expected_response_type": "clarification_request",
  "gold_mode": "exact",
  "gold_spec": {
    "must_clarify": true
  },
  "scoring_profile": "default_ambiguity",
  "metadata": {
    "source": "curated",
    "tags": ["ambiguity", "coreference", "underspecified"]
  }
}
```

### One valid model answer

```json
{
  "schema_version": "1.0",
  "response_type": "clarification_request",
  "clarification": {
    "question": "Which object should be moved, and where should it be placed?",
    "missing_fields": ["target", "destination"]
  },
  "notes": null,
  "uncertainty": {
    "has_ambiguity": true,
    "fields": ["target", "destination"]
  }
}
```

---

## 8.4 Unsupported task

### `tasks/v1_core/unsupported/liquid_glass_dragon.001.json`

```json
{
  "task_id": "unsupported.liquid_glass_dragon.001",
  "suite": "v1_core",
  "category": "unsupported",
  "difficulty": "medium",
  "scene_id": "forest_cabin_001",
  "turns": [
    {
      "role": "user",
      "content": "Add a dragon made of liquid glass using a non-catalog asset."
    }
  ],
  "expected_response_type": "refusal",
  "gold_mode": "flexible",
  "gold_spec": {
    "allowed_reason_codes": [
      "out_of_catalog",
      "unsupported_capability"
    ]
  },
  "scoring_profile": "default_unsupported",
  "metadata": {
    "source": "curated",
    "tags": ["unsupported", "catalog"]
  }
}
```

---

## 8.5 Multi-turn task

### `tasks/v1_core/multi_turn/bench_rotation_chain.001.json`

```json
{
  "task_id": "multi_turn.bench_rotation_chain.001",
  "suite": "v1_core",
  "category": "multi_turn",
  "difficulty": "medium",
  "scene_id": "pond_garden_001",
  "turns": [
    {
      "role": "user",
      "content": "Add a bench near the pond."
    },
    {
      "role": "assistant",
      "content": "{\"schema_version\":\"1.0\",\"response_type\":\"scene_actions\",\"actions\":[{\"action_type\":\"add_object\",\"object_spec\":{\"category\":\"bench\",\"asset_id\":null,\"variant\":null,\"style\":null,\"tags\":[]},\"transform\":{\"position\":{\"mode\":\"relative\",\"reference_object\":\"pond_1\",\"relation\":\"near\",\"offset_meters\":2}},\"attributes\":{\"color\":null,\"material\":null,\"count\":1,\"size\":null},\"constraints\":{\"grounded\":true,\"non_overlapping\":true,\"keep_path_clear\":false,\"preserve_existing_objects\":true},\"confidence\":0.93}],\"notes\":null,\"uncertainty\":{\"has_ambiguity\":false,\"fields\":[]}}"
    },
    {
      "role": "user",
      "content": "Now rotate it 90 degrees."
    }
  ],
  "expected_response_type": "scene_actions",
  "gold_mode": "rule_based",
  "gold_spec": {
    "accepted_action_types": ["rotate_object"],
    "required_target": {
      "selector_type": "coreference",
      "value": "it"
    },
    "required_attributes": {
      "rotation_delta_degrees": 90
    }
  },
  "scoring_profile": "default_multi_turn",
  "metadata": {
    "source": "curated",
    "tags": ["multi_turn", "coreference", "editing"]
  }
}
```

---

## 9. Suite config

## 9.1 `configs/suites/v1_core.yaml`

```yaml
suite_name: v1_core
description: Core scene planning benchmark v1
task_roots:
  - tasks/v1_core/single_turn
  - tasks/v1_core/multi_turn
  - tasks/v1_core/ambiguity
  - tasks/v1_core/constraints
  - tasks/v1_core/unsupported
defaults:
  system_prompt: |
    You are a scene-planning assistant.
    Output JSON only.
    Use schema_version 1.0.
    Do not invent unsupported categories or actions.
    If the request is ambiguous, return a clarification_request.
    If the request is impossible or unsupported, return a refusal.
  response_schema_path: schemas/response.schema.json
  scene_schema_path: schemas/scene.schema.json
  task_schema_path: schemas/task.schema.json
scoring_profiles:
  default_spatial:
    weights:
      schema_validity: 0.20
      action_correctness: 0.20
      argument_correctness: 0.20
      spatial_correctness: 0.25
      state_or_ambiguity: 0.10
      operational: 0.05
    hard_fail_conditions:
      - invalid_json
      - schema_invalid
      - disallowed_category
      - disallowed_action
  default_layout:
    weights:
      schema_validity: 0.20
      action_correctness: 0.20
      argument_correctness: 0.20
      spatial_correctness: 0.25
      state_or_ambiguity: 0.10
      operational: 0.05
    hard_fail_conditions:
      - invalid_json
      - schema_invalid
  default_ambiguity:
    weights:
      schema_validity: 0.25
      action_correctness: 0.20
      argument_correctness: 0.10
      spatial_correctness: 0.00
      state_or_ambiguity: 0.40
      operational: 0.05
    hard_fail_conditions:
      - invalid_json
      - schema_invalid
      - unsupported_response_type
  default_unsupported:
    weights:
      schema_validity: 0.25
      action_correctness: 0.25
      argument_correctness: 0.10
      spatial_correctness: 0.00
      state_or_ambiguity: 0.35
      operational: 0.05
    hard_fail_conditions:
      - invalid_json
      - schema_invalid
  default_multi_turn:
    weights:
      schema_validity: 0.20
      action_correctness: 0.20
      argument_correctness: 0.20
      spatial_correctness: 0.10
      state_or_ambiguity: 0.25
      operational: 0.05
    hard_fail_conditions:
      - invalid_json
      - schema_invalid
```

---

## 10. Python typed models

## 10.1 `src/bench/types.py`

```python
from __future__ import annotations

from typing import Literal, Optional, Any
from pydantic import BaseModel, Field


ResponseType = Literal[
    "scene_actions",
    "scene_patch",
    "clarification_request",
    "refusal",
]


class Uncertainty(BaseModel):
    has_ambiguity: bool
    fields: list[str]


class TargetRef(BaseModel):
    selector_type: Literal["object_id", "tag", "category", "coreference"]
    value: str


class ObjectSpec(BaseModel):
    category: str
    asset_id: Optional[str] = None
    variant: Optional[str] = None
    style: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class PositionAbsolute(BaseModel):
    mode: Literal["absolute"]
    coordinates: tuple[float, float, float]


class PositionRelative(BaseModel):
    mode: Literal["relative"]
    reference_object: str
    relation: Literal[
        "left_of",
        "right_of",
        "in_front_of",
        "behind",
        "on_top_of",
        "under",
        "inside",
        "near",
        "around",
        "center_of",
    ]
    offset_meters: Optional[float] = None


PositionSpec = PositionAbsolute | PositionRelative


class RotationSpec(BaseModel):
    euler_degrees: tuple[float, float, float]


class ScaleUniform(BaseModel):
    uniform: float


class ScaleXYZ(BaseModel):
    xyz: tuple[float, float, float]


ScaleSpec = ScaleUniform | ScaleXYZ


class TransformSpec(BaseModel):
    position: Optional[PositionSpec] = None
    rotation: Optional[RotationSpec] = None
    scale: Optional[ScaleSpec] = None


class AttributesSpec(BaseModel):
    color: Optional[str] = None
    material: Optional[str] = None
    count: Optional[int] = None
    size: Optional[str] = None


class RelationSpec(BaseModel):
    reference_object: str
    relation: str


class ConstraintsSpec(BaseModel):
    grounded: Optional[bool] = None
    non_overlapping: Optional[bool] = None
    keep_path_clear: Optional[bool] = None
    preserve_existing_objects: Optional[bool] = None


class LayoutSpec(BaseModel):
    layout_type: Literal["line", "circle", "triangle", "grid", "ring", "arc"]
    count: Optional[int] = None
    reference_object: Optional[str] = None
    radius_meters: Optional[float] = None


class Action(BaseModel):
    action_type: Literal[
        "add_object",
        "remove_object",
        "move_object",
        "rotate_object",
        "scale_object",
        "set_material",
        "set_color",
        "duplicate_object",
        "group_objects",
        "ungroup_objects",
        "replace_object",
        "set_relation",
        "clear_area",
        "spawn_layout",
        "annotate_constraint",
    ]
    target: Optional[TargetRef] = None
    object_spec: Optional[ObjectSpec] = None
    transform: Optional[TransformSpec] = None
    attributes: Optional[AttributesSpec] = None
    relations: Optional[list[RelationSpec]] = None
    constraints: Optional[ConstraintsSpec] = None
    layout: Optional[LayoutSpec] = None
    confidence: float


class Clarification(BaseModel):
    question: str
    missing_fields: list[str]


class Refusal(BaseModel):
    reason_code: Literal[
        "unsupported_capability",
        "unknown_target",
        "contradictory_constraints",
        "out_of_catalog",
        "insufficient_context",
    ]
    message: str


class PatchOp(BaseModel):
    op: Literal["add", "remove", "replace"]
    path: str
    value: Any | None = None


class ScenePatch(BaseModel):
    operations: list[PatchOp]


class Response(BaseModel):
    schema_version: Literal["1.0"]
    response_type: ResponseType
    actions: Optional[list[Action]] = None
    patch: Optional[ScenePatch] = None
    clarification: Optional[Clarification] = None
    refusal: Optional[Refusal] = None
    notes: Optional[str] = None
    uncertainty: Uncertainty
```

---

## 11. Runner flow

## 11.1 End-to-end execution sequence

1. load suite config
2. load schemas
3. load scenes
4. load tasks
5. validate task and scene files
6. assemble model input
7. call adapter
8. parse raw model output
9. validate against response schema
10. score by profile
11. persist artifacts
12. render reports

---

## 12. Prompt assembly

## 12.1 `src/bench/prompts.py`

```python
from __future__ import annotations

import json
from pathlib import Path


def build_prompt_bundle(system_prompt: str, scene: dict, task: dict, response_schema: dict) -> list[dict]:
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {
            "role": "system",
            "content": (
                "Scene context JSON:\n"
                + json.dumps(scene, indent=2)
                + "\n\n"
                + "Response schema JSON Schema:\n"
                + json.dumps(response_schema, indent=2)
                + "\n\n"
                + "Return only a JSON object that conforms to the schema."
            ),
        },
    ]
    messages.extend(task["turns"])
    return messages
```

---

## 13. Model adapter interface

## 13.1 `src/bench/adapters/base.py`

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ModelResult:
    raw_text: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    model_name: str | None = None


class BaseAdapter(ABC):
    @abstractmethod
    def generate(self, messages: list[dict], config: dict) -> ModelResult:
        raise NotImplementedError
```

## 13.2 `src/bench/adapters/mock_adapter.py`

```python
from __future__ import annotations

import time
from .base import BaseAdapter, ModelResult


class MockAdapter(BaseAdapter):
    def generate(self, messages: list[dict], config: dict) -> ModelResult:
        start = time.perf_counter()
        raw = config.get("mock_response", "{\"schema_version\":\"1.0\",\"response_type\":\"refusal\",\"refusal\":{\"reason_code\":\"unsupported_capability\",\"message\":\"mock\"},\"uncertainty\":{\"has_ambiguity\":false,\"fields\":[]}}")
        latency_ms = int((time.perf_counter() - start) * 1000)
        return ModelResult(raw_text=raw, latency_ms=latency_ms, model_name="mock")
```

---

## 14. Validation layer

## 14.1 `src/bench/validation/json_parse.py`

```python
from __future__ import annotations

import json


class JsonParseError(Exception):
    pass


def parse_json(raw_text: str) -> dict:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise JsonParseError(str(exc)) from exc
```

## 14.2 `src/bench/validation/schema_validate.py`

```python
from __future__ import annotations

from jsonschema import Draft202012Validator


class SchemaValidationError(Exception):
    pass


def validate_instance(instance: dict, schema: dict) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
    if errors:
        message = "; ".join(
            f"path={'/'.join(map(str, err.path)) or '<root>'}: {err.message}"
            for err in errors
        )
        raise SchemaValidationError(message)
```

---

## 15. Scoring design

The scorer is modular. Each scorer returns:

* `score`: float from 0 to 1
* `details`: dict
* `failures`: list[str]

### Scoring modules

* schema
* action
* argument
* spatial
* ambiguity
* state
* robustness
* operational

---

## 16. Failure taxonomy

## 16.1 `src/bench/scoring/failure_taxonomy.py`

```python
FAIL_INVALID_JSON = "invalid_json"
FAIL_SCHEMA_INVALID = "schema_invalid"
FAIL_UNSUPPORTED_RESPONSE_TYPE = "unsupported_response_type"
FAIL_DISALLOWED_CATEGORY = "disallowed_category"
FAIL_DISALLOWED_ACTION = "disallowed_action"
FAIL_HALLUCINATED_TARGET = "hallucinated_target"
FAIL_WRONG_ACTION = "wrong_action"
FAIL_WRONG_RELATION = "wrong_relation"
FAIL_WRONG_CATEGORY = "wrong_category"
FAIL_WRONG_COUNT = "wrong_count"
FAIL_MISSING_CLARIFICATION = "missing_clarification"
FAIL_UNNECESSARY_CLARIFICATION = "unnecessary_clarification"
FAIL_STATE_DRIFT = "state_drift"
```

---

## 17. Scorer pseudocode

## 17.1 Schema scorer pseudocode

```python
def score_schema(raw_text, parsed, response_schema):
    failures = []
    details = {}

    if raw_text is None:
        failures.append("invalid_json")
        return 0.0, details, failures

    try:
        validate_instance(parsed, response_schema)
    except SchemaValidationError as e:
        failures.append("schema_invalid")
        details["error"] = str(e)
        return 0.0, details, failures

    return 1.0, {"valid": True}, failures
```

## 17.2 Action scorer pseudocode

```python
def score_action(task, parsed_response):
    expected = task["expected_response_type"]
    actual = parsed_response["response_type"]

    if actual != expected:
        return 0.0, {"expected": expected, "actual": actual}, ["unsupported_response_type"]

    gold = task["gold_spec"]

    if actual == "scene_actions":
        actions = parsed_response.get("actions", [])
        action_types = [a["action_type"] for a in actions]
        accepted = set(gold.get("accepted_action_types", []))

        if accepted and not any(a in accepted for a in action_types):
            return 0.0, {"accepted": list(accepted), "actual": action_types}, ["wrong_action"]

        return 1.0, {"action_types": action_types}, []

    if actual == "clarification_request":
        must_clarify = gold.get("must_clarify", False)
        return (1.0 if must_clarify else 0.0), {"must_clarify": must_clarify}, ([] if must_clarify else ["unnecessary_clarification"])

    if actual == "refusal":
        allowed_reason_codes = set(gold.get("allowed_reason_codes", []))
        actual_reason = parsed_response["refusal"]["reason_code"]
        ok = (not allowed_reason_codes) or (actual_reason in allowed_reason_codes)
        return (1.0 if ok else 0.0), {"actual_reason": actual_reason}, ([] if ok else ["wrong_action"])

    return 1.0, {}, []
```

## 17.3 Argument scorer pseudocode

```python
def score_arguments(task, parsed_response):
    gold = task["gold_spec"]
    if parsed_response["response_type"] != "scene_actions":
        return 1.0, {}, []

    actions = parsed_response.get("actions", [])
    if not actions:
        return 0.0, {"reason": "no_actions"}, ["wrong_action"]

    best = actions[0]
    score_parts = []
    failures = []
    details = {}

    required_category = gold.get("required_category")
    if required_category is not None:
        actual_category = ((best.get("object_spec") or {}).get("category"))
        ok = actual_category == required_category
        score_parts.append(1.0 if ok else 0.0)
        details["category"] = {"expected": required_category, "actual": actual_category}
        if not ok:
            failures.append("wrong_category")

    variant_any_of = gold.get("variant_any_of", [])
    if variant_any_of:
        actual_variant = ((best.get("object_spec") or {}).get("variant"))
        ok = actual_variant in variant_any_of
        score_parts.append(1.0 if ok else 0.0)
        details["variant"] = {"accepted": variant_any_of, "actual": actual_variant}

    count_range = gold.get("count_range")
    if count_range:
        actual_count = ((best.get("attributes") or {}).get("count"))
        min_count = count_range["min"]
        max_count = count_range["max"]
        ok = actual_count is not None and min_count <= actual_count <= max_count
        score_parts.append(1.0 if ok else 0.0)
        details["count"] = {"expected_range": count_range, "actual": actual_count}
        if not ok:
            failures.append("wrong_count")

    if not score_parts:
        return 1.0, details, failures

    return sum(score_parts) / len(score_parts), details, failures
```

## 17.4 Spatial scorer pseudocode

```python
def score_spatial(task, parsed_response):
    gold = task["gold_spec"]
    required_relation = gold.get("required_relation")
    if not required_relation:
        return 1.0, {}, []

    if parsed_response["response_type"] != "scene_actions":
        return 0.0, {"reason": "not_scene_actions"}, ["wrong_relation"]

    actions = parsed_response.get("actions", [])
    if not actions:
        return 0.0, {"reason": "no_actions"}, ["wrong_relation"]

    action = actions[0]
    position = (((action.get("transform") or {}).get("position")) or {})

    actual_ref = position.get("reference_object")
    actual_relation = position.get("relation")

    ref_ok = actual_ref == required_relation["reference_object"]
    rel_ok = actual_relation == required_relation["relation"]

    score = (float(ref_ok) + float(rel_ok)) / 2.0
    failures = []
    if not rel_ok:
        failures.append("wrong_relation")
    if not ref_ok:
        failures.append("hallucinated_target")

    details = {
        "expected_reference_object": required_relation["reference_object"],
        "actual_reference_object": actual_ref,
        "expected_relation": required_relation["relation"],
        "actual_relation": actual_relation,
    }
    return score, details, failures
```

## 17.5 Ambiguity scorer pseudocode

```python
def score_ambiguity(task, parsed_response):
    gold = task["gold_spec"]
    must_clarify = gold.get("must_clarify", False)

    if must_clarify:
        if parsed_response["response_type"] != "clarification_request":
            return 0.0, {"must_clarify": True}, ["missing_clarification"]
        fields = parsed_response.get("uncertainty", {}).get("fields", [])
        return 1.0, {"uncertainty_fields": fields}, []

    if parsed_response["response_type"] == "clarification_request":
        return 0.0, {"must_clarify": False}, ["unnecessary_clarification"]

    return 1.0, {}, []
```

## 17.6 Aggregate scorer pseudocode

```python
def aggregate_scores(profile, module_scores, module_failures):
    hard_fails = set(profile["hard_fail_conditions"])
    all_failures = [f for group in module_failures.values() for f in group]

    if any(f in hard_fails for f in all_failures):
        return {
            "final_score": 0.0,
            "hard_fail": True,
            "failures": all_failures,
            "weighted_breakdown": module_scores,
        }

    weights = profile["weights"]
    final_score = (
        module_scores["schema_validity"] * weights["schema_validity"] +
        module_scores["action_correctness"] * weights["action_correctness"] +
        module_scores["argument_correctness"] * weights["argument_correctness"] +
        module_scores["spatial_correctness"] * weights["spatial_correctness"] +
        module_scores["state_or_ambiguity"] * weights["state_or_ambiguity"] +
        module_scores["operational"] * weights["operational"]
    )

    return {
        "final_score": final_score,
        "hard_fail": False,
        "failures": all_failures,
        "weighted_breakdown": module_scores,
    }
```

---

## 18. Operational score

Keep v1 simple.

```python
def score_operational(latency_ms: int, output_tokens: int | None) -> float:
    latency_score = 1.0
    if latency_ms > 8000:
        latency_score = 0.2
    elif latency_ms > 4000:
        latency_score = 0.5
    elif latency_ms > 2000:
        latency_score = 0.8

    return latency_score
```

---

## 19. Runner pseudocode

## 19.1 `src/bench/runner.py`

```python
def run_task(task, scene, suite_cfg, adapter, model_cfg, response_schema):
    messages = build_prompt_bundle(
        system_prompt=suite_cfg["defaults"]["system_prompt"],
        scene=scene,
        task=task,
        response_schema=response_schema,
    )

    model_result = adapter.generate(messages, model_cfg)

    raw_text = model_result.raw_text
    parsed = None
    parse_error = None
    schema_error = None

    try:
        parsed = parse_json(raw_text)
    except JsonParseError as e:
        parse_error = str(e)

    module_scores = {
        "schema_validity": 0.0,
        "action_correctness": 0.0,
        "argument_correctness": 0.0,
        "spatial_correctness": 0.0,
        "state_or_ambiguity": 0.0,
        "operational": score_operational(model_result.latency_ms, model_result.output_tokens),
    }
    module_details = {}
    module_failures = {}

    if parsed is None:
        module_failures["schema_validity"] = ["invalid_json"]
        profile = suite_cfg["scoring_profiles"][task["scoring_profile"]]
        aggregate = aggregate_scores(profile, module_scores, module_failures)
        return build_result_record(task, raw_text, parsed, model_result, aggregate, module_details, parse_error=parse_error)

    try:
        validate_instance(parsed, response_schema)
        module_scores["schema_validity"] = 1.0
        module_details["schema_validity"] = {"valid": True}
        module_failures["schema_validity"] = []
    except SchemaValidationError as e:
        schema_error = str(e)
        module_failures["schema_validity"] = ["schema_invalid"]
        profile = suite_cfg["scoring_profiles"][task["scoring_profile"]]
        aggregate = aggregate_scores(profile, module_scores, module_failures)
        return build_result_record(task, raw_text, parsed, model_result, aggregate, module_details, schema_error=schema_error)

    action_score, action_details, action_failures = score_action(task, parsed)
    arg_score, arg_details, arg_failures = score_arguments(task, parsed)
    spatial_score, spatial_details, spatial_failures = score_spatial(task, parsed)

    if task["category"] in {"ambiguity", "unsupported"}:
        state_or_ambiguity_score, soa_details, soa_failures = score_ambiguity(task, parsed)
    else:
        state_or_ambiguity_score, soa_details, soa_failures = score_state(task, parsed, scene)

    module_scores["action_correctness"] = action_score
    module_scores["argument_correctness"] = arg_score
    module_scores["spatial_correctness"] = spatial_score
    module_scores["state_or_ambiguity"] = state_or_ambiguity_score

    module_details["action_correctness"] = action_details
    module_details["argument_correctness"] = arg_details
    module_details["spatial_correctness"] = spatial_details
    module_details["state_or_ambiguity"] = soa_details

    module_failures["action_correctness"] = action_failures
    module_failures["argument_correctness"] = arg_failures
    module_failures["spatial_correctness"] = spatial_failures
    module_failures["state_or_ambiguity"] = soa_failures

    profile = suite_cfg["scoring_profiles"][task["scoring_profile"]]
    aggregate = aggregate_scores(profile, module_scores, module_failures)

    return build_result_record(task, raw_text, parsed, model_result, aggregate, module_details)
```

---

## 20. CLI

## 20.1 `src/bench/cli.py`

```python
import typer

app = typer.Typer()


@app.command()
def validate_dataset():
    """Validate scenes, tasks, and configs against schemas."""
    ...


@app.command()
def run(
    suite: str = typer.Option(...),
    model: str = typer.Option(...),
    output_dir: str = typer.Option("outputs"),
):
    """Run an eval suite."""
    ...


@app.command()
def report(run_path: str = typer.Option(...)):
    """Generate HTML and JSON reports."""
    ...


@app.command()
def compare(run_a: str = typer.Option(...), run_b: str = typer.Option(...)):
    """Compare two runs."""
    ...


if __name__ == "__main__":
    app()
```

---

## 21. Output artifacts

Each run should write:

```text
outputs/runs/2026-03-26T12-00-00Z_v1_core_mock/
  run_manifest.json
  per_task/
    spatial.left_of.cabin.tree.001.json
    ambiguity.put_it_over_there.001.json
  aggregate.json
  report.html
```

### `run_manifest.json`

Include:

* suite version
* model config
* schema hashes
* task count
* git commit if available
* timestamp

---

## 22. Result record shape

```json
{
  "task_id": "spatial.left_of.cabin.tree.001",
  "model_name": "mock",
  "raw_response": "...",
  "parsed_response": {},
  "latency_ms": 42,
  "input_tokens": null,
  "output_tokens": null,
  "aggregate": {
    "final_score": 0.94,
    "hard_fail": false,
    "failures": [],
    "weighted_breakdown": {
      "schema_validity": 1.0,
      "action_correctness": 1.0,
      "argument_correctness": 1.0,
      "spatial_correctness": 1.0,
      "state_or_ambiguity": 0.8,
      "operational": 1.0
    }
  },
  "details": {
    "schema_validity": {"valid": true},
    "action_correctness": {},
    "argument_correctness": {},
    "spatial_correctness": {},
    "state_or_ambiguity": {}
  }
}
```

---

## 23. HTML report requirements

The HTML report should contain:

* overall score
* score by category
* hard fail rate
* valid JSON rate
* schema pass rate
* top failure types
* per-task expandable cards with:

  * prompt turns
  * raw response
  * parsed response
  * score breakdown
  * failures

---

## 24. Test plan

## 24.1 `tests/test_schema_validation.py`

Cases:

* valid response
* invalid enum
* extra unknown property
* missing required field
* bad response-type branch

## 24.2 `tests/test_action_score.py`

Cases:

* correct action type
* wrong action type
* clarification when action expected
* refusal when unsupported expected

## 24.3 `tests/test_spatial_score.py`

Cases:

* correct relation and reference object
* correct relation wrong object
* wrong relation correct object
* absolute coordinates when relative required

## 24.4 `tests/test_ambiguity_score.py`

Cases:

* must-clarify task answered with clarification
* must-clarify task answered with fake action
* clear task answered with clarification

## 24.5 `tests/test_runner_smoke.py`

Runs one mock suite end-to-end.

---

## 25. Pyproject

## 25.1 `pyproject.toml`

```toml
[project]
name = "scene-planning-bench"
version = "0.1.0"
description = "Deterministic benchmark for LLM scene-planning outputs"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.6",
  "jsonschema>=4.21",
  "typer>=0.12",
  "pyyaml>=6.0",
  "jinja2>=3.1"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "ruff>=0.3",
  "mypy>=1.8"
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
```

---

## 26. README skeleton

## 26.1 `README.md`

````md
# Scene Planning Benchmark

A deterministic benchmark for evaluating how well LLMs convert natural-language world-editing instructions into strict structured scene plans.

## Features
- strict JSON-only outputs
- JSON Schema validation
- deterministic scoring
- single-turn and multi-turn tasks
- pluggable model adapters
- HTML reports

## Quick start
```bash
pip install -e .[dev]
python -m bench.cli validate-dataset
python -m bench.cli run --suite v1_core --model mock_model
python -m bench.cli report --run-path outputs/runs/<run_id>
````

## Task categories

* object creation
* spatial placement
* attribute control
* layout/count
* editing
* replacement
* ambiguity
* unsupported
* multi-turn

```

---

## 27. Codex implementation order

This is the order Codex should build:

### Phase 1
- repo skeleton
- `pyproject.toml`
- all JSON schemas
- scene/task fixtures
- schema validation tests

### Phase 2
- typed Python models
- loader/registry
- prompt assembly
- mock adapter
- CLI skeleton

### Phase 3
- parse + schema validation pipeline
- schema scorer
- action scorer
- argument scorer
- spatial scorer
- aggregate scorer

### Phase 4
- runner end-to-end
- JSON output artifacts
- smoke tests

### Phase 5
- ambiguity scorer
- multi-turn state scorer
- HTML reports

### Phase 6
- paraphrase grouping
- compare reports
- real model adapters

---

## 28. Acceptance criteria

Codex is done with v1 when:

- all schemas validate against Draft 2020-12 meta-schema structure
- task and scene files validate
- one suite runs end-to-end with mock adapter
- JSON parse and schema failures are classified correctly
- at least 5 example tasks run successfully
- HTML report renders
- tests pass

Using Draft 2020-12 is appropriate here because it is the current JSON Schema version and supports modern validation patterns such as `prefixItems`, improved tuple handling, and clearer validation vocabulary separation. :contentReference[oaicite:1]{index=1}

---

## 29. Notes for future v2

Not required now, but leave extension points for:
- asset-catalog grounding
- coordinate tolerance bands
- JSON Patch-first tasks
- multilingual prompts
- executor-backed verification
- contamination-resistant rolling refreshes inspired by benchmark frameworks that regularly update task sets.
```

[1]: https://json-schema.org/draft/2020-12 "JSON Schema"

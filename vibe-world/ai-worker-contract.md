# AI Worker Contract

_Drafted: March 24, 2026_

## Purpose

This document defines the boundary between the V1 authoritative multiplayer backend and the external AI worker/service.

The worker exists to:

- interpret player prompts,
- produce constrained object intent,
- turn that intent into validated draft/edit payloads,
- hand those payloads back to the authoritative backend.

The worker does not exist to:

- own multiplayer permissions,
- mutate authoritative state directly without validation,
- define lifecycle rules,
- bypass world settings.

## Design principles

- The worker is advisory and generative, not authoritative.
- The worker should operate on constrained schemas.
- The worker should return structured payloads, not freeform scene dumps.
- The backend should be able to reject any worker output safely.

## High-level flow

1. player submits a create or edit prompt
2. backend records an AI job
3. worker receives the job with current world and object context
4. worker generates `prompt_ir`
5. worker or downstream validator converts `prompt_ir` into `builder_spec`
6. worker submits structured output back to the backend
7. backend validates permissions, lifecycle state, and version
8. backend applies or rejects the result through reducers

## Worker inputs

Suggested job input fields:

- `job_id`
- `job_type`
- `world_id`
- `player_id`
- `target_object_id`
- `source_prompt`
- `world_settings`
- `object_context`
- `base_object_version`

### `job_type`

Allowed V1 values:

- `create`
- `refine`
- `remix`

### `world_settings`

The worker should receive only the settings needed to stay within allowed behavior:

- visibility
- destructive editing flag
- cooldown duration
- protected spawn info if relevant
- object size and complexity caps

### `object_context`

For `refine` and `remix`, the worker should receive:

- current object summary
- current object version
- current builder spec
- relevant attribution summary if needed

The worker does not need the full world state unless placement or context matters.

## Worker outputs

The worker should return:

- `job_id`
- `status`
- `prompt_ir`
- `builder_spec`
- optional `render_spec`
- validation notes or warnings
- error code if failed

### Required output constraints

- `prompt_ir` must match `prompt-ir-spec.md`
- `builder_spec` must be deterministic enough for server-side validation
- `render_spec` must be optional and non-authoritative

## Builder spec expectations

The builder spec should resolve vague IR terms into concrete structure.

Suggested responsibilities:

- exact part list
- exact relative attachment plan
- exact material selection
- exact size resolution within allowed caps
- exact behavior preset assignments

The builder spec should not:

- encode arbitrary scripts
- include unrestricted mesh payloads
- imply permissions the backend did not grant

## Validation pipeline

Before the backend accepts worker output, it should validate:

- job still exists and is active
- object version still matches when editing
- output schema is valid
- shape/material/behavior vocabulary is allowed
- complexity is within limits
- destructive intent is allowed in the current world

## Failure cases

The worker should be able to fail cleanly with codes such as:

- `invalid_prompt`
- `unsupported_request`
- `unsafe_request`
- `context_stale`
- `generation_failed`
- `validation_failed`
- `timeout`

The backend should:

- mark the AI job as failed
- keep live world state unchanged
- surface an understandable error to the player

## Timeout model

V1 should assume AI generation may fail or stall.

Recommended behavior:

- AI jobs get explicit timeout windows
- expired jobs may not write back into live state
- stale worker responses should be rejected if the job is no longer active

## Trusted identity boundary

The worker should write back through a trusted service identity, not by impersonating players directly.

The backend still decides:

- whether the job is valid
- whether the player still has permission
- whether the object version is current
- whether the lifecycle state allows the change

## Suggested request and response shapes

Example request:

```json
{
  "job_id": "job_123",
  "job_type": "create",
  "world_id": "world_1",
  "player_id": "player_7",
  "target_object_id": null,
  "source_prompt": "make a cozy mushroom house with glowing windows",
  "world_settings": {
    "visibility": "public",
    "destructive_edits_enabled": false,
    "object_cooldown_seconds": 30
  },
  "object_context": null,
  "base_object_version": null
}
```

Example response:

```json
{
  "job_id": "job_123",
  "status": "completed",
  "prompt_ir": {
    "ir_version": "v1",
    "operation": "create"
  },
  "builder_spec": {
    "builder_version": "v1"
  },
  "render_spec": null,
  "warnings": []
}
```

## V1 simplifications

To keep the first implementation manageable:

- use one worker contract for create, refine, and remix
- do not split the worker into many microservices
- keep render preview optional
- do not attempt multi-stage autonomous planning inside the worker

## Recommended related docs

- `prompt-ir-spec.md`
- `spacetimedb-v1-schema.md`
- `reducer-api-spec.md`
- `prototype-v1-scope.md`

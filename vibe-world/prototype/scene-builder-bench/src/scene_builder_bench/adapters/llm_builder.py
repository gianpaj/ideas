from __future__ import annotations

import json
import os
import re
from typing import Any

from scene_builder_bench.adapters.base import BuilderAdapter
from scene_builder_bench.utils import read_json
from scene_builder_bench.registry import project_root
from scene_builder_runtime import BuilderSpec, NormalizedScenePlan, WorldSettings


SYSTEM_PROMPT = """\
You are a scene-builder assistant that converts normalized scene plans into BuilderSpec JSON.

You MUST output ONLY valid JSON matching the BuilderSpec schema below. No markdown, no explanation, no code fences.

BuilderSpec JSON Schema:
{schema}

Rules:
- builder_version must be "0.1"
- request_id must match the plan's request_id
- intent_id must match the selected intent's intent_id
- operation must match the intent's operation ("create", "refine", or "remix")
- object_category must match the intent's category
- size_tier must match the intent's size_tier (default "medium")
- parts: each needs part_id, primitive, material, dimensions (3 floats), modifiers (list)
  - Allowed primitives: cube, slab, column, stair, wedge, arch, platform, blob
  - Allowed materials: stone, moss_stone, neon, glass_block, jelly, cloud, wood, lava_light, void, red
- instances: each needs instance_id, anchor_mode, offset (3 floats); reference_object and relation are optional (null if absent)
- materials: deduplicated list of all materials used across parts
- behaviors: from the intent's behavior_presets
  - Allowed behaviors: glow, bob, pulse, spin, bounce, open_close, hover
- placement: derive from transform_hints.position (mode, reference_object, relation, offset_meters)
  - If no transform_hints, use {{"mode": "absolute"}}
  - reference_object, relation, offset_meters should be null if not applicable
- complexity: must have part_count, instance_count, behavior_count matching actual counts
- diagnostics: empty list []
- target_object_id and base_object_version: null unless this is a refine/remix operation
- attachments: empty list []
- World settings caps: max_part_count={max_parts}, max_behavior_count={max_behaviors}, max_instances={max_instances}

Output ONLY the JSON object. No other text."""


def _extract_json(text: str) -> str:
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def _build_user_prompt(
    plan: NormalizedScenePlan,
    target_intent_id: str | None,
    object_context: BuilderSpec | None,
) -> str:
    plan_json = json.dumps(
        plan.model_dump(mode="json", exclude_none=True),
        indent=2,
    )
    parts = [f"Normalized scene plan:\n{plan_json}"]
    if target_intent_id:
        parts.append(f"\nSelect intent: {target_intent_id}")
    if object_context:
        ctx = json.dumps(
            object_context.model_dump(mode="json", exclude_none=True),
            indent=2,
        )
        parts.append(f"\nExisting object context (prior BuilderSpec):\n{ctx}")
    return "\n".join(parts)


def _call_openai(
    model: str,
    system: str,
    user: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key or "not-needed", base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
        max_completion_tokens=4096,
    )
    return resp.choices[0].message.content or ""


def _call_anthropic(model: str, system: str, user: str) -> str:
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
        temperature=0,
    )
    return resp.content[0].text


def _call_google(model: str, system: str, user: str) -> str:
    from google import genai
    client = genai.Client()
    resp = client.models.generate_content(
        model=model,
        contents=user,
        config=genai.types.GenerateContentConfig(
            system_instruction=system,
            temperature=0,
            max_output_tokens=4096,
        ),
    )
    return resp.text or ""


class LLMBuilderAdapter(BuilderAdapter):
    def __init__(
        self,
        *,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self._schema = read_json(project_root() / "schemas" / "builder_spec.schema.json")

        if "/" in model:
            self.provider, self.model_name = model.split("/", 1)
        else:
            self.provider, self.model_name = "", model

    def _call_llm(self, system: str, user: str) -> str:
        if self.provider == "anthropic":
            return _call_anthropic(self.model_name, system, user)
        if self.provider == "google":
            return _call_google(self.model_name, system, user)
        # openai or llamacpp or unknown → use OpenAI SDK
        return _call_openai(
            self.model_name,
            system,
            user,
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def build(
        self,
        plan: NormalizedScenePlan,
        *,
        target_intent_id: str | None,
        world_settings: WorldSettings,
        object_context: BuilderSpec | None,
    ) -> BuilderSpec:
        system = SYSTEM_PROMPT.format(
            schema=json.dumps(self._schema, indent=2),
            max_parts=world_settings.max_part_count,
            max_behaviors=world_settings.max_behavior_count,
            max_instances=world_settings.max_instances,
        )
        user = _build_user_prompt(plan, target_intent_id, object_context)

        raw = self._call_llm(system, user)
        extracted = _extract_json(raw)
        payload = json.loads(extracted)
        return BuilderSpec.model_validate(payload)

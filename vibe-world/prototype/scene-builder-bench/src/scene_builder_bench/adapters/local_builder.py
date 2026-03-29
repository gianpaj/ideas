from __future__ import annotations

from scene_builder_bench.adapters.base import BuilderAdapter
from scene_builder_runtime import BuilderSpec, NormalizedScenePlan, WorldSettings, build_builder_spec


class LocalBuilderAdapter(BuilderAdapter):
    def build(
        self,
        plan: NormalizedScenePlan,
        *,
        target_intent_id: str | None,
        world_settings: WorldSettings,
        object_context: BuilderSpec | None,
    ) -> BuilderSpec:
        return build_builder_spec(
            plan,
            target_intent_id=target_intent_id,
            world_settings=world_settings,
            object_context=object_context,
        )

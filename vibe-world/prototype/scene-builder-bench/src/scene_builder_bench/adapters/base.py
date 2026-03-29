from __future__ import annotations

from abc import ABC, abstractmethod

from scene_builder_runtime import BuilderSpec, NormalizedScenePlan, WorldSettings


class BuilderAdapter(ABC):
    @abstractmethod
    def build(
        self,
        plan: NormalizedScenePlan,
        *,
        target_intent_id: str | None,
        world_settings: WorldSettings,
        object_context: BuilderSpec | None,
    ) -> BuilderSpec:
        raise NotImplementedError

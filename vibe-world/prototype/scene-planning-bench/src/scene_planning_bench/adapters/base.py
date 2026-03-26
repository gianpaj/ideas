from __future__ import annotations

from abc import ABC, abstractmethod

from scene_planning_bench.types import LoadedTask


class Adapter(ABC):
    name: str

    @abstractmethod
    def generate(self, task: LoadedTask) -> str:
        raise NotImplementedError

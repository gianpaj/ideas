from __future__ import annotations

import json

from scene_planning_bench.adapters.base import Adapter
from scene_planning_bench.types import LoadedTask


class MockAdapter(Adapter):
    name = "mock"

    def generate(self, task: LoadedTask) -> str:
        return json.dumps(task.task.gold_payload())

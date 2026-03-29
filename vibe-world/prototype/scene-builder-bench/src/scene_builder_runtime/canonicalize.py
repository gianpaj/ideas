from __future__ import annotations

import json
from typing import Any


def canonicalize_payload(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

from __future__ import annotations

from hashlib import sha256

from scene_builder_runtime.canonicalize import canonicalize_payload


def hash_payload(payload: object) -> str:
    return sha256(canonicalize_payload(payload).encode("utf-8")).hexdigest()

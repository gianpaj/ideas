"""Constraint/rubric scorer for the production voxel "core" artifact.

Unlike the gold-reference scorers (builder/voxel_builder), this scores a model
core against the *rules* the production prompt enforces, so optimizing the bench
prompt transfers to the shipped object-generation path rather than rewarding one
fixed gold shape. Mirrors the validity gates in @3dvibegame/ai-planning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from scene_runtime.artifacts import VoxelBuilderSpec, VoxelCoreSpec

# The only material ids the production renderer maps to colors. Anything else
# renders as a fallback, so the prompt restricts the model to these.
ALLOWED_MATERIALS = frozenset(
    {
        "moss_stone",
        "wood",
        "neon",
        "glass_block",
        "jelly",
        "cloud",
        "lava_light",
        "void",
        "red",
        "stone",
    }
)

ALLOWED_OP_KINDS = frozenset({"add_box", "add_sphere", "add_line"})

# Keys each op kind is allowed to carry. Production zod strips anything else
# (so the op still compiles), but a stray key means the model authored an
# attribute that silently vanishes — most often a `color_hint` placed on an op
# instead of its material, so the player's requested color never renders.
_COMMON_OP_KEYS = frozenset({"op_id", "kind", "mode", "material_id", "tags"})
_OP_KEYS_BY_KIND: dict[str, frozenset[str]] = {
    "add_box": _COMMON_OP_KEYS | {"position", "size"},
    "add_sphere": _COMMON_OP_KEYS | {"center", "radius"},
    "add_line": _COMMON_OP_KEYS | {"from", "to", "radius", "shape"},
}

# The prompt says "Aim for 4-14 operations." for a single object.
OP_COUNT_MIN = 4
OP_COUNT_MAX = 14

# The prompt says "Keep the object near y=0 (above the floor)". Only *floating*
# is a real defect: the server's groundOperations lifts any object whose lowest
# voxel is below the floor up to y=0, so a negative min_y is always auto-fixed
# and must NOT be penalized. It never pulls a floater down, so a lowest voxel
# more than this tolerance above the floor stays hovering — that is the failure.
GROUND_TOLERANCE = 0.5

_HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


@dataclass
class VoxelCoreScore:
    schema_validity: float
    subscores: dict[str, float] = field(default_factory=dict)
    is_rejection: bool = False
    errors: list[str] = field(default_factory=list)


def compute_voxel_core_score(
    payload: Any,
    *,
    profile: str = "object",
) -> VoxelCoreScore:
    """Score a decoded model output against the production core rules.

    `payload` is the already-JSON-decoded model output. `profile` selects the
    expected behavior ("object" = author a core; "reject" = refuse a meaningless
    prompt).
    """

    if profile == "reject":
        return _score_reject(payload)
    return _score_object(payload)


def _score_reject(payload: Any) -> VoxelCoreScore:
    if not isinstance(payload, dict):
        return VoxelCoreScore(
            schema_validity=0.0,
            subscores={"rejected_correctly": 0.0},
            errors=["output was not a JSON object"],
        )
    rejection = payload.get("rejection")
    rejected = isinstance(rejection, str) and bool(rejection.strip())
    return VoxelCoreScore(
        schema_validity=1.0,
        subscores={"rejected_correctly": 1.0 if rejected else 0.0},
        is_rejection=rejected,
        errors=[] if rejected else ["expected a {\"rejection\": ...} response"],
    )


def _score_object(payload: Any) -> VoxelCoreScore:
    errors: list[str] = []

    # A rejection on a buildable prompt is a hard fail (the model refused a valid
    # object request).
    if isinstance(payload, dict) and isinstance(payload.get("rejection"), str):
        return VoxelCoreScore(
            schema_validity=0.0,
            subscores={},
            is_rejection=True,
            errors=["unexpected rejection of a buildable prompt"],
        )

    try:
        core = VoxelCoreSpec.model_validate(payload)
    except Exception as exc:  # noqa: BLE001 - surface any validation failure
        return VoxelCoreScore(
            schema_validity=0.0,
            subscores={},
            errors=[f"core did not validate: {exc}"],
        )

    core_dict = core.model_dump(mode="json", exclude_none=True)
    subscores = _rubric_subscores(core_dict)

    # "compiles" hard-fail gate: the core must assemble into a VoxelBuilderSpec
    # envelope that the strict production-equivalent model accepts.
    compiles = True
    try:
        VoxelBuilderSpec.model_validate(assemble_envelope(core_dict))
    except Exception as exc:  # noqa: BLE001 - surface any validation failure
        compiles = False
        errors.append(f"envelope did not compile: {exc}")

    return VoxelCoreScore(
        schema_validity=1.0 if compiles else 0.0,
        subscores=subscores,
        errors=errors,
    )


def _rubric_subscores(core: dict[str, Any]) -> dict[str, float]:
    ops = core.get("operations", [])
    materials = core.get("materials", [])
    declared_ids = {m.get("material_id") for m in materials}

    op_kinds_allowed = _mean(
        1.0 if op.get("kind") in ALLOWED_OP_KINDS else 0.0 for op in ops
    )

    op_ids = [op.get("op_id") for op in ops]
    op_ids_unique = (
        1.0
        if op_ids and all(op_ids) and len(set(op_ids)) == len(op_ids)
        else 0.0
    )

    op_count_in_range = 1.0 if OP_COUNT_MIN <= len(ops) <= OP_COUNT_MAX else 0.0

    materials_declared = (
        1.0
        if ops and all(op.get("material_id") in declared_ids for op in ops)
        else 0.0
    )

    palette_compliance = _mean(
        1.0 if m.get("material_id") in ALLOWED_MATERIALS else 0.0
        for m in materials
    )

    hints = [m.get("color_hint") for m in materials if m.get("color_hint")]
    color_hint_valid = (
        1.0
        if not hints
        else _mean(1.0 if _HEX_COLOR.match(str(h)) else 0.0 for h in hints)
    )

    ops_well_formed = _mean(
        1.0 if _op_extra_keys(op) == frozenset() else 0.0 for op in ops
    )

    grounded = _grounded_score(ops)

    return {
        "op_kinds_allowed": round(op_kinds_allowed, 6),
        "op_ids_unique": op_ids_unique,
        "op_count_in_range": op_count_in_range,
        "ops_well_formed": round(ops_well_formed, 6),
        "materials_declared": materials_declared,
        "palette_compliance": round(palette_compliance, 6),
        "color_hint_valid": round(color_hint_valid, 6),
        "grounded": grounded,
    }


def _op_extra_keys(op: dict[str, Any]) -> frozenset[str]:
    """Keys on an op that its kind does not define (production silently strips
    them, so the authored attribute — e.g. a misplaced color_hint — is lost)."""

    allowed = _OP_KEYS_BY_KIND.get(op.get("kind"))
    if allowed is None:
        # Unknown kind is already penalized by op_kinds_allowed; don't double-count.
        return frozenset()
    return frozenset(op.keys()) - allowed


def _grounded_score(ops: list[dict[str, Any]]) -> float:
    try:
        min_y = min(_op_min_y(op) for op in ops) if ops else 0.0
    except (TypeError, ValueError, KeyError, IndexError):
        return 0.0
    # Negative min_y is auto-grounded by the server; only floating is a defect.
    return 1.0 if min_y <= GROUND_TOLERANCE else 0.0


def _op_min_y(op: dict[str, Any]) -> float:
    kind = op.get("kind")
    if kind == "add_box":
        return float(op["position"][1]) - float(op["size"][1]) / 2.0
    if kind == "add_sphere":
        return float(op["center"][1]) - float(op["radius"])
    if kind == "add_line":
        return min(float(op["from"][1]), float(op["to"][1])) - float(op["radius"])
    # Unknown op kind contributes no floor constraint.
    return 0.0


def _strip_op(op: dict[str, Any]) -> dict[str, Any]:
    """Drop keys an op kind doesn't define, mirroring production zod's strip on
    `parseVoxelBuilderSpec` so the compile gate doesn't hard-fail on stray keys.
    The soft penalty for those keys lives in `ops_well_formed`."""

    allowed = _OP_KEYS_BY_KIND.get(op.get("kind"))
    if allowed is None:
        return op
    return {key: value for key, value in op.items() if key in allowed}


def assemble_envelope(core: dict[str, Any], source_prompt: str = "bench") -> dict[str, Any]:
    """Wrap a core into a full VoxelBuilderSpec envelope (mirrors the server's
    `assembleVoxelSpec`) so it can be validated against voxel_builder.schema.json.
    """

    base_id = f"{_slug(core['object_category'])}_{_short_hash(source_prompt)}"
    materials = []
    for entry in core.get("materials", []):
        material: dict[str, Any] = {
            "material_id": entry["material_id"],
            "label": entry["material_id"],
            "render_class": "matte_voxel",
        }
        if entry.get("color_hint"):
            material["color_hint"] = entry["color_hint"]
        if entry.get("tags"):
            material["tags"] = entry["tags"]
        materials.append(material)

    return {
        "spec_version": "0.1",
        "request_id": f"{base_id}::prompt_0",
        "intent_id": f"{base_id}::intent_0",
        "operation": "create",
        "target_object_id": None,
        "base_object_version": None,
        "object_category": _slug(core["object_category"]),
        "size_tier": core["size_tier"],
        "style_tags": _unique(_slug(tag) for tag in core.get("style_tags", []))[:6],
        "behaviors": _unique(_slug(b) for b in core.get("behaviors", []))[:3],
        "grid": {"unit_meters": 0.5, "up_axis": "y", "rotation_step_degrees": 90},
        "placement": {
            "mode": "absolute",
            "reference_object": None,
            "relation": None,
            "offset": [0, 0, 0],
        },
        "materials": materials,
        "anchors": [
            {"anchor_id": "base", "position": [0, 0, 0], "tags": ["placement"]},
            {"anchor_id": "focus", "position": [0, 2.4, 0], "tags": ["camera"]},
        ],
        "operations": [_strip_op(op) for op in core.get("operations", [])],
        "compile_hints": {
            "preferred_runtime": "primitive_parts",
            "preserve_edit_regions": True,
            "collision_detail": "coarse",
        },
        "diagnostics": ["generated by voxel-builder ai worker"],
    }


def _mean(values: Any) -> float:
    collected = list(values)
    if not collected:
        return 1.0
    return sum(collected) / len(collected)


def _slug(value: str) -> str:
    slugged = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:40]
    return slugged or "object"


def _unique(values: Any) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def _short_hash(value: str) -> str:
    h = 0x811C9DC5
    for ch in value:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return format(h, "08x")

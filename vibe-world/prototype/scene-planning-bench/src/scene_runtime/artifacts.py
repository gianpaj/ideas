from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from scene_runtime.models import Relation


class ArtifactType(str, Enum):
    SCENE_ACTIONS = "scene_actions"
    BUILDER = "builder"
    VOXEL_BUILDER = "voxel_builder"
    # The production "creative core" the game's Gemini call authors (materials +
    # operations + size/style/behaviors/quantity/scale). The server fills the
    # deterministic envelope (grid/placement/anchors/ids) around it, so the bench
    # scores this core, not the full VoxelBuilderSpec. Mirrors `voxelCoreSchema`
    # in @3dvibegame/ai-planning.
    VOXEL_CORE = "voxel_core"


class BuilderOperation(str, Enum):
    CREATE = "create"
    REFINE = "refine"
    REMIX = "remix"


class BlendMode(str, Enum):
    UNION = "union"
    SUBTRACT = "subtract"
    INTERSECT = "intersect"
    EXCLUDE = "exclude"


class UpAxis(str, Enum):
    Y = "y"


Vector3 = Annotated[list[float], Field(min_length=3, max_length=3)]


class BuilderPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_id: str
    primitive: str
    material: str
    dimensions: Vector3
    modifiers: list[str] = Field(default_factory=list)
    local_position: Vector3 | None = None
    local_rotation: Vector3 | None = None
    local_scale: Vector3 | None = None


class BuilderInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance_id: str
    anchor_mode: Literal["absolute", "relative"]
    reference_object: str | None = None
    relation: Relation | None = None
    offset: Vector3


class BuilderPlacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["absolute", "relative"]
    reference_object: str | None = None
    relation: Relation | None = None
    offset_meters: float | None = None


class BuilderComplexity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_count: int = Field(ge=0)
    instance_count: int = Field(ge=0)
    behavior_count: int = Field(ge=0)


class BuilderSpec(BaseModel):
    """Mid-level semantic IR: parts + instances + materials for an object."""

    model_config = ConfigDict(extra="forbid")

    builder_version: Literal["0.1"] = "0.1"
    request_id: str
    intent_id: str
    operation: BuilderOperation
    target_object_id: str | None = None
    base_object_version: int | None = None
    object_category: str
    size_tier: str
    parts: list[BuilderPart]
    instances: list[BuilderInstance] = Field(default_factory=list)
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    behaviors: list[str] = Field(default_factory=list)
    placement: BuilderPlacement
    complexity: BuilderComplexity
    diagnostics: list[str] = Field(default_factory=list)


class VoxelGrid(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_meters: float = Field(gt=0)
    up_axis: UpAxis = UpAxis.Y
    rotation_step_degrees: Literal[90] = 90


class VoxelMaterial(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material_id: str
    label: str | None = None
    render_class: str | None = None
    color_hint: str | None = None
    tags: list[str] = Field(default_factory=list)


class VoxelAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anchor_id: str
    position: Vector3
    tags: list[str] = Field(default_factory=list)


class VoxelPlacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["absolute", "relative"]
    reference_object: str | None = None
    relation: Relation | None = None
    offset: Vector3


class RegionSelector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    by_bounds: dict[str, Any] | None = None
    by_tags: list[str] | None = None
    by_material_ids: list[str] | None = None


class CompileHints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_runtime: Literal["primitive_parts", "merged_mesh", "instanced_voxels"] | None = None
    preserve_edit_regions: bool | None = None
    preview_camera: dict[str, Any] | None = None
    collision_detail: Literal["coarse", "medium", "full"] | None = None


class AddBoxOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op_id: str
    kind: Literal["add_box"]
    mode: BlendMode | None = None
    position: Vector3
    size: Vector3
    material_id: str
    tags: list[str] = Field(default_factory=list)


class AddSphereOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op_id: str
    kind: Literal["add_sphere"]
    mode: BlendMode | None = None
    center: Vector3
    radius: float = Field(gt=0)
    material_id: str
    tags: list[str] = Field(default_factory=list)


class AddLineOp(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    op_id: str
    kind: Literal["add_line"]
    mode: BlendMode | None = None
    from_: Vector3 = Field(alias="from")
    to: Vector3
    radius: float = Field(gt=0)
    shape: Literal["rounded", "square"] | None = None
    material_id: str
    tags: list[str] = Field(default_factory=list)


class PaintRegionOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op_id: str
    kind: Literal["paint_region"]
    target: RegionSelector
    material_id: str


class RotateRegionOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op_id: str
    kind: Literal["rotate_region"]
    target: RegionSelector
    rotate: dict[str, Any]


class CloneRegionOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op_id: str
    kind: Literal["clone_region"]
    target: RegionSelector
    copies: dict[str, Any]
    mode: BlendMode | None = None


VoxelOp = Annotated[
    Union[AddBoxOp, AddSphereOp, AddLineOp, PaintRegionOp, RotateRegionOp, CloneRegionOp],
    Field(discriminator="kind"),
]


class VoxelCoreMaterial(BaseModel):
    # Production validates with plain zod objects (no .strict()), which strip
    # unknown keys rather than erroring — so ignore extras here too, instead of
    # hard-failing on something the game silently tolerates.
    model_config = ConfigDict(extra="ignore")

    material_id: str = Field(min_length=1, max_length=40)
    color_hint: str | None = None
    tags: list[str] | None = None


class VoxelCoreSpec(BaseModel):
    """Production "creative core" the game's Gemini call authors.

    Mirrors `voxelCoreSchema` in @3dvibegame/ai-planning: the LLM authors only
    metadata + the operations list; the server assembles the deterministic
    envelope (grid/placement/anchors/ids) around it. Operations stay permissive
    (raw dicts, like production's `z.array(z.unknown())`); the constraint scorer
    inspects them and the assembled envelope is validated separately.

    `extra="ignore"` mirrors production zod, which strips unknown top-level keys
    instead of erroring — the bench should not hard-fail on extras the game drops.
    """

    model_config = ConfigDict(extra="ignore")

    object_category: str = Field(min_length=1, max_length=60)
    size_tier: str = Field(min_length=1, max_length=20)
    style_tags: list[str] = Field(default_factory=list, max_length=12)
    behaviors: list[str] = Field(default_factory=list, max_length=6)
    materials: list[VoxelCoreMaterial] = Field(min_length=1, max_length=12)
    operations: list[dict[str, Any]] = Field(min_length=1, max_length=40)
    quantity: int = Field(default=1, ge=1, le=4)
    scale: float | None = Field(default=None, ge=0.25, le=4)


class VoxelBuilderSpec(BaseModel):
    """Low-level voxel/geometry operations spec for an object."""

    model_config = ConfigDict(extra="forbid")

    spec_version: Literal["0.1"] = "0.1"
    request_id: str
    intent_id: str
    operation: BuilderOperation
    target_object_id: str | None = None
    base_object_version: int | None = None
    object_category: str
    size_tier: str
    style_tags: list[str] = Field(default_factory=list)
    behaviors: list[str] = Field(default_factory=list)
    grid: VoxelGrid
    placement: VoxelPlacement
    materials: list[VoxelMaterial] = Field(default_factory=list)
    anchors: list[VoxelAnchor] = Field(default_factory=list)
    operations: list[VoxelOp]
    compile_hints: CompileHints | None = None
    diagnostics: list[str] = Field(default_factory=list)

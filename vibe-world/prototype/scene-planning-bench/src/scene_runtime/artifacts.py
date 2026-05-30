from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from scene_runtime.models import Relation


class ArtifactType(str, Enum):
    SCENE_ACTIONS = "scene_actions"
    BUILDER = "builder"
    VOXEL_BUILDER = "voxel_builder"


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

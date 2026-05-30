from __future__ import annotations

from scene_runtime.artifacts import VoxelBuilderSpec


def _sequence_ratio(expected: list[str], actual: list[str]) -> float:
    if not expected and not actual:
        return 1.0
    if not expected or not actual:
        return 0.0
    pairs = zip(expected, actual)
    matches = sum(1 for a, b in pairs if a == b)
    return matches / max(len(expected), len(actual))


def _set_ratio(expected: list[str], actual: list[str]) -> float:
    expected_set = set(expected)
    actual_set = set(actual)
    if not expected_set and not actual_set:
        return 1.0
    union = expected_set | actual_set
    if not union:
        return 1.0
    return len(expected_set & actual_set) / len(union)


def compute_voxel_scores(
    expected: VoxelBuilderSpec, actual: VoxelBuilderSpec
) -> dict[str, float]:
    category_match = 1.0 if expected.object_category == actual.object_category else 0.0
    operation_match = 1.0 if expected.operation == actual.operation else 0.0
    size_tier_match = 1.0 if expected.size_tier == actual.size_tier else 0.0

    placement_match = 1.0 if expected.placement == actual.placement else 0.0

    expected_ops = [op.kind for op in expected.operations]
    actual_ops = [op.kind for op in actual.operations]
    op_kind_match = _sequence_ratio(expected_ops, actual_ops)
    op_count_match = 1.0 if len(expected_ops) == len(actual_ops) else 0.0

    expected_materials = [material.material_id for material in expected.materials]
    actual_materials = [material.material_id for material in actual.materials]
    material_set_match = _set_ratio(expected_materials, actual_materials)

    op_material_expected: list[str] = []
    op_material_actual: list[str] = []
    for op in expected.operations:
        op_material_expected.append(getattr(op, "material_id", ""))
    for op in actual.operations:
        op_material_actual.append(getattr(op, "material_id", ""))
    op_material_match = _sequence_ratio(op_material_expected, op_material_actual)

    grid_match = 1.0 if expected.grid == actual.grid else 0.0

    return {
        "category_match": category_match,
        "operation_match": operation_match,
        "size_tier_match": size_tier_match,
        "placement_match": placement_match,
        "op_kind_match": op_kind_match,
        "op_count_match": op_count_match,
        "material_set_match": material_set_match,
        "op_material_match": op_material_match,
        "grid_match": grid_match,
    }

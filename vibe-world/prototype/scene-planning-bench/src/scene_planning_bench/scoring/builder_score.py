from __future__ import annotations

from scene_runtime.artifacts import BuilderSpec


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


def compute_builder_scores(
    expected: BuilderSpec, actual: BuilderSpec
) -> dict[str, float]:
    category_match = 1.0 if expected.object_category == actual.object_category else 0.0
    operation_match = 1.0 if expected.operation == actual.operation else 0.0
    size_tier_match = 1.0 if expected.size_tier == actual.size_tier else 0.0

    placement_match = 1.0 if expected.placement == actual.placement else 0.0

    expected_primitives = [part.primitive for part in expected.parts]
    actual_primitives = [part.primitive for part in actual.parts]
    part_primitive_match = _sequence_ratio(expected_primitives, actual_primitives)

    expected_part_materials = [part.material for part in expected.parts]
    actual_part_materials = [part.material for part in actual.parts]
    part_material_match = _sequence_ratio(expected_part_materials, actual_part_materials)

    material_match = _set_ratio(expected.materials, actual.materials)

    expected_complexity = expected.complexity
    actual_complexity = actual.complexity
    complexity_match = 1.0 if expected_complexity == actual_complexity else 0.0

    return {
        "category_match": category_match,
        "operation_match": operation_match,
        "size_tier_match": size_tier_match,
        "placement_match": placement_match,
        "part_primitive_match": part_primitive_match,
        "part_material_match": part_material_match,
        "material_set_match": material_match,
        "complexity_match": complexity_match,
    }

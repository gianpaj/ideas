from __future__ import annotations


def compute_schema_score(schema_errors: list[str]) -> float:
    return 0.0 if schema_errors else 1.0

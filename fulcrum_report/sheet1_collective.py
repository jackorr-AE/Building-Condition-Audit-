"""Sheet 1 collective item type/material field resolution."""

from __future__ import annotations

# Known Fulcrum field names per condition column (first match wins).
CONDITION_TYPE_FIELDS: dict[str, list[str]] = {
    "condition_external_walls": ["type_of_external_walls"],
    "condition_downpipes": ["Material_Downpipes", "material_downpipes", "type_of_downpipes"],
    "condition_gutters": ["material_gutter", "material_gutters", "Material_Gutters", "type_of_gutters"],
    "condition_ceiling": ["type_of_ceiling"],
    "condition_floor": ["type_of_flooring"],
    "condition_wall": ["type_of_walls"],
    "condition_lights": ["type_of_light_fitting"],
    "condition_joinery": ["type_of_joinery", "type_of_benchtop"],
}


def row_value_insensitive(row: dict[str, str], field_name: str) -> str:
    target = (field_name or "").strip().lower()
    if not target:
        return ""
    for key, value in row.items():
        if (key or "").strip().lower() == target and value and str(value).strip():
            return str(value).strip()
    return ""


def sheet1_type_material(
    row: dict[str, str],
    condition_field: str,
    explicit_type_fields: list[str] | None = None,
) -> str:
    """Return type/material text for a Sheet 1 condition column."""
    candidates: list[str] = []
    if explicit_type_fields:
        candidates.extend(explicit_type_fields)
    candidates.extend(CONDITION_TYPE_FIELDS.get(condition_field, []))
    suffix = condition_field.replace("condition_", "", 1) if condition_field.startswith("condition_") else ""
    if suffix:
        candidates.extend(
            [
                f"type_of_{suffix}",
                f"material_{suffix}",
                f"Material_{suffix}",
            ]
        )
    seen: set[str] = set()
    for name in candidates:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        value = row_value_insensitive(row, name)
        if value:
            return value
    return ""

import csv

from fulcrum_report.paths import ProjectPaths
from fulcrum_report.xlsx_io import FulcrumWorkbook


def keep_non_empty_columns(columns: list[str], rows: list[dict[str, str]]) -> list[str]:
    return [c for c in columns if any((r.get(c) or "").strip() for r in rows)]


def write_section(writer: csv.writer, title: str, columns: list[str], rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    cols = keep_non_empty_columns(columns, rows)
    writer.writerow([title])
    writer.writerow(cols)
    for r in rows:
        writer.writerow([(r.get(c) or "").strip() for c in cols])
    writer.writerow([])


def split_asset_subtype(asset_type: str) -> str:
    parts = [p.strip() for p in (asset_type or "").split(",")]
    if len(parts) >= 2:
        return parts[1]
    return asset_type or ""


def asset_extra_fields(r: dict[str, str]) -> dict[str, str]:
    return {
        "Comments": (r.get("descriptioncomments") or "").strip(),
        "Last Test Date": (r.get("last_test_date") or "").strip(),
    }


INTERNAL_COMMENT_BY_SUBTYPE = {
    "Floor": "comments_floor",
    "Walls": "comments_walls",
    "Ceiling": "comments_ceiling",
    "Lights": "comments_lights",
    "Joinery": "comments_joinery",
}


def main() -> int:
    paths = ProjectPaths()
    wb = FulcrumWorkbook.from_project(paths)

    id_to_location = {(r.get("_record_id") or "").strip(): (r.get("location") or "").strip() for r in wb.sheet1}

    internal_building_rows: list[dict[str, str]] = []
    component_map = [
        ("Floor", "type_of_flooring", "condition_floor", "quantity_floor"),
        ("Walls", "type_of_walls", "condition_wall", ""),
        ("Ceiling", "", "condition_ceiling", ""),
        ("Lights", "type_of_light_fitting", "condition_lights", "quantity_lights"),
        ("Joinery", "type_of_joinery", "condition_joinery", ""),
    ]

    for r in wb.sheet1:
        loc = (r.get("location") or "").strip()
        if not loc or loc.startswith("External"):
            continue
        for subtype, type_field, cond_field, qty_field in component_map:
            cond = (r.get(cond_field) or "").strip()
            if not cond:
                continue
            type_material = (r.get(type_field) or "").strip() if type_field else ""
            if subtype == "Joinery":
                benchtop = (r.get("type_of_benchtop") or "").strip()
                if benchtop:
                    type_material = f"{type_material} / {benchtop}" if type_material else benchtop
            qty = (r.get(qty_field) or "").strip() if qty_field else ""
            comment_field = INTERNAL_COMMENT_BY_SUBTYPE.get(subtype, "")
            internal_building_rows.append(
                {
                    "Location": loc,
                    "Asset Sub-Type": subtype,
                    "Type/Material": type_material,
                    "Condition": cond,
                    "Quantity": qty,
                    "Comments": (r.get(comment_field) or "").strip() if comment_field else "",
                }
            )

    building_external_rows: list[dict[str, str]] = []
    for r in wb.sheet2:
        pid = (r.get("_parent_id") or "").strip()
        loc = id_to_location.get(pid, "")
        desc = (r.get("description_of_collectable_item_external") or "").strip()
        cond = (r.get("condition_othercollectable_external") or "").strip()
        typ = (r.get("type_of_collectable_item_external") or "").strip()
        if not desc and not cond and not typ:
            continue
        building_external_rows.append(
            {
                "Location": loc or "External",
                "Asset Sub-Type": desc,
                "Type/Material": typ,
                "Condition": cond,
                "Quantity": (r.get("quantity_othercollectableexternal") or "").strip(),
                "Unit": (r.get("unit_othercollectableexternal") or "").strip(),
                "Comments": (r.get("comments_othercollectable_external") or "").strip(),
            }
        )

    def section_from_assets(
        title: str,
        predicate,
        columns: list[str],
        enrich=None,
    ) -> tuple[str, list[str], list[dict[str, str]]]:
        out: list[dict[str, str]] = []
        for r in wb.sheet3:
            at = (r.get("asset_type") or "").strip()
            if not predicate(at):
                continue
            row = {
                "Barcode No": (r.get("asset_id_barcode") or "").strip(),
                "Location": (r.get("location_repeat") or "").strip(),
                "Asset Sub-Type": split_asset_subtype(at),
                "Type/Material": (r.get("asset_description") or "").strip(),
                "Condition": (r.get("condition_asset") or "").strip(),
                "Last Test Result": (r.get("last_test_result") or "").strip(),
                "Door Type": (r.get("door_type") or "").strip(),
                "Door Frame Type": (r.get("door_frame_type") or "").strip(),
                "Door Closer": (r.get("door_closer") or "").strip(),
                "Door Jams Fitted": (r.get("door_jams_fitted") or "").strip(),
                "Door is Compliant": (r.get("door_is_compliant") or "").strip(),
                "Lockable": (r.get("do_they_lock_doors") or "").strip(),
                "Gate Type": (r.get("gate_type") or "").strip(),
                "Lockable (Gate)": (r.get("do_they_lock_gates") or "").strip(),
                "Frame Type": (r.get("frame_type") or "").strip(),
                "Lockable (Window)": (r.get("do_they_lock_windows") or "").strip(),
                "Type of Aircon Unit": (r.get("type_of_aircon_unit") or "").strip(),
                "Type of Boiler": (r.get("type_of_boiler") or "").strip(),
                "Type of Playground": (r.get("type_of_playground") or "").strip(),
                "Sandpit Size (m²)": (r.get("size_of_sandpit_m2") or "").strip(),
                **asset_extra_fields(r),
            }
            if enrich:
                row.update(enrich(r))
            out.append(row)
        return (title, columns, out)

    standard_asset_columns = [
        "Barcode No",
        "Location",
        "Asset Sub-Type",
        "Type/Material",
        "Condition",
        "Comments",
        "Last Test Result",
        "Last Test Date",
    ]

    sections = [
        (
            "Building Internal",
            ["Location", "Asset Sub-Type", "Type/Material", "Condition", "Quantity", "Comments"],
            internal_building_rows,
        ),
        section_from_assets(
            "Doors",
            lambda at: at == "Doors/Windows/Gates, Doors",
            [
                "Barcode No",
                "Location",
                "Asset Sub-Type",
                "Door Type",
                "Door Frame Type",
                "Condition",
                "Comments",
                "Door Closer",
                "Door Jams Fitted",
                "Door is Compliant",
                "Lockable",
            ],
        ),
        section_from_assets(
            "Electrical",
            lambda at: at.startswith("Electrical,"),
            standard_asset_columns,
        ),
        (
            "Building External",
            ["Location", "Asset Sub-Type", "Type/Material", "Condition", "Quantity", "Unit", "Comments"],
            building_external_rows,
        ),
        section_from_assets(
            "Fire",
            lambda at: at.startswith("Fire,"),
            standard_asset_columns,
        ),
        section_from_assets(
            "Gates / Fencing",
            lambda at: at == "Doors/Windows/Gates, Gates",
            [
                "Barcode No",
                "Location",
                "Asset Sub-Type",
                "Gate Type",
                "Condition",
                "Comments",
                "Lockable (Gate)",
            ],
        ),
        section_from_assets(
            "Gas",
            lambda at: at == "Gas",
            standard_asset_columns,
        ),
        section_from_assets(
            "HVAC",
            lambda at: at.startswith("HVAC,"),
            [
                "Barcode No",
                "Location",
                "Asset Sub-Type",
                "Type/Material",
                "Type of Aircon Unit",
                "Condition",
                "Comments",
                "Last Test Result",
                "Last Test Date",
            ],
        ),
        section_from_assets(
            "Plumbing",
            lambda at: at.startswith("Plumbing,"),
            [
                "Barcode No",
                "Location",
                "Asset Sub-Type",
                "Type/Material",
                "Type of Boiler",
                "Condition",
                "Comments",
                "Last Test Result",
                "Last Test Date",
            ],
        ),
        section_from_assets(
            "Security",
            lambda at: at.startswith("Security,"),
            standard_asset_columns,
        ),
        section_from_assets(
            "Defibrillator",
            lambda at: at == "Defibrillator",
            standard_asset_columns,
        ),
    ]

    paths.appendix_b_csv.parent.mkdir(parents=True, exist_ok=True)
    with paths.appendix_b_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for title, columns, rows in sections:
            write_section(w, title, columns, rows)

    print(f"Wrote {paths.appendix_b_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

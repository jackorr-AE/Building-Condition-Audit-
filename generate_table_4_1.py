import csv

from fulcrum_report.conditions import aggregate_doors, worst_condition
from fulcrum_report.paths import ProjectPaths
from fulcrum_report.xlsx_io import FulcrumWorkbook

PLUMBING_COMMENT_FIELDS = ("comments_taps", "comments_basins", "comments_toiletpans")

INTERNAL_COLUMNS: list[tuple[str, str | None, str | None]] = [
    ("Walls", "condition_wall", "comments_walls"),
    ("Flooring", "condition_floor", "comments_floor"),
    ("Ceilings", "condition_ceiling", "comments_ceiling"),
    ("Lights", "condition_lights", "comments_lights"),
    ("Doors", None, None),
    ("Plumbing", None, None),
    ("Cabinetry & Fixed Furniture", "condition_joinery", "comments_joinery"),
]


def plumbing_comment(row: dict[str, str]) -> str:
    parts = [(row.get(f) or "").strip() for f in PLUMBING_COMMENT_FIELDS]
    return "; ".join(p for p in parts if p)


def main() -> int:
    paths = ProjectPaths()
    wb = FulcrumWorkbook.from_project(paths)
    internal_locations = paths.config["internal_locations"]
    doors_method = paths.config.get("doors_aggregation", "average")

    sheet1_by_id = {r["_record_id"]: r for r in wb.sheet1 if r.get("_record_id")}

    doors_by_parent: dict[str, list[str]] = {}
    for a in wb.sheet3:
        parent_id = a.get("_parent_id", "").strip()
        if not parent_id or a.get("asset_type", "").strip() != "Doors/Windows/Gates, Doors":
            continue
        cond = a.get("condition_asset", "").strip()
        if cond:
            doors_by_parent.setdefault(parent_id, []).append(cond)

    out_rows: list[dict[str, str]] = []
    for rid, r in sheet1_by_id.items():
        location = r.get("location", "").strip()
        if location not in internal_locations:
            continue

        ceilings = r.get("condition_ceiling", "").strip()
        if location == "Staircase":
            ceilings = "N/A"
        elif ceilings == "Not Applicable":
            ceilings = "N/A"

        row: dict[str, str] = {
            "Room / Area": location,
            "Location Comments": (r.get("location_comments") or "").strip(),
        }

        for heading, cond_field, comment_field in INTERNAL_COLUMNS:
            if heading == "Doors":
                row[heading] = aggregate_doors(doors_by_parent.get(rid, []), doors_method)
            elif heading == "Plumbing":
                row[heading] = worst_condition(
                    [
                        r.get("condition_taps", "").strip(),
                        r.get("condition_basins", "").strip(),
                        r.get("condition_toiletpans", "").strip(),
                    ]
                )
                row[f"{heading} Comments"] = plumbing_comment(r)
            elif cond_field:
                row[heading] = r.get(cond_field, "").strip()
                if comment_field:
                    row[f"{heading} Comments"] = (r.get(comment_field) or "").strip()

        for k, v in list(row.items()):
            if v == "Not Applicable":
                row[k] = "N/A"

        out_rows.append(row)

    out_rows.sort(key=lambda x: internal_locations.index(x["Room / Area"]))

    fieldnames = ["Room / Area"]
    if any((r.get("Location Comments") or "").strip() for r in out_rows):
        fieldnames.append("Location Comments")
    for heading, cond_field, comment_field in INTERNAL_COLUMNS:
        fieldnames.append(heading)
        comment_heading = f"{heading} Comments"
        if heading == "Doors":
            continue
        if any((r.get(comment_heading) or "").strip() for r in out_rows):
            fieldnames.append(comment_heading)

    paths.table_4_1.parent.mkdir(parents=True, exist_ok=True)
    with paths.table_4_1.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(out_rows)

    print(f"Wrote {paths.table_4_1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

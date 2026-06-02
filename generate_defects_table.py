import csv

from fulcrum_report.paths import ProjectPaths
from fulcrum_report.xlsx_io import FulcrumWorkbook, defect_description_and_repair


def photo_reference(row: dict[str, str]) -> str:
    urls = (row.get("photos_defects_urls") or "").strip()
    if urls:
        return urls
    return (row.get("photos_defects") or "").strip()


def dedupe_defects(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: dict[tuple[str, ...], dict[str, str]] = {}
    order: list[tuple[str, ...]] = []

    for row in rows:
        key = (
            row.get("Area", "").strip(),
            row.get("Location", "").strip(),
            row.get("Asset Type", "").strip(),
            row.get("Defect Description", "").strip(),
            row.get("Repair Description", "").strip(),
        )
        if key not in seen:
            seen[key] = dict(row)
            order.append(key)
            continue

        existing_photos = seen[key].get("Photo Reference", "").strip()
        new_photos = row.get("Photo Reference", "").strip()
        if new_photos:
            parts = [p.strip() for p in f"{existing_photos}, {new_photos}".split(",") if p.strip()]
            unique: list[str] = []
            seen_ids: set[str] = set()
            for part in parts:
                if part not in seen_ids:
                    seen_ids.add(part)
                    unique.append(part)
            seen[key]["Photo Reference"] = ", ".join(unique)

    return [seen[k] for k in order]


def main() -> int:
    paths = ProjectPaths()
    wb = FulcrumWorkbook.from_project(paths)

    area_by_parent = {
        (r.get("_record_id") or "").strip(): (r.get("location") or "").strip()
        for r in wb.sheet1
        if (r.get("_record_id") or "").strip() and (r.get("location") or "").strip()
    }

    out_rows: list[dict[str, str]] = []
    for d in wb.sheet4:
        parent_id = (d.get("_parent_id") or "").strip()
        defect, repair = defect_description_and_repair(d)
        out_rows.append(
            {
                "Area": area_by_parent.get(parent_id, ""),
                "Location": (d.get("location_defect") or "").strip(),
                "Asset Type": (d.get("asset_type_defects") or "").strip(),
                "Defect Description": defect,
                "Repair Description": repair,
                "Timeframe": (d.get("Timeframe") or d.get("timeframe") or "").strip(),
                "Photo Reference": photo_reference(d),
            }
        )

    if paths.config.get("dedupe_defects", True):
        before = len(out_rows)
        out_rows = dedupe_defects(out_rows)
        if before != len(out_rows):
            print(f"Deduplicated defects: {before} -> {len(out_rows)} rows")

    fieldnames = [
        "Area",
        "Location",
        "Asset Type",
        "Defect Description",
        "Repair Description",
        "Timeframe",
        "Photo Reference",
    ]
    paths.table_defects.parent.mkdir(parents=True, exist_ok=True)
    with paths.table_defects.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    print(f"Wrote {paths.table_defects}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

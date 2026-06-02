import csv
import re

from fulcrum_report.paths import ProjectPaths
from fulcrum_report.sheet1_collective import sheet1_type_material
from fulcrum_report.xlsx_io import FulcrumWorkbook


def title_case_heading(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return s
    s = s.replace("Linemarking", "Line Marking")
    s = s.replace("Wheel stops", "Wheel Stops")
    parts = re.split(r"(\s+|/|&|\(|\)|-)", s)
    out_parts: list[str] = []
    for p in parts:
        if not p or re.fullmatch(r"(\s+|/|&|\(|\)|-)", p):
            out_parts.append(p)
        else:
            out_parts.append(p[:1].upper() + p[1:])
    return "".join(out_parts)


def normalize_value(v: str, na_for_blank: bool = False) -> str:
    vv = (v or "").strip()
    if not vv:
        return "N/A" if na_for_blank else ""
    if vv == "Not Applicable":
        return "N/A"
    return vv


def comment_field_for_condition(field: str) -> str:
    if field.startswith("condition_"):
        return "comments_" + field[len("condition_") :]
    return ""


def main() -> int:
    paths = ProjectPaths()
    wb = FulcrumWorkbook.from_project(paths)
    external_areas = paths.config["external_areas"]

    sheet1_by_location = {(r.get("location") or "").strip(): r for r in wb.sheet1 if (r.get("location") or "").strip()}

    sheet2_by_parent: dict[str, list[dict[str, str]]] = {}
    for r in wb.sheet2:
        pid = (r.get("_parent_id") or "").strip()
        if pid:
            sheet2_by_parent.setdefault(pid, []).append(r)

    output_paths = [paths.table_4_2, paths.table_4_3]

    for idx, (area, spec) in enumerate(external_areas.items()):
        s1 = sheet1_by_location.get(area, {})
        parent_id = (s1.get("_record_id") or "").strip()
        items = sheet2_by_parent.get(parent_id, [])

        item_cond: dict[str, str] = {}
        item_comment: dict[str, str] = {}
        for it in items:
            desc = (it.get("description_of_collectable_item_external") or "").strip()
            cond = (it.get("condition_othercollectable_external") or "").strip()
            cmt = (it.get("comments_othercollectable_external") or "").strip()
            if not desc:
                continue
            if desc not in item_cond:
                item_cond[desc] = cond
            elif not item_cond[desc] and cond:
                item_cond[desc] = cond
            if cmt and desc not in item_comment:
                item_comment[desc] = cmt

        row: dict[str, str] = {"Area": area}

        sheet1_pairs: list[tuple[str, str, str | None]] = []
        for col in spec.get("sheet1_columns", []):
            if not isinstance(col, (list, tuple)) or len(col) < 2:
                continue
            field = col[0]
            heading = col[1]
            explicit_type = list(col[2:]) if len(col) > 2 else None
            row[heading] = normalize_value(s1.get(field, ""), na_for_blank=False)
            cfield = comment_field_for_condition(field)
            comment_heading = f"{heading} Comments"
            if cfield:
                row[comment_heading] = (s1.get(cfield) or "").strip()
            material = sheet1_type_material(s1, field, explicit_type)
            material_heading = f"{heading} Material"
            if material:
                row[material_heading] = material
            sheet1_pairs.append((heading, comment_heading, cfield, material_heading if material else None))

        sheet2_headings: list[tuple[str, str]] = []
        for desc in spec.get("sheet2_items", []):
            heading = title_case_heading(desc)
            if desc in item_cond:
                row[heading] = normalize_value(item_cond.get(desc, ""), na_for_blank=True)
            else:
                row[heading] = ""
            comment_heading = f"{heading} Comments"
            if desc in item_comment:
                row[comment_heading] = item_comment[desc]
            sheet2_headings.append((heading, comment_heading))

        fieldnames = ["Area"]
        for heading, comment_heading, _, material_heading in sheet1_pairs:
            fieldnames.append(heading)
            if material_heading:
                fieldnames.append(material_heading)
            if (row.get(comment_heading) or "").strip():
                fieldnames.append(comment_heading)
        for heading, comment_heading in sheet2_headings:
            fieldnames.append(heading)
            if (row.get(comment_heading) or "").strip():
                fieldnames.append(comment_heading)

        if idx < len(output_paths):
            out_csv = output_paths[idx]
        elif spec.get("output"):
            out_csv = paths.tables_dir / spec["output"]
        else:
            out_csv = paths.tables_dir / f"Table_4-{idx + 2}.csv"

        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerow(row)
        print(f"Wrote {out_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

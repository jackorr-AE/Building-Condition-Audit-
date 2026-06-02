import csv
import re
from collections import defaultdict

from fulcrum_report.paths import ProjectPaths
from fulcrum_report.xlsx_io import FulcrumWorkbook


def n(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def first_non_empty(values: list[str]) -> str:
    for v in values:
        vv = (v or "").strip()
        if vv:
            return vv
    return ""


def main() -> int:
    paths = ProjectPaths()
    wb = FulcrumWorkbook.from_project(paths)

    id_to_loc = {(r.get("_record_id") or "").strip(): (r.get("location") or "").strip() for r in wb.sheet1}

    internal_comment = {}
    subtype_to_field = {
        "floor": "comments_floor",
        "walls": "comments_walls",
        "ceiling": "comments_ceiling",
        "lights": "comments_lights",
        "joinery": "comments_joinery",
    }
    for r in wb.sheet1:
        loc = (r.get("location") or "").strip()
        if not loc or loc.startswith("External"):
            continue
        for st, fld in subtype_to_field.items():
            c = (r.get(fld) or "").strip()
            if c:
                internal_comment[(n(loc), st)] = c

    external_comment = {}
    for r in wb.sheet2:
        pid = (r.get("_parent_id") or "").strip()
        loc = id_to_loc.get(pid, "")
        desc = (r.get("description_of_collectable_item_external") or "").strip()
        c = (r.get("comments_othercollectable_external") or "").strip()
        if loc and desc and c:
            external_comment[(n(loc), n(desc))] = c

    assets_by_section = defaultdict(list)
    for r in wb.sheet3:
        at = (r.get("asset_type") or "").strip()
        loc = (r.get("location_repeat") or "").strip()
        desc_comment = (r.get("descriptioncomments") or "").strip()
        subtype = at.split(",", 1)[1].strip() if "," in at else at
        combo = f"{subtype} {(r.get('asset_description') or '').strip()}".strip()
        record = {
            "loc_n": n(loc),
            "sub_n": n(subtype),
            "combo_n": n(combo),
            "comment": desc_comment,
            "asset_type_n": n(at),
        }
        if at.startswith("Electrical,"):
            assets_by_section["electrical"].append(record)
        elif at == "Doors/Windows/Gates, Doors":
            assets_by_section["doors"].append(record)
        elif at == "Doors/Windows/Gates, Gates":
            assets_by_section["gates"].append(record)
        elif at.startswith("HVAC,"):
            assets_by_section["hvac"].append(record)
        elif at.startswith("Plumbing,"):
            assets_by_section["plumbing"].append(record)
        elif at.startswith("Security,"):
            assets_by_section["security"].append(record)
        elif at == "Gas":
            assets_by_section["gas"].append(record)
        elif at == "Defibrillator":
            assets_by_section["defibrillator"].append(record)

    with paths.appendix_b_csv.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    current_section = ""
    header = []
    col_idx = {}
    for i, row in enumerate(rows):
        if not any((c or "").strip() for c in row):
            continue
        first = (row[0] or "").strip()
        non_empty = [c for c in row if (c or "").strip()]
        if first and len(non_empty) == 1 and first.lower() not in {"location", "area"}:
            current_section = first.lower()
            header = []
            col_idx = {}
            continue
        if first.lower() == "location":
            header = row
            col_idx = {h.strip().lower(): idx for idx, h in enumerate(header) if h.strip()}
            continue
        if not header:
            continue

        cidx = None
        for name in ("comment", "comments"):
            if name in col_idx:
                cidx = col_idx[name]
                break
        if cidx is None:
            continue
        if cidx < len(row) and (row[cidx] or "").strip():
            continue

        loc = (row[col_idx["location"]] if "location" in col_idx and col_idx["location"] < len(row) else "").strip()
        subtype = (
            row[col_idx["asset sub-type"]]
            if "asset sub-type" in col_idx and col_idx["asset sub-type"] < len(row)
            else ""
        ).strip()

        comment = ""
        sec = current_section
        if sec == "building internal":
            comment = internal_comment.get((n(loc), n(subtype)), "")
        elif sec == "building external":
            comment = external_comment.get((n(loc), n(subtype)), "")
        elif sec in (
            "electrical",
            "doors",
            "gates / fencing",
            "gas",
            "hvac",
            "plumbing",
            "security",
            "defibrillator",
        ):
            key = "gates" if sec == "gates / fencing" else sec
            candidates = []
            for a in assets_by_section.get(key, []):
                if n(loc) and n(loc) not in a["loc_n"]:
                    continue
                sub_n = n(subtype)
                if sub_n and sub_n not in a["sub_n"] and sub_n not in a["combo_n"]:
                    continue
                if a["comment"]:
                    candidates.append(a["comment"])
            comment = first_non_empty(candidates)

        if comment:
            while len(row) <= cidx:
                row.append("")
            row[cidx] = comment
            rows[i] = row

    with paths.appendix_b_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print(f"Updated {paths.appendix_b_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

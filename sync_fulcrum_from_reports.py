import csv
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


NS = {"ss": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
ET.register_namespace("", NS["ss"])

from fulcrum_report.paths import ProjectPaths

_paths: ProjectPaths | None = None
ROOT: Path
XLSX_PATH: Path
BACKUP_PATH: Path
UNPACK_ROOT: Path
SHEET1: Path
SHEET2: Path
SHEET3: Path
SHEET4: Path
CSV_APPENDIX: Path
CSV_DEFECTS: Path
SHARED_STRINGS: Path


def configure_paths() -> ProjectPaths:
    global _paths, ROOT, XLSX_PATH, BACKUP_PATH, UNPACK_ROOT
    global SHEET1, SHEET2, SHEET3, SHEET4, CSV_APPENDIX, CSV_DEFECTS, SHARED_STRINGS
    _paths = ProjectPaths()
    ROOT = _paths.root
    XLSX_PATH = _paths.fulcrum_xlsx
    BACKUP_PATH = _paths.root / "data" / "Fulcrum Export.backup.xlsx"
    UNPACK_ROOT = _paths.unpack_dir
    SHEET1 = UNPACK_ROOT / "xl" / "worksheets" / "sheet1.xml"
    SHEET2 = UNPACK_ROOT / "xl" / "worksheets" / "sheet2.xml"
    SHEET3 = UNPACK_ROOT / "xl" / "worksheets" / "sheet3.xml"
    SHEET4 = UNPACK_ROOT / "xl" / "worksheets" / "sheet4.xml"
    CSV_APPENDIX = _paths.appendix_b_csv
    CSV_DEFECTS = _paths.table_defects_refined
    SHARED_STRINGS = UNPACK_ROOT / "xl" / "sharedStrings.xml"
    return _paths


def n(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def yn(text: str) -> str:
    t = (text or "").strip().lower()
    if t in {"y", "yes", "true"}:
        return "yes"
    if t in {"n", "no", "false"}:
        return "no"
    return (text or "").strip()


def col_letters(cell_ref: str) -> str:
    m = re.match(r"([A-Z]+)", cell_ref or "")
    return m.group(1) if m else ""


def col_to_num(col: str) -> int:
    out = 0
    for ch in col:
        out = out * 26 + (ord(ch) - ord("A") + 1)
    return out


def num_to_col(num: int) -> str:
    out = []
    n0 = num
    while n0 > 0:
        n0, r = divmod(n0 - 1, 26)
        out.append(chr(ord("A") + r))
    return "".join(reversed(out))


class SheetEditor:
    def __init__(self, path: Path, shared_strings: list[str]):
        self.path = path
        self.shared_strings = shared_strings
        self.tree = ET.parse(path)
        self.root = self.tree.getroot()
        self.sheet_data = self.root.find("ss:sheetData", NS)
        if self.sheet_data is None:
            raise RuntimeError(f"No sheetData in {path}")
        self.rows = self.sheet_data.findall("ss:row", NS)
        if not self.rows:
            raise RuntimeError(f"No rows in {path}")
        self.header_cols = self._header_cols()
        self.header_to_col = {h: c for c, h in self.header_cols.items()}

    def _header_cols(self) -> dict[str, str]:
        out: dict[str, str] = {}
        header_row = self.rows[0]
        for c in header_row.findall("ss:c", NS):
            col = col_letters(c.attrib.get("r", ""))
            val = self.cell_text(c)
            if col and val:
                out[col] = val.strip()
        return out

    def cell_text(self, cell: ET.Element) -> str:
        t = cell.attrib.get("t")
        if t == "s":
            v = cell.find("ss:v", NS)
            if v is not None and (v.text or "").strip().isdigit():
                idx = int(v.text)
                if 0 <= idx < len(self.shared_strings):
                    return self.shared_strings[idx]
            return ""
        if t == "inlineStr":
            tnode = cell.find("ss:is/ss:t", NS)
            return (tnode.text or "") if tnode is not None else ""
        v = cell.find("ss:v", NS)
        return (v.text or "") if v is not None else ""

    def _row_number(self, row: ET.Element, fallback_idx: int) -> int:
        r = row.attrib.get("r")
        if r and r.isdigit():
            return int(r)
        return fallback_idx + 1

    def row_dict(self, row: ET.Element) -> dict[str, str]:
        vals: dict[str, str] = {}
        for c in row.findall("ss:c", NS):
            col = col_letters(c.attrib.get("r", ""))
            hdr = self.header_cols.get(col)
            if hdr:
                vals[hdr] = self.cell_text(c).strip()
        return vals

    def data_rows(self):
        for i, row in enumerate(self.rows[1:], start=1):
            yield i, row, self.row_dict(row)

    def _get_cell(self, row: ET.Element, col: str, row_num: int) -> ET.Element:
        target_ref = f"{col}{row_num}"
        for c in row.findall("ss:c", NS):
            if col_letters(c.attrib.get("r", "")) == col:
                return c
        new_cell = ET.Element(f"{{{NS['ss']}}}c", {"r": target_ref})
        inserted = False
        target_num = col_to_num(col)
        cells = row.findall("ss:c", NS)
        for idx, c in enumerate(cells):
            ccol = col_letters(c.attrib.get("r", ""))
            if ccol and col_to_num(ccol) > target_num:
                row.insert(idx, new_cell)
                inserted = True
                break
        if not inserted:
            row.append(new_cell)
        return new_cell

    def set_value(self, row: ET.Element, row_num: int, header: str, value: str) -> bool:
        col = self.header_to_col.get(header)
        if not col:
            return False
        cell = self._get_cell(row, col, row_num)
        old_val = self.cell_text(cell).strip()
        new_val = (value or "").strip()
        if old_val == new_val:
            return False

        # Clear children and set as inline string or numeric.
        for child in list(cell):
            cell.remove(child)
        if new_val == "":
            cell.attrib.pop("t", None)
            return True

        if re.fullmatch(r"-?\d+(\.\d+)?", new_val):
            cell.attrib.pop("t", None)
            v = ET.SubElement(cell, f"{{{NS['ss']}}}v")
            v.text = new_val
            return True

        cell.attrib["t"] = "inlineStr"
        is_node = ET.SubElement(cell, f"{{{NS['ss']}}}is")
        t_node = ET.SubElement(is_node, f"{{{NS['ss']}}}t")
        t_node.text = new_val
        return True

    def save(self) -> None:
        self.tree.write(self.path, encoding="utf-8", xml_declaration=True)


def parse_appendix_sections(path: Path) -> list[tuple[str, list[dict[str, str]]]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    sections: list[tuple[str, list[dict[str, str]]]] = []
    sec_name = ""
    headers: list[str] = []
    data: list[dict[str, str]] = []

    def flush():
        nonlocal data
        if sec_name and data:
            sections.append((sec_name, data))
        data = []

    for row in rows:
        vals = [c.strip() for c in row]
        non_empty = [c for c in vals if c]
        if not non_empty:
            continue
        if len(non_empty) == 1 and non_empty[0].lower() not in {"location", "area"}:
            flush()
            sec_name = non_empty[0]
            headers = []
            continue
        if vals and vals[0].strip().lower() in {"location", "area"}:
            headers = [h.strip() for h in vals]
            continue
        if not headers:
            continue
        rec = {}
        for i, h in enumerate(headers):
            if not h:
                continue
            rec[h] = vals[i] if i < len(vals) else ""
        if any((v or "").strip() for v in rec.values()):
            data.append(rec)
    flush()
    return sections


def load_shared_strings(path: Path) -> list[str]:
    root = ET.parse(path).getroot()
    out: list[str] = []
    for si in root.findall("ss:si", NS):
        t = si.find("ss:t", NS)
        if t is not None and t.text is not None:
            out.append(t.text)
            continue
        parts: list[str] = []
        for r in si.findall("ss:r", NS):
            rt = r.find("ss:t", NS)
            if rt is not None and rt.text is not None:
                parts.append(rt.text)
        out.append("".join(parts))
    return out


def build_sheet1_index(sheet1: SheetEditor) -> dict[str, tuple[int, ET.Element, dict[str, str]]]:
    out = {}
    for i, row, rec in sheet1.data_rows():
        loc = n(rec.get("location", ""))
        if loc:
            out[loc] = (i, row, rec)
    return out


def build_sheet2_index(sheet2: SheetEditor) -> dict[tuple[str, str], tuple[int, ET.Element, dict[str, str]]]:
    out = {}
    for i, row, rec in sheet2.data_rows():
        k = (n(rec.get("_parent_id", "")), n(rec.get("description_of_collectable_item_external", "")))
        if k[0] and k[1]:
            out[k] = (i, row, rec)
    return out


def build_parent_location_map(sheet1: SheetEditor) -> dict[str, str]:
    out = {}
    for _, _, rec in sheet1.data_rows():
        rid = (rec.get("_record_id") or "").strip()
        loc = (rec.get("location") or "").strip()
        if rid and loc:
            out[rid] = loc
    return out


def find_sheet3_match(
    sheet3_rows: list[tuple[int, ET.Element, dict[str, str]]],
    location: str,
    subtype: str,
    section: str,
    row_data: dict[str, str],
) -> tuple[int, ET.Element, dict[str, str]] | None:
    loc_n = n(location)
    sub_n = n(subtype)
    sec = n(section)

    def sec_ok(asset_type: str) -> bool:
        at = (asset_type or "").lower()
        if sec == "doors":
            return at == "doors/windows/gates, doors"
        if sec == "gates / fencing":
            return at == "doors/windows/gates, gates"
        if sec == "electrical":
            return at.startswith("electrical,")
        if sec == "fire":
            return at.startswith("fire,")
        if sec == "hvac":
            return at.startswith("hvac,")
        if sec == "plumbing":
            return at.startswith("plumbing,")
        if sec == "security":
            return at.startswith("security,")
        if sec == "defibrillator":
            return at == "defibrillator"
        return False

    candidates = []
    for item in sheet3_rows:
        _, _, rec = item
        if loc_n and n(rec.get("location_repeat", "")) != loc_n:
            continue
        at = rec.get("asset_type", "")
        if not sec_ok(at):
            continue
        sub = at.split(",", 1)[1].strip() if "," in at else at
        hay = " ".join(
            [
                n(sub),
                n(rec.get("asset_description", "")),
                n(rec.get("door_type", "")),
                n(rec.get("gate_type", "")),
            ]
        ).strip()
        if sub_n and sub_n not in hay:
            continue
        candidates.append(item)

    if len(candidates) == 1:
        return candidates[0]

    # Tie-break using door/gate type if provided.
    dt = n(row_data.get("Door Type", ""))
    gt = n(row_data.get("Gate/Fencing Type", ""))
    if dt:
        picks = [c for c in candidates if dt in n(c[2].get("door_type", ""))]
        if len(picks) == 1:
            return picks[0]
    if gt:
        picks = [c for c in candidates if gt in n(c[2].get("gate_type", ""))]
        if len(picks) == 1:
            return picks[0]
    return candidates[0] if candidates else None


def extract_photo_ids(text: str) -> set[str]:
    raw = (text or "").strip()
    if not raw:
        return set()
    ids = set()
    for part in [x.strip() for x in raw.split(",") if x.strip()]:
        m = re.search(r"[?&]id=([a-f0-9\\-]+)", part, re.I)
        if m:
            ids.add(m.group(1).lower())
            continue
        # also allow direct id strings
        if re.fullmatch(r"[a-f0-9\\-]{20,}", part, re.I):
            ids.add(part.lower())
    return ids


def sync_appendix(sheet1: SheetEditor, sheet2: SheetEditor, sheet3: SheetEditor) -> dict[str, int]:
    counts = {"sheet1": 0, "sheet2": 0, "sheet3": 0}
    sections = parse_appendix_sections(CSV_APPENDIX)

    s1_by_loc = build_sheet1_index(sheet1)
    parent_loc_map = build_parent_location_map(sheet1)
    parent_by_loc = {n(v): k for k, v in parent_loc_map.items()}
    s2_idx = build_sheet2_index(sheet2)
    s3_rows = list(sheet3.data_rows())

    s1_map = {
        "floor": ("type_of_flooring", "condition_floor", "quantity_floor", "comments_floor"),
        "walls": ("type_of_walls", "condition_wall", "quantity_walls", "comments_walls"),
        "ceiling": ("", "condition_ceiling", "quantity_ceiling", "comments_ceiling"),
        "lights": ("type_of_light_fitting", "condition_lights", "quantity_lights", "comments_lights"),
        "joinery": ("type_of_joinery", "condition_joinery", "", "comments_joinery"),
    }

    for sec_name, rows in sections:
        sec_n = n(sec_name)
        for r in rows:
            loc = (r.get("Location") or "").strip()
            subtype = (r.get("Asset Sub-Type") or "").strip()
            cond = (r.get("Condition") or "").strip()
            qty = (r.get("Quantity") or "").strip()
            cmt = (r.get("Comment") or r.get("Comments") or "").strip()

            if sec_n == "building internal":
                key = n(subtype)
                if key not in s1_map:
                    continue
                rec = s1_by_loc.get(n(loc))
                if not rec:
                    continue
                i, row, _ = rec
                row_num = i + 1
                type_h, cond_h, qty_h, cmt_h = s1_map[key]

                type_material = (r.get("Type/Material") or "").strip()
                if key == "joinery" and type_material:
                    if "/" in type_material:
                        j1, j2 = [x.strip() for x in type_material.split("/", 1)]
                        if sheet1.set_value(row, row_num, "type_of_joinery", j1):
                            counts["sheet1"] += 1
                        if sheet1.set_value(row, row_num, "type_of_benchtop", j2):
                            counts["sheet1"] += 1
                    else:
                        if sheet1.set_value(row, row_num, "type_of_joinery", type_material):
                            counts["sheet1"] += 1
                elif type_h and type_material:
                    if sheet1.set_value(row, row_num, type_h, type_material):
                        counts["sheet1"] += 1
                if cond_h and cond:
                    if sheet1.set_value(row, row_num, cond_h, cond):
                        counts["sheet1"] += 1
                if qty_h and qty:
                    if sheet1.set_value(row, row_num, qty_h, qty):
                        counts["sheet1"] += 1
                if cmt_h:
                    if sheet1.set_value(row, row_num, cmt_h, cmt):
                        counts["sheet1"] += 1
                continue

            if sec_n == "building external":
                pid = parent_by_loc.get(n(loc), "")
                if not pid:
                    continue
                rec = s2_idx.get((n(pid), n(subtype)))
                if not rec:
                    continue
                i, row, _ = rec
                row_num = i + 1
                if cond:
                    if sheet2.set_value(row, row_num, "condition_othercollectable_external", cond):
                        counts["sheet2"] += 1
                if sheet2.set_value(row, row_num, "comments_othercollectable_external", cmt):
                    counts["sheet2"] += 1
                continue

            if sec_n in {"doors", "electrical", "fire", "gates / fencing", "hvac", "plumbing", "security", "defibrillator"}:
                rec = find_sheet3_match(s3_rows, loc, subtype, sec_name, r)
                if not rec:
                    continue
                i, row, _ = rec
                row_num = i + 1

                if sec_n == "doors":
                    pairs = [
                        ("door_type", r.get("Door Type", "")),
                        ("door_frame_type", r.get("Door Frame Type", "")),
                        ("condition_asset", cond),
                        ("door_closer", yn(r.get("Door Closer", ""))),
                        ("door_jams_fitted", yn(r.get("Door Jams Fitted", ""))),
                        ("door_is_compliant", yn(r.get("Door is Compliant", ""))),
                        ("do_they_lock_doors", yn(r.get("Lockable", ""))),
                    ]
                elif sec_n == "gates / fencing":
                    pairs = [
                        ("gate_type", r.get("Gate/Fencing Type", "")),
                        ("condition_asset", cond),
                        ("descriptioncomments", cmt),
                    ]
                else:
                    pairs = [
                        ("condition_asset", cond),
                        ("last_test_result", r.get("Last Test Result", "")),
                        ("last_test_date", r.get("Last Test Date", "")),
                        ("descriptioncomments", cmt),
                    ]
                for hdr, val in pairs:
                    v = (val or "").strip()
                    if v or hdr in {"descriptioncomments"}:
                        if sheet3.set_value(row, row_num, hdr, v):
                            counts["sheet3"] += 1
                continue

    return counts


def sync_defects(sheet4: SheetEditor) -> int:
    updates = 0
    with CSV_DEFECTS.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    sheet_rows = list(sheet4.data_rows())
    used = set()
    for csv_row in rows:
        loc = (csv_row.get("Location") or "").strip()
        at = (csv_row.get("Asset Type") or "").strip()
        defect_desc = (csv_row.get("Defect Description") or "").strip()
        repair_desc = (csv_row.get("Repair Description") or "").strip()
        if not defect_desc and not repair_desc:
            defect_desc = (csv_row.get("Defect / Repair Description") or "").strip()
        timeframe = (csv_row.get("Timeframe") or "").strip()
        photos = extract_photo_ids(csv_row.get("Photo Reference", ""))
        full_desc = defect_desc if not timeframe else f"{defect_desc} ({timeframe})"

        candidates = []
        for i, row, rec in sheet_rows:
            if i in used:
                continue
            if n(rec.get("location_defect", "")) != n(loc):
                continue
            if n(rec.get("asset_type_defects", "")) != n(at):
                continue
            row_ids = extract_photo_ids(rec.get("photos_defects_urls", "")) | extract_photo_ids(rec.get("photos_defects", ""))
            if photos and row_ids and photos.isdisjoint(row_ids):
                continue
            candidates.append((i, row, rec))

        if not candidates:
            continue
        i, row, _ = candidates[0]
        used.add(i)
        row_num = i + 1
        if sheet4.set_value(row, row_num, "asset_type_defects", at):
            updates += 1
        if "defect_description" in sheet4.header_to_col:
            if sheet4.set_value(row, row_num, "defect_description", defect_desc):
                updates += 1
            if sheet4.set_value(row, row_num, "repair_description", repair_desc):
                updates += 1
        elif sheet4.set_value(row, row_num, "defect_repair_description", full_desc):
            updates += 1
        if sheet4.set_value(row, row_num, "location_defect", loc):
            updates += 1
    return updates


def repack_xlsx(unpack_root: Path, out_xlsx: Path) -> None:
    tmp = out_xlsx.with_suffix(".tmp.xlsx")
    if tmp.exists():
        tmp.unlink()
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in unpack_root.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(unpack_root).as_posix())
    if out_xlsx.exists():
        out_xlsx.unlink()
    tmp.replace(out_xlsx)


def main() -> int:
    configure_paths()
    if not XLSX_PATH.exists():
        raise RuntimeError("Fulcrum Export.xlsx not found.")
    shutil.copy2(XLSX_PATH, BACKUP_PATH)

    shared = load_shared_strings(SHARED_STRINGS)
    s1 = SheetEditor(SHEET1, shared)
    s2 = SheetEditor(SHEET2, shared)
    s3 = SheetEditor(SHEET3, shared)
    s4 = SheetEditor(SHEET4, shared)

    appendix_counts = sync_appendix(s1, s2, s3)
    defect_updates = sync_defects(s4)

    s1.save()
    s2.save()
    s3.save()
    s4.save()
    repack_xlsx(UNPACK_ROOT, XLSX_PATH)

    print(
        f"Updated cells -> sheet1: {appendix_counts['sheet1']}, "
        f"sheet2: {appendix_counts['sheet2']}, sheet3: {appendix_counts['sheet3']}, "
        f"sheet4: {defect_updates}"
    )
    print(f"Backup written: {BACKUP_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


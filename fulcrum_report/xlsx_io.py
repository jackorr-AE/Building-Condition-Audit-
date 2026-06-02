import re
import shutil
import zipfile
from pathlib import Path

import xml.etree.ElementTree as ET

NS = {"ss": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def col_letters(cell_ref: str) -> str:
    m = re.match(r"([A-Z]+)", cell_ref or "")
    return m.group(1) if m else ""


def load_shared_strings(shared_strings_xml_path: str | Path) -> list[str]:
    root = ET.parse(shared_strings_xml_path).getroot()
    strings: list[str] = []
    for si in root.findall("ss:si", NS):
        t = si.find("ss:t", NS)
        if t is not None and t.text is not None:
            strings.append(t.text)
            continue
        parts: list[str] = []
        for r in si.findall("ss:r", NS):
            rt = r.find("ss:t", NS)
            if rt is not None and rt.text is not None:
                parts.append(rt.text)
        strings.append("".join(parts))
    return strings


def parse_sheet_as_rows(sheet_xml_path: str | Path, shared_strings: list[str]) -> list[dict[str, str]]:
    root = ET.parse(sheet_xml_path).getroot()
    sheet_data = root.find("ss:sheetData", NS)
    if sheet_data is None:
        return []

    grid: list[dict[str, str]] = []
    for row in sheet_data.findall("ss:row", NS):
        row_vals: dict[str, str] = {}
        for c in row.findall("ss:c", NS):
            col = col_letters(c.attrib.get("r", ""))
            t = c.attrib.get("t")
            v = c.find("ss:v", NS)
            if v is None or v.text is None:
                continue
            raw = v.text
            if t == "s":
                try:
                    row_vals[col] = shared_strings[int(raw)]
                except Exception:
                    row_vals[col] = ""
            else:
                row_vals[col] = raw
        grid.append(row_vals)

    if not grid:
        return []

    header_row = grid[0]
    col_to_header = {
        col: header_row[col].strip()
        for col in header_row
        if header_row[col].strip()
    }

    out: list[dict[str, str]] = []
    for data_row in grid[1:]:
        record = {header: data_row.get(col, "").strip() for col, header in col_to_header.items()}
        out.append(record)
    return out


def _sheet_kind(headers: set[str]) -> str | None:
    if "location" in headers and "condition_floor" in headers:
        return "general"
    if "description_of_collectable_item_external" in headers:
        return "additional_external"
    if "asset_type" in headers and "condition_asset" in headers:
        return "assets"
    if "location_defect" in headers or "asset_type_defects" in headers:
        return "defects"
    return None


def defect_repair_text(row: dict[str, str]) -> str:
    """Single defect_repair_description field, or defect + repair split fields."""
    combined = (row.get("defect_repair_description") or "").strip()
    if combined:
        return combined
    defect = (row.get("defect_description") or "").strip()
    repair = (row.get("repair_description") or "").strip()
    if defect and repair:
        return f"{defect} {repair}"
    return defect or repair


class FulcrumWorkbook:
    """Load Fulcrum export sheets from unpacked xlsx XML (auto-detected by headers)."""

    def __init__(self, unpack_xl_dir: Path):
        self.xl_dir = unpack_xl_dir
        self.shared = load_shared_strings(unpack_xl_dir / "sharedStrings.xml")
        ws = unpack_xl_dir / "worksheets"
        by_kind: dict[str, list[dict[str, str]]] = {
            "general": [],
            "additional_external": [],
            "assets": [],
            "defects": [],
        }
        for sheet_path in sorted(ws.glob("sheet*.xml"), key=lambda p: int(p.stem[5:])):
            rows = parse_sheet_as_rows(sheet_path, self.shared)
            if not rows:
                continue
            kind = _sheet_kind(set(rows[0].keys()))
            if kind:
                by_kind[kind] = rows
        self.sheet1 = by_kind["general"]
        self.sheet2 = by_kind["additional_external"]
        self.sheet3 = by_kind["assets"]
        self.sheet4 = by_kind["defects"]

    @classmethod
    def from_project(cls, paths) -> "FulcrumWorkbook":
        paths.ensure_unpack()
        return cls(paths.unpack_xl)


def unpack_xlsx(xlsx_path: Path, unpack_dir: Path) -> None:
    if unpack_dir.exists():
        shutil.rmtree(unpack_dir)
    unpack_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(xlsx_path, "r") as zf:
        zf.extractall(unpack_dir)


def needs_unpack(xlsx_path: Path, unpack_dir: Path) -> bool:
    xl = unpack_dir / "xl" / "sharedStrings.xml"
    if not xl.exists():
        return True
    if not xlsx_path.exists():
        return False
    return xlsx_path.stat().st_mtime > xl.stat().st_mtime

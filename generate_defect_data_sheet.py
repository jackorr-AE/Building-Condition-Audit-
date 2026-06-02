import csv
import html
import re
from pathlib import Path

from PIL import Image, ImageOps

from fulcrum_report.branding import appendix_page_header_html, file_data_uri, logo_data_uri
from fulcrum_report.pdf_print import print_html_to_pdf
from fulcrum_report.paths import ProjectPaths

REPORT_TITLE = "Appendix - Defects Register"
JPEG_QUALITY = 18
MAX_IMAGE_WIDTH = 900
MAX_IMAGE_HEIGHT = 700


def split_photo_urls(photo_ref: str) -> list[str]:
    text = (photo_ref or "").strip()
    if not text:
        return []
    return [p.strip() for p in text.split(",") if p.strip()]


def extract_photo_ids(photo_ref: str) -> list[str]:
    """Return lookup keys from photo refs: Fulcrum UUIDs and local filename stems."""
    ids: list[str] = []
    for part in split_photo_urls(photo_ref):
        m = re.search(r"\bid=([0-9a-fA-F-]{36})\b", part)
        if m:
            ids.append(m.group(1))
            continue
        if re.fullmatch(r"[0-9a-fA-F-]{36}", part, flags=re.IGNORECASE):
            ids.append(part)
            continue
        stem = Path(part.replace("\\", "/").split("/")[-1]).stem.strip()
        if stem:
            ids.append(stem)
    out: list[str] = []
    seen: set[str] = set()
    for i in ids:
        key = i.lower()
        if key not in seen:
            out.append(i)
            seen.add(key)
    return out


def resolve_local_photo_filename(photo_id: str, photo_source_dir: Path) -> str | None:
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = photo_source_dir / f"{photo_id}{ext}"
        if p.exists():
            return p.name
    target = photo_id.lower()
    for p in photo_source_dir.iterdir():
        if not p.is_file() or p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        if p.stem.lower() == target:
            return p.name
    return None


def compress_photo(source_name: str, photo_source_dir: Path, photo_output_dir: Path) -> Path | None:
    src = photo_source_dir / source_name
    if not src.exists():
        return None
    photo_output_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"{Path(source_name).stem}_q{JPEG_QUALITY}_oriented.jpg"
    out_path = photo_output_dir / out_name
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGB")
            im.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.Resampling.LANCZOS)
            im.save(out_path, format="JPEG", optimize=True, quality=JPEG_QUALITY, progressive=True)
        return out_path
    except Exception:
        return None


def photo_src_for_html(photo_path: Path | None) -> str | None:
    return file_data_uri(photo_path)


def main() -> int:
    paths = ProjectPaths()
    paths.defect_photos_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    with paths.table_defects_refined.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            resolved: list[str] = []
            for pid in extract_photo_ids(row.get("Photo Reference", ""))[:2]:
                fn = resolve_local_photo_filename(pid, paths.photos_dir)
                if not fn:
                    continue
                out_path = compress_photo(fn, paths.photos_dir, paths.defect_photos_dir)
                if not out_path or not out_path.exists():
                    out_path = paths.photos_dir / fn
                src = photo_src_for_html(out_path)
                if src:
                    resolved.append(src)
            row["_photos"] = "|".join(resolved)
            rows.append(row)

    left_logo_src = logo_data_uri(paths.logo_left)
    right_logo_src = logo_data_uri(paths.logo_right)

    html_rows: list[str] = []
    for r in rows:
        photos = [p for p in (r.get("_photos", "") or "").split("|") if p]
        if photos:
            imgs = "".join(
                f'<img src="{p}" alt="Defect photo" class="defect-photo" />'
                for p in photos[:2]
            )
            photo_cell = f'<div class="photo-wrap">{imgs}</div>'
        else:
            photo_cell = '<div class="photo-wrap na">N/A</div>'

        defect_desc = (r.get("Defect Description") or r.get("Defect / Repair Description") or "").strip()
        repair_desc = (r.get("Repair Description") or "").strip()
        html_rows.append(
            "<tr>"
            f"<td>{html.escape((r.get('Area') or '').strip())}</td>"
            f"<td>{html.escape((r.get('Location') or '').strip())}</td>"
            f"<td>{html.escape((r.get('Asset Type') or '').strip())}</td>"
            f"<td>{html.escape(defect_desc)}</td>"
            f"<td>{html.escape(repair_desc)}</td>"
            f"<td>{html.escape((r.get('Timeframe') or '').strip())}</td>"
            f"<td class='photo-col'>{photo_cell}</td>"
            "</tr>"
        )

    header_html = appendix_page_header_html(
        left_logo_src=left_logo_src,
        title=REPORT_TITLE,
        right_logo_src=right_logo_src,
    )

    html_doc = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{html.escape(REPORT_TITLE)}</title>
  <style>
    @page {{
      size: A4 landscape;
      margin: 12mm 10mm 12mm 10mm;
    }}
    body {{
      font-family: Arial, Helvetica, sans-serif;
      margin: 0;
      color: #111;
    }}
    .appendix-header {{
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      align-items: center;
      width: 100%;
      margin: 0 0 6px 0;
      min-height: 48px;
    }}
    .appendix-header img {{
      height: 42px;
      max-width: 100%;
      object-fit: contain;
    }}
    .appendix-header .left {{ justify-self: start; }}
    .appendix-header .right {{ justify-self: end; }}
    .appendix-header .spacer {{ width: 1px; height: 42px; }}
    .appendix-header .title {{
      justify-self: center;
      text-align: center;
      font-weight: 700;
      font-size: 14pt;
      color: #005b2e;
      padding: 0 8px;
      line-height: 1.2;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      font-size: 11px;
    }}
    thead {{
      display: table-header-group;
    }}
    th, td {{
      border: 1px solid #7c8f8d;
      padding: 5px 6px;
      vertical-align: top;
      overflow-wrap: break-word;
      word-break: normal;
      box-sizing: border-box;
    }}
    tr {{
      page-break-inside: avoid;
      break-inside: avoid;
    }}
    tbody tr {{
      page-break-inside: avoid;
      break-inside: avoid;
    }}
    .meta-header-cell {{
      border: none;
      padding: 0 0 6px 0;
    }}
    tr.column-headers th {{
      background: #005b2e;
      color: #fff;
      text-align: left;
      font-weight: 700;
      white-space: normal;
      line-height: 1.15;
      font-size: 9pt;
      padding: 4px 3px;
    }}
    .photo-col {{
      padding: 0;
    }}
    .photo-wrap {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 4px;
      align-items: stretch;
      min-height: 140px;
      padding: 4px;
      box-sizing: border-box;
    }}
    .photo-wrap.na {{
      display: flex;
      align-items: center;
      justify-content: center;
      color: #666;
      font-style: italic;
    }}
    .defect-photo {{
      width: 100%;
      height: 150px;
      object-fit: cover;
      border: 0;
      display: block;
    }}
    @media print {{
      .defect-photo {{ height: 135px; }}
    }}
  </style>
</head>
<body>
  <table>
    <colgroup>
      <col style="width:10%">
      <col style="width:9%">
      <col style="width:12%">
      <col style="width:20%">
      <col style="width:20%">
      <col style="width:9%">
      <col style="width:20%">
    </colgroup>
    <thead>
      <tr>
        <td colspan="7" class="meta-header-cell">
          {header_html}
        </td>
      </tr>
      <tr class="column-headers">
        <th>Area</th>
        <th>Location</th>
        <th>Asset Type</th>
        <th>Defect Description</th>
        <th>Repair Description</th>
        <th>Timeframe</th>
        <th>Representative Photo</th>
      </tr>
    </thead>
    <tbody>
      {''.join(html_rows)}
    </tbody>
  </table>
</body>
</html>
"""

    paths.defect_list_html.parent.mkdir(parents=True, exist_ok=True)
    paths.defect_list_html.write_text(html_doc, encoding="utf-8")
    print_html_to_pdf(paths.defect_list_html, paths.defect_list_pdf, landscape=True)
    print(f"Wrote {paths.defect_list_html} and {paths.defect_list_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

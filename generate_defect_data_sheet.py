import csv
import html
import os
import re
from pathlib import Path

from PIL import Image, ImageOps


from fulcrum_report.branding import logo_rel, page_header_html
from fulcrum_report.paths import ProjectPaths
CAPTION_TEXT = "Defects Register"
JPEG_QUALITY = 18
MAX_IMAGE_WIDTH = 900
MAX_IMAGE_HEIGHT = 700


def split_photo_urls(photo_ref: str) -> list[str]:
    text = (photo_ref or "").strip()
    if not text:
        return []
    return [p.strip() for p in text.split(",") if p.strip()]


def extract_photo_ids(photo_ref: str) -> list[str]:
    ids: list[str] = []
    for part in split_photo_urls(photo_ref):
        m = re.search(r"\bid=([0-9a-fA-F-]{36})\b", part)
        if m:
            ids.append(m.group(1))
            continue
        if re.fullmatch(r"[0-9a-fA-F-]{36}", part):
            ids.append(part)
    out: list[str] = []
    seen: set[str] = set()
    for i in ids:
        if i not in seen:
            out.append(i)
            seen.add(i)
    return out


def resolve_local_photo_filename(photo_id: str, photo_source_dir: Path) -> str | None:
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = photo_source_dir / f"{photo_id}{ext}"
        if p.exists():
            return p.name
    return None


def compress_photo(source_name: str, photo_source_dir: Path, photo_output_dir: Path) -> str | None:
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
        return out_name
    except Exception:
        return None


def main() -> int:
    paths = ProjectPaths()
    paths.defect_photos_dir.mkdir(parents=True, exist_ok=True)
    photo_output_rel = os.path.relpath(paths.defect_photos_dir, paths.root).replace("\\", "/")
    photo_source_rel = os.path.relpath(paths.photos_dir, paths.root).replace("\\", "/")

    rows: list[dict[str, str]] = []
    with paths.table_defects_refined.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            resolved: list[str] = []
            for pid in extract_photo_ids(row.get("Photo Reference", ""))[:2]:
                fn = resolve_local_photo_filename(pid, paths.photos_dir)
                if fn:
                    compressed = compress_photo(fn, paths.photos_dir, paths.defect_photos_dir)
                    if compressed:
                        resolved.append(f"{photo_output_rel}/{compressed}")
                    else:
                        resolved.append(f"{photo_source_rel}/{fn}")
            row["_photos"] = "|".join(resolved)
            rows.append(row)

    left_logo_rel = logo_rel(paths.logo_left, paths.root)
    right_logo_rel = logo_rel(paths.logo_right, paths.root)

    html_rows: list[str] = []
    for r in rows:
        photos = [p for p in (r.get("_photos", "") or "").split("|") if p]
        if photos:
            imgs = "".join(
                f'<img src="{html.escape(p)}" alt="Defect photo" class="defect-photo" />'
                for p in photos[:2]
            )
            photo_cell = f'<div class="photo-wrap">{imgs}</div>'
        else:
            photo_cell = '<div class="photo-wrap na">N/A</div>'

        html_rows.append(
            "<tr>"
            f"<td>{html.escape((r.get('Area') or '').strip())}</td>"
            f"<td>{html.escape((r.get('Location') or '').strip())}</td>"
            f"<td>{html.escape((r.get('Asset Type') or '').strip())}</td>"
            f"<td>{html.escape((r.get('Defect / Repair Description') or '').strip())}</td>"
            f"<td>{html.escape((r.get('Timeframe') or '').strip())}</td>"
            f"<td class='photo-col'>{photo_cell}</td>"
            "</tr>"
        )

    html_doc = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{html.escape(CAPTION_TEXT)}</title>
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
    .page-header {{
      width: 100%;
      align-items: center;
      margin: 0 0 6px 0;
    }}
    .page-header-dual {{
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
    }}
    .page-header-single {{
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 12px;
    }}
    .page-header-title-only {{ display: block; }}
    .page-header img {{
      height: 48px;
      object-fit: contain;
    }}
    .page-header-dual .left {{ justify-self: start; }}
    .page-header-dual .right {{ justify-self: end; }}
    .page-header-single .left {{ justify-self: start; }}
    .page-header .title {{
      font-weight: 700;
      font-size: 15pt;
      color: #005b2e;
      transform: translateY(-2px);
    }}
    .page-header-dual .title {{
      justify-self: center;
      text-align: center;
    }}
    .page-header-single .title {{
      justify-self: start;
      text-align: left;
    }}
    .page-header-title-only .title {{
      text-align: center;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      font-size: 12px;
    }}
    thead {{
      display: table-header-group;
    }}
    th, td {{
      border: 1px solid #7c8f8d;
      padding: 6px 8px;
      vertical-align: top;
      overflow-wrap: break-word;
      word-break: normal;
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
    th {{
      background: #005b2e;
      color: #fff;
      text-align: left;
      font-weight: 700;
      white-space: nowrap;
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
      <col style="width:12%">
      <col style="width:10%">
      <col style="width:13%">
      <col style="width:23%">
      <col style="width:10%">
      <col style="width:32%">
    </colgroup>
    <thead>
      <tr>
        <td colspan="6" class="meta-header-cell">
          {page_header_html(left_logo_rel=left_logo_rel, right_logo_rel=right_logo_rel, title=CAPTION_TEXT)}
        </td>
      </tr>
      <tr>
        <th>Area</th>
        <th>Location</th>
        <th>Asset Type</th>
        <th>Defect / Repair Description</th>
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
    print(f"Wrote {paths.defect_list_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


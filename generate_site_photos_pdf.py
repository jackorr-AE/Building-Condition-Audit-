import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps

from fulcrum_report.branding import logo_rel, site_photos_topbar_html
from fulcrum_report.paths import ProjectPaths
from fulcrum_report.xlsx_io import FulcrumWorkbook

JPEG_QUALITY = 20
MAX_IMAGE_SIZE = (1400, 1050)
PHOTOS_PER_PAGE = 9


def split_ids(text: str) -> list[str]:
    if not text:
        return []
    return [x.strip() for x in text.split(",") if x.strip()]


def normalize_photo_id(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    raw = raw.replace("\\", "/").split("/")[-1]
    raw = raw.split("?", 1)[0].split("#", 1)[0]
    return Path(raw).stem.strip().lower()


def prettify_photo_field_name(field: str) -> str:
    name = field.replace("photos_", "").replace("_", " ").strip()
    if not name:
        return "Photo"
    return " ".join(w.capitalize() for w in name.split())


def concise_asset_type(asset_type: str) -> str:
    parts = [p.strip() for p in (asset_type or "").split(",")]
    return parts[-1] if parts else asset_type


def build_photo_metadata(wb: FulcrumWorkbook) -> dict[str, str]:
    sheet1 = wb.sheet1
    sheet2 = wb.sheet2
    sheet3 = wb.sheet3
    sheet4 = wb.sheet4

    id_to_loc = {(r.get("_record_id") or "").strip(): (r.get("location") or "").strip() for r in sheet1}
    photo_desc: dict[str, str] = {}

    def put(photo_id: str, desc: str) -> None:
        pid = normalize_photo_id(photo_id)
        if not pid or pid in photo_desc:
            return
        photo_desc[pid] = desc.strip() if desc.strip() else "Site photo"

    # Sheet 1 photos_*
    for r in sheet1:
        loc = (r.get("location") or "").strip()
        for k, v in r.items():
            if not k.startswith("photos_"):
                continue
            if k.endswith("_urls") or k.endswith("_captions"):
                continue
            ids = split_ids(v)
            if not ids:
                continue
            label = prettify_photo_field_name(k)
            desc = ", ".join(x for x in [loc, label] if x)
            for pid in ids:
                put(pid, desc)

    # Sheet 2 external collectables
    for r in sheet2:
        loc = (r.get("location_repeat") or "").strip()
        if not loc:
            loc = id_to_loc.get((r.get("_parent_id") or "").strip(), "")
        item = (r.get("description_of_collectable_item_external") or "").strip()
        ids = split_ids((r.get("photos_othercollectable_external") or "").strip())
        desc = ", ".join(x for x in [loc, item] if x)
        for pid in ids:
            put(pid, desc)

    # Sheet 3 assets
    for r in sheet3:
        loc = (r.get("location_repeat") or "").strip()
        at = concise_asset_type((r.get("asset_type") or "").strip())
        detail = (r.get("asset_description") or "").strip()
        desc = ", ".join(x for x in [loc, at, detail] if x)
        for pid in split_ids((r.get("asset_photos") or "").strip()):
            put(pid, desc)

    # Sheet 4 defects
    for r in sheet4:
        loc = (r.get("location_defect") or "").strip()
        at = (r.get("asset_type_defects") or "").strip()
        desc = ", ".join(x for x in [loc, at] if x)
        for pid in split_ids((r.get("photos_defects") or "").strip()):
            put(pid, desc)

    return photo_desc


def compress_image(src: Path, dst: Path) -> None:
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        im.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
        im.save(dst, format="JPEG", optimize=True, progressive=True, quality=JPEG_QUALITY)


def parse_exif_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def get_taken_datetime(src: Path) -> datetime:
    try:
        with Image.open(src) as im:
            exif = im.getexif()
            dt = parse_exif_datetime(exif.get(36867) or exif.get(306))
            if dt is not None:
                return dt
    except Exception:
        pass
    return datetime.fromtimestamp(src.stat().st_mtime)


def fallback_desc(stem: str) -> str:
    text = re.sub(r"[_\-]+", " ", stem or "").strip()
    text = re.sub(r"\s{2,}", " ", text)
    return text if text else "Site photo"


def chunked(items: list, n: int):
    for i in range(0, len(items), n):
        yield items[i : i + n]


def generate_html(photo_items: list[tuple[str, str]], paths: ProjectPaths) -> str:
    left_logo_rel = logo_rel(paths.logo_left, paths.root)
    right_logo_rel = logo_rel(paths.logo_right, paths.root)
    topbar = site_photos_topbar_html(left_logo_rel, right_logo_rel)
    comp_rel = os.path.relpath(paths.site_photos_dir, paths.root).replace("\\", "/")

    cards = []
    for idx, (filename, desc) in enumerate(photo_items, start=1):
        caption = f"Picture {idx}: {desc}"
        cards.append(
            f"""
            <div class="card">
              <div class="img-wrap"><img src="{comp_rel}/{filename}" alt="{html_escape(caption)}" /></div>
              <div class="cap">{html_escape(caption)}</div>
            </div>
            """
        )

    pages = []
    for group in chunked(cards, PHOTOS_PER_PAGE):
        # Pad to exactly 9 slots for stable layout.
        while len(group) < PHOTOS_PER_PAGE:
            group.append('<div class="card empty"></div>')
        pages.append(
            f"""
            <section class="page">
              {topbar}
              <div class="grid">
                {''.join(group)}
              </div>
            </section>
            """
        )

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Site Photos</title>
  <style>
    @page {{
      size: A4 portrait;
      margin: 10mm;
    }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: #111;
    }}
    .page {{
      height: calc(297mm - 20mm);
      page-break-after: always;
      break-after: page;
      display: flex;
      flex-direction: column;
    }}
    .page:last-child {{
      page-break-after: auto;
      break-after: auto;
    }}
    .topbar {{
      align-items: center;
      margin-bottom: 4mm;
      min-height: 12mm;
    }}
    .topbar-dual {{
      display: grid;
      grid-template-columns: 1fr 1fr;
    }}
    .topbar-single img {{
      height: 10mm;
      object-fit: contain;
      justify-self: start;
    }}
    .topbar-dual img {{
      height: 10mm;
      object-fit: contain;
    }}
    .topbar-dual .logo-left {{ justify-self: start; }}
    .topbar-dual .logo-right {{ justify-self: end; }}
    .topbar-empty {{ min-height: 0; margin-bottom: 2mm; }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      grid-template-rows: repeat(3, 1fr);
      gap: 2.5mm;
      flex: 1;
      min-height: 0;
    }}
    .card {{
      border: 0.2mm solid #9aa9a7;
      display: flex;
      flex-direction: column;
      min-height: 0;
      overflow: hidden;
      background: #fff;
    }}
    .card.empty {{
      border-color: transparent;
      background: transparent;
    }}
    .img-wrap {{
      flex: 1;
      min-height: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #f7f7f7;
    }}
    .img-wrap img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .cap {{
      font-size: 7pt;
      line-height: 1.15;
      padding: 1mm 1.2mm;
      border-top: 0.2mm solid #9aa9a7;
      min-height: 8mm;
      max-height: 11mm;
      overflow: hidden;
    }}
  </style>
</head>
<body>
  {''.join(pages)}
</body>
</html>
"""


def html_escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def print_pdf(html_path: Path, pdf_path: Path) -> None:
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if not chrome.exists():
        chrome = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    if not chrome.exists():
        raise RuntimeError("No Chromium browser found for PDF generation.")

    file_url = "file:///" + str(html_path).replace("\\", "/").replace(" ", "%20")
    cmd = [
        str(chrome),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        file_url,
    ]
    subprocess.run(cmd, check=True)


def main() -> int:
    paths = ProjectPaths()
    if not paths.photos_dir.exists():
        raise RuntimeError(f"photos folder not found: {paths.photos_dir}")
    paths.site_photos_dir.mkdir(parents=True, exist_ok=True)

    wb = FulcrumWorkbook.from_project(paths)
    photo_desc = build_photo_metadata(wb)
    files = sorted(
        [p for p in paths.photos_dir.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}],
        key=lambda x: x.name.lower(),
    )

    prepared: list[tuple[datetime, str, str]] = []
    for p in files:
        dst = paths.site_photos_dir / f"{p.stem}_q{JPEG_QUALITY}.jpg"
        compress_image(p, dst)
        pid = normalize_photo_id(p.name)
        desc = photo_desc.get(pid, fallback_desc(p.stem))
        taken = get_taken_datetime(p)
        prepared.append((taken, dst.name, desc))

    prepared.sort(key=lambda x: (x[0], x[1].lower()))
    ordered = [(name, desc) for _, name, desc in prepared]

    html_doc = generate_html(ordered, paths)
    paths.site_photos_html.parent.mkdir(parents=True, exist_ok=True)
    paths.site_photos_html.write_text(html_doc, encoding="utf-8")
    print_pdf(paths.site_photos_html, paths.site_photos_pdf)
    print(f"Wrote {paths.site_photos_html} and {paths.site_photos_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


import csv
import html
from pathlib import Path

from fulcrum_report.branding import appendix_page_header_html, logo_data_uri, logo_src_for_html
from fulcrum_report.pdf_print import print_html_to_pdf
from fulcrum_report.paths import ProjectPaths


def parse_sections(csv_path: Path) -> list[dict]:
    sections: list[dict] = []
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    i = 0
    while i < len(rows):
        row = rows[i]
        non_empty = [c for c in row if (c or "").strip()]
        if len(non_empty) == 1 and (row[0] or "").strip():
            title = (row[0] or "").strip()
            i += 1
            while i < len(rows) and not any((c or "").strip() for c in rows[i]):
                i += 1
            if i >= len(rows):
                break
            header_raw = rows[i]
            while header_raw and not (header_raw[-1] or "").strip():
                header_raw.pop()
            headers = [h.strip() for h in header_raw if h.strip()]
            i += 1

            data: list[list[str]] = []
            while i < len(rows):
                r = rows[i]
                ne = [c for c in r if (c or "").strip()]
                if len(ne) == 1 and (r[0] or "").strip():
                    break
                if not ne:
                    i += 1
                    continue
                vals = [(r[idx].strip() if idx < len(r) else "") for idx in range(len(headers))]
                data.append(vals)
                i += 1

            if headers and data:
                sections.append({"title": title, "headers": headers, "rows": data})
            continue

        i += 1

    return sections


def col_widths_for_headers(headers: list[str]) -> list[float]:
    weights: list[float] = []
    for h in headers:
        hl = (h or "").strip().lower()
        if hl == "comments":
            weights.append(3.2)
        elif hl in ("location", "type/material"):
            weights.append(2.0)
        elif hl in ("asset sub-type", "type of aircon unit", "type of boiler"):
            weights.append(1.6)
        elif "door" in hl or "last test" in hl or hl == "lockable":
            weights.append(1.35)
        elif hl in ("condition", "quantity", "unit", "barcode no"):
            weights.append(1.0)
        else:
            weights.append(1.2)
    total = sum(weights) or 1.0
    return [w / total * 100.0 for w in weights]


def header_font_size_pt(column_count: int) -> float:
    if column_count <= 6:
        return 9.5
    if column_count <= 8:
        return 8.5
    return 7.5


def build_section_html(
    section: dict,
    left_logo_src: str | None,
    right_logo_src: str | None,
) -> str:
    title = section["title"]
    headers = section["headers"]
    rows = section["rows"]
    widths = col_widths_for_headers(headers)
    ncols = len(headers)
    th_size = header_font_size_pt(ncols)

    colgroup = "".join(f'<col style="width:{w:.3f}%">' for w in widths)
    ths = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    condition_idx = -1
    for idx, h in enumerate(headers):
        if (h or "").strip().lower() == "condition":
            condition_idx = idx
            break

    def condition_class(value: str) -> str:
        v = (value or "").strip().lower()
        if v == "excellent":
            return "cond-excellent"
        if v == "good":
            return "cond-good"
        if v == "fair":
            return "cond-fair"
        if v == "poor":
            return "cond-poor"
        if v == "very poor":
            return "cond-very-poor"
        return ""

    trs = []
    for r in rows:
        cells = []
        for idx, v in enumerate(r):
            classes = []
            if idx == condition_idx:
                classes.append("cond-center")
                c = condition_class(v)
                if c:
                    classes.append(c)
            class_attr = f' class="{" ".join(classes)}"' if classes else ""
            cells.append(f"<td{class_attr}>{html.escape(v)}</td>")
        trs.append(f"<tr>{''.join(cells)}</tr>")

    return f"""
<table class="section-table cols-{ncols}">
  <colgroup>{colgroup}</colgroup>
  <thead>
    <tr>
      <td colspan="{ncols}" class="meta-header-cell">
        {appendix_page_header_html(
            left_logo_src=left_logo_src,
            title=title,
            right_logo_src=right_logo_src,
        )}
      </td>
    </tr>
    <tr class="column-headers">{ths}</tr>
  </thead>
  <tbody>
    {''.join(trs)}
  </tbody>
</table>
"""


def generate_html(
    sections: list[dict],
    html_path: Path,
    logo_left: Path,
    logo_right: Path | None,
    *,
    embed_logos: bool = True,
) -> str:
    if embed_logos:
        left_logo_src = logo_data_uri(logo_left)
        right_logo_src = logo_data_uri(logo_right) if logo_right else None
    else:
        left_logo_src = logo_src_for_html(logo_left, html_path)
        right_logo_src = logo_src_for_html(logo_right, html_path) if logo_right else None

    section_blocks = [
        build_section_html(s, left_logo_src, right_logo_src) for s in sections
    ]

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Appendix - Asset Register</title>
  <style>
    @page {{
      size: A4 landscape;
      margin: 12mm 25.4mm 12mm 25.4mm;
    }}
    body {{
      font-family: Arial, Helvetica, sans-serif;
      margin: 0;
      color: #111;
    }}
    .section-table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      font-size: 11px;
      margin: 0 0 8mm 0;
      page-break-after: always;
    }}
    .section-table:last-of-type {{
      page-break-after: auto;
    }}
    thead {{
      display: table-header-group;
    }}
    tr {{
      page-break-inside: avoid;
      break-inside: avoid;
    }}
    th, td {{
      border: 1px solid #7c8f8d;
      padding: 5px 6px;
      vertical-align: top;
      overflow-wrap: break-word;
      word-break: normal;
      box-sizing: border-box;
    }}
    .cond-center {{
      text-align: center;
      font-weight: 400;
    }}
    .cond-excellent {{ background: #17a2d8; }}
    .cond-good {{ background: #8dc84a; }}
    .cond-fair {{ background: #f3ec00; }}
    .cond-poor {{ background: #f1b400; }}
    .cond-very-poor {{ background: #ef1111; color: #000; }}
    tr.column-headers th {{
      background: #005b2e;
      color: #fff;
      text-align: center;
      font-weight: 700;
      white-space: normal;
      line-height: 1.15;
      overflow: hidden;
      hyphens: auto;
      padding: 4px 3px;
      font-size: 9.5pt;
    }}
    .cols-7 tr.column-headers th {{ font-size: 8.5pt; }}
    .cols-8 tr.column-headers th {{ font-size: 8pt; }}
    .cols-9 tr.column-headers th {{ font-size: 7.5pt; }}
    .cols-10 tr.column-headers th {{ font-size: 7pt; }}
    .cols-11 tr.column-headers th,
    .cols-12 tr.column-headers th {{ font-size: 6.5pt; }}
    .meta-header-cell {{
      border: none;
      padding: 0 0 6px 0;
    }}
    .appendix-header {{
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      align-items: center;
      width: 100%;
      margin: 0 0 4px 0;
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
  </style>
</head>
<body>
  {''.join(section_blocks)}
</body>
</html>
"""


def main() -> int:
    paths = ProjectPaths()
    paths.ensure_unpack()
    sections = parse_sections(paths.appendix_b_csv)
    if not sections:
        raise RuntimeError(f"No non-empty sections found in {paths.appendix_b_csv}")

    paths.appendix_b_html.parent.mkdir(parents=True, exist_ok=True)
    html_doc = generate_html(
        sections,
        paths.appendix_b_html,
        paths.logo_left,
        paths.logo_right,
        embed_logos=True,
    )
    paths.appendix_b_html.write_text(html_doc, encoding="utf-8")
    print_html_to_pdf(paths.appendix_b_html, paths.appendix_b_pdf, landscape=True)
    print(f"Wrote {paths.appendix_b_html} and {paths.appendix_b_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

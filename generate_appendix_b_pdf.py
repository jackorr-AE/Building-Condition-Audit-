import csv
import html
import os
import subprocess
from pathlib import Path

from fulcrum_report.branding import logo_rel, page_header_html
from fulcrum_report.paths import ProjectPaths


def parse_sections(csv_path: Path) -> list[dict]:
    sections: list[dict] = []
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    i = 0
    while i < len(rows):
        row = rows[i]
        non_empty = [c for c in row if (c or "").strip()]
        # Section title row: first cell populated, rest empty
        if len(non_empty) == 1 and (row[0] or "").strip():
            title = (row[0] or "").strip()
            i += 1
            # find header row
            while i < len(rows) and not any((c or "").strip() for c in rows[i]):
                i += 1
            if i >= len(rows):
                break
            header_raw = rows[i]
            # trim trailing empty header cells
            while header_raw and not (header_raw[-1] or "").strip():
                header_raw.pop()
            headers = [h.strip() for h in header_raw if h.strip()]
            i += 1

            data: list[list[str]] = []
            while i < len(rows):
                r = rows[i]
                ne = [c for c in r if (c or "").strip()]
                # next section starts
                if len(ne) == 1 and (r[0] or "").strip():
                    break
                # skip blank separator rows
                if not ne:
                    i += 1
                    continue
                # normalize width to header length
                vals = [(r[idx].strip() if idx < len(r) else "") for idx in range(len(headers))]
                data.append(vals)
                i += 1

            if headers and data:
                sections.append({"title": title, "headers": headers, "rows": data})
            continue

        i += 1

    return sections


def col_widths_for_count(n: int) -> list[float]:
    if n <= 5:
        return [100.0 / n] * n
    if n == 6:
        return [15, 15, 15, 25, 15, 15]
    if n == 7:
        return [14, 14, 14, 18, 14, 13, 13]
    if n == 8:
        return [12, 12, 12, 16, 12, 12, 12, 12]
    if n == 9:
        return [11, 11, 11, 14, 11, 11, 10, 10, 11]
    # fallback
    return [100.0 / n] * n


def build_section_html(section: dict, left_logo_rel: str | None, right_logo_rel: str | None) -> str:
    title = section["title"]
    headers = section["headers"]
    rows = section["rows"]
    widths = col_widths_for_count(len(headers))

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
<table class="section-table">
  <colgroup>{colgroup}</colgroup>
  <thead>
    <tr>
      <td colspan="{len(headers)}" class="meta-header-cell">
        {page_header_html(left_logo_rel=left_logo_rel, right_logo_rel=right_logo_rel, title=title)}
      </td>
    </tr>
    <tr>{ths}</tr>
  </thead>
  <tbody>
    {''.join(trs)}
  </tbody>
</table>
"""


def generate_html(
    sections: list[dict],
    root: Path,
    logo_left: Path,
    logo_right: Path | None,
) -> str:
    left_logo_rel = logo_rel(logo_left, root)
    right_logo_rel = logo_rel(logo_right, root)

    section_blocks = [
        build_section_html(s, left_logo_rel, right_logo_rel) for s in sections
    ]

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Appendix B Asset Register</title>
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
    }}
    .cond-center {{
      text-align: center;
      font-weight: 400;
    }}
    .cond-excellent {{
      background: #17a2d8;
    }}
    .cond-good {{
      background: #8dc84a;
    }}
    .cond-fair {{
      background: #f3ec00;
    }}
    .cond-poor {{
      background: #f1b400;
    }}
    .cond-very-poor {{
      background: #ef1111;
      color: #000;
    }}
    th {{
      background: #005b2e;
      color: #fff;
      text-align: center;
      font-weight: 700;
      white-space: nowrap;
    }}
    .meta-header-cell {{
      border: none;
      padding: 0 0 6px 0;
    }}
    .page-header {{
      width: 100%;
      align-items: center;
      margin: 0 0 4px 0;
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
      height: 42px;
      object-fit: contain;
    }}
    .page-header-dual .left {{ justify-self: start; }}
    .page-header-dual .right {{ justify-self: end; }}
    .page-header-single .left {{ justify-self: start; }}
    .page-header .title {{
      font-weight: 700;
      font-size: 14pt;
      color: #005b2e;
      transform: translateY(-1px);
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
  </style>
</head>
<body>
  {''.join(section_blocks)}
</body>
</html>
"""


def print_pdf(html_path: Path, pdf_path: Path) -> None:
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if not chrome.exists():
        chrome = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    if not chrome.exists():
        raise RuntimeError("No Chromium browser found for PDF printing.")

    file_url = "file:///" + str(html_path).replace("\\", "/").replace(" ", "%20")
    cmd = [
        str(chrome),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--print-to-pdf-landscape",
        f"--print-to-pdf={pdf_path}",
        file_url,
    ]
    subprocess.run(cmd, check=True)


def main() -> int:
    paths = ProjectPaths()
    sections = parse_sections(paths.appendix_b_csv)
    if not sections:
        raise RuntimeError(f"No non-empty sections found in {paths.appendix_b_csv}")

    paths.appendix_b_html.parent.mkdir(parents=True, exist_ok=True)
    html_doc = generate_html(sections, paths.root, paths.logo_left, paths.logo_right)
    paths.appendix_b_html.write_text(html_doc, encoding="utf-8")
    print_pdf(paths.appendix_b_html, paths.appendix_b_pdf)
    print(f"Wrote {paths.appendix_b_html} and {paths.appendix_b_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


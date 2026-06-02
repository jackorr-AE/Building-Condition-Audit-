"""Report header branding (single or dual logo)."""

import base64
import html
import os
from pathlib import Path
from urllib.parse import quote


def logo_rel(path: Path | None, root: Path) -> str | None:
    if path is None or not path.exists():
        return None
    return os.path.relpath(path, root).replace("\\", "/")


def logo_src_for_html(logo_path: Path | None, html_file: Path) -> str | None:
    """Path or data-URI suitable for img src from a given HTML file location."""
    if logo_path is None or not logo_path.exists():
        return None
    rel = os.path.relpath(logo_path.resolve(), html_file.parent.resolve()).replace("\\", "/")
    return "/".join(quote(part, safe="/") for part in rel.split("/"))


def _mime_for_suffix(suffix: str) -> str:
    if suffix == ".png":
        return "image/png"
    if suffix in (".jpg", ".jpeg"):
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


def file_data_uri(file_path: Path | None) -> str | None:
    if file_path is None or not file_path.exists():
        return None
    mime = _mime_for_suffix(file_path.suffix.lower())
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def logo_data_uri(logo_path: Path | None) -> str | None:
    return file_data_uri(logo_path)


def appendix_page_header_html(
    *,
    left_logo_src: str | None,
    title: str,
    right_logo_src: str | None = None,
    left_alt: str = "Asset Engineers",
    right_alt: str = "Client",
) -> str:
    """Three-column header: logo left, centred section title, optional logo right."""
    title_html = html.escape(title)
    left = (
        f'<img class="left" src="{html.escape(left_logo_src)}" alt="{html.escape(left_alt)}" />'
        if left_logo_src
        else '<div class="left spacer"></div>'
    )
    right = (
        f'<img class="right" src="{html.escape(right_logo_src)}" alt="{html.escape(right_alt)}" />'
        if right_logo_src
        else '<div class="right spacer"></div>'
    )
    return f"""
        <div class="page-header appendix-header">
          {left}
          <div class="title">{title_html}</div>
          {right}
        </div>"""


def page_header_html(
    *,
    left_logo_rel: str | None,
    right_logo_rel: str | None,
    title: str,
    left_alt: str = "Asset Engineers",
    right_alt: str = "Client",
) -> str:
    title_html = html.escape(title)
    if left_logo_rel and right_logo_rel:
        return f"""
        <div class="page-header page-header-dual">
          <img class="left" src="{html.escape(left_logo_rel)}" alt="{html.escape(left_alt)}" />
          <div class="title">{title_html}</div>
          <img class="right" src="{html.escape(right_logo_rel)}" alt="{html.escape(right_alt)}" />
        </div>"""
    if left_logo_rel:
        return f"""
        <div class="page-header page-header-single">
          <img class="left" src="{html.escape(left_logo_rel)}" alt="{html.escape(left_alt)}" />
          <div class="title">{title_html}</div>
        </div>"""
    return f'<div class="page-header page-header-title-only"><div class="title">{title_html}</div></div>'


def site_photos_topbar_html(left_logo_rel: str | None, right_logo_rel: str | None) -> str:
    if left_logo_rel and right_logo_rel:
        return f"""
              <div class="topbar topbar-dual">
                <img class="logo-left" src="{html.escape(left_logo_rel)}" alt="Asset Engineers" />
                <img class="logo-right" src="{html.escape(right_logo_rel)}" alt="Client" />
              </div>"""
    if left_logo_rel:
        return f"""
              <div class="topbar topbar-single">
                <img class="logo-left" src="{html.escape(left_logo_rel)}" alt="Asset Engineers" />
              </div>"""
    return '<div class="topbar topbar-empty"></div>'

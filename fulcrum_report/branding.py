"""Report header branding (single or dual logo)."""

import html
import os
from pathlib import Path


def logo_rel(path: Path | None, root: Path) -> str | None:
    if path is None or not path.exists():
        return None
    return os.path.relpath(path, root).replace("\\", "/")


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

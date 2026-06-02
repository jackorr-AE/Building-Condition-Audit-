"""Print HTML reports to PDF via headless Chromium."""

import subprocess
from pathlib import Path


def print_html_to_pdf(html_path: Path, pdf_path: Path, *, landscape: bool = True) -> None:
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
        f"--print-to-pdf={pdf_path}",
        file_url,
    ]
    if landscape:
        cmd.insert(-1, "--print-to-pdf-landscape")
    subprocess.run(cmd, check=True)

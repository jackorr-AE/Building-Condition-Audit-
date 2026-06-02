import os
import sys
from pathlib import Path

from fulcrum_report.config import load_config
from fulcrum_report.xlsx_io import needs_unpack, unpack_xlsx


def find_toolkit_root(start: Path | None = None) -> Path:
    start = start or Path(__file__).resolve().parent.parent
    for candidate in [start, *start.parents]:
        if (candidate / "fulcrum_report").is_dir() and (candidate / "projects").is_dir():
            return candidate
        if (candidate / "fulcrum_report").is_dir() and any(candidate.glob("generate_*.py")):
            return candidate
    return start


def active_project_name() -> str | None:
    if os.environ.get("FULCRUM_PROJECT"):
        return os.environ["FULCRUM_PROJECT"]
    if "--project" in sys.argv:
        idx = sys.argv.index("--project")
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return None


def list_projects(toolkit_root: Path | None = None) -> list[str]:
    root = toolkit_root or find_toolkit_root()
    projects_dir = root / "projects"
    if not projects_dir.is_dir():
        return []
    return sorted(
        p.name
        for p in projects_dir.iterdir()
        if p.is_dir() and (p / "config" / "project.json").exists()
    )


def find_project_root(project_name: str | None = None) -> Path:
    toolkit = find_toolkit_root()
    name = project_name or active_project_name()
    if not name:
        available = list_projects(toolkit)
        hint = f" Available: {', '.join(available)}" if available else ""
        raise ValueError(
            f"No project specified. Use --project NAME or set FULCRUM_PROJECT.{hint}"
        )
    project_root = toolkit / "projects" / name
    if not (project_root / "config" / "project.json").exists():
        raise FileNotFoundError(f"Project not found: {project_root}")
    return project_root


class ProjectPaths:
    def __init__(self, project_name: str | None = None, root: Path | None = None):
        self.toolkit_root = find_toolkit_root()
        self.root = (root or find_project_root(project_name)).resolve()
        self.config = load_config(self.root)
        p = self.config["paths"]

        self.fulcrum_xlsx = self.root / p["fulcrum_xlsx"]
        self.unpack_dir = self.root / p["unpack_dir"]
        self.unpack_xl = self.unpack_dir / "xl"
        self.photos_dir = self.root / p["photos_dir"]
        self.defect_photos_dir = self.root / p["defect_photos_dir"]
        self.site_photos_dir = self.root / p["site_photos_dir"]
        self.tables_dir = self.root / p["tables_dir"]
        self.reports_dir = self.root / p["reports_dir"]
        self.logo_left = self.root / p["logo_left"]
        right = p.get("logo_right")
        self.logo_right = (self.root / right).resolve() if right else None

        o = self.config["outputs"]
        self.table_4_1 = self.tables_dir / o["table_4_1"]
        self.table_4_2 = self.tables_dir / o["table_4_2"]
        self.table_4_3 = self.tables_dir / o["table_4_3"]
        self.table_defects = self.tables_dir / o["table_defects"]
        self.table_defects_refined = self.tables_dir / o["table_defects_refined"]
        self.appendix_b_csv = self.tables_dir / o["appendix_b_csv"]
        self.appendix_b_html = self.reports_dir / o["appendix_b_html"]
        self.appendix_b_pdf = self.reports_dir / o["appendix_b_pdf"]
        self.defect_list_html = self.reports_dir / o["defect_list_html"]
        self.defect_list_pdf = self.reports_dir / o["defect_list_pdf"]
        self.site_photos_html = self.reports_dir / o["site_photos_html"]
        self.site_photos_pdf = self.reports_dir / o["site_photos_pdf"]

    def ensure_dirs(self) -> None:
        for d in (
            self.fulcrum_xlsx.parent,
            self.unpack_dir,
            self.photos_dir,
            self.defect_photos_dir,
            self.site_photos_dir,
            self.tables_dir,
            self.reports_dir,
            self.logo_left.parent,
        ):
            d.mkdir(parents=True, exist_ok=True)

    def ensure_unpack(self) -> None:
        if self.fulcrum_xlsx.exists() and needs_unpack(self.fulcrum_xlsx, self.unpack_dir):
            unpack_xlsx(self.fulcrum_xlsx, self.unpack_dir)
        elif not (self.unpack_xl / "sharedStrings.xml").exists():
            raise FileNotFoundError(
                f"No unpacked workbook at {self.unpack_dir}. "
                f"Place '{self.fulcrum_xlsx.name}' in {self.fulcrum_xlsx.parent} and run unpack_xlsx.py."
            )

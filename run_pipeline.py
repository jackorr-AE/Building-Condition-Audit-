"""Run the full Fulcrum inspection report pipeline."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from fulcrum_report.paths import ProjectPaths, find_toolkit_root, list_projects

STEPS = [
    ("unpack_xlsx.py", "Unpack Fulcrum export"),
    ("generate_table_4_1.py", "Table 4-1 — internal rooms"),
    ("generate_table_4_2.py", "Table 4-2/4-3 — external areas"),
    ("generate_table_4_excel.py", "Table 4-1/4-2 formatted Excel"),
    ("generate_defects_table.py", "Defects table"),
    ("refine_defects_descriptions.py", "Refine defect descriptions"),
    ("generate_appendix_b_asset_register.py", "Appendix B asset register"),
    ("fill_appendix_b_comments.py", "Fill appendix comments"),
]

REPORT_STEPS = [
    ("generate_appendix_b_pdf.py", "Appendix B HTML/PDF"),
    ("generate_defect_data_sheet.py", "Appendix — Defects Register HTML/PDF"),
    ("generate_site_photos_pdf.py", "Appendix — Site Photos HTML/PDF"),
]


def run_script(script: str, toolkit_root: Path, project: str) -> int:
    env = os.environ.copy()
    env["FULCRUM_PROJECT"] = project
    result = subprocess.run(
        [sys.executable, str(toolkit_root / script), "--project", project],
        cwd=toolkit_root,
        env=env,
    )
    return result.returncode


def main() -> int:
    available = list_projects()
    parser = argparse.ArgumentParser(description="Run Fulcrum inspection report pipeline")
    parser.add_argument(
        "--project", "-p",
        required=not available,
        choices=available if available else None,
        help="Project folder name under projects/",
    )
    parser.add_argument("--tables-only", action="store_true", help="Generate CSV tables only (skip HTML/PDF)")
    parser.add_argument("--reports-only", action="store_true", help="Generate HTML/PDF reports only (skip tables)")
    parser.add_argument("--list", action="store_true", help="List available projects")
    args = parser.parse_args()

    toolkit = find_toolkit_root()

    if args.list:
        for name in available:
            print(name)
        return 0

    if not args.project:
        parser.error("No projects found. Create a folder under projects/ with config/project.json")

    paths = ProjectPaths(project_name=args.project)
    print(f"Toolkit: {toolkit}")
    print(f"Project: {paths.config['project_name']} ({paths.root})")
    print()

    if not args.reports_only:
        for script, label in STEPS:
            print(f"--- {label} ---")
            code = run_script(script, toolkit, args.project)
            if code != 0:
                raise SystemExit(code)
            print()

    if not args.tables_only:
        for script, label in REPORT_STEPS:
            print(f"--- {label} ---")
            code = run_script(script, toolkit, args.project)
            if code != 0:
                print(f"Warning: {script} failed (missing assets such as photos/logos may be expected).")
            print()

    print("Pipeline complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

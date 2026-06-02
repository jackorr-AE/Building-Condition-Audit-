import json
import os
import sys
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "project_name": "Inspection Project",
    "doors_aggregation": "average",
    "dedupe_defects": True,
    "internal_locations": [],
    "external_areas": {},
    "paths": {
        "fulcrum_xlsx": "data/Fulcrum Export.xlsx",
        "unpack_dir": "data/_xlsx_unpack",
        "photos_dir": "assets/photos",
        "defect_photos_dir": "output/defect_photos",
        "site_photos_dir": "output/site_photos_compressed",
        "tables_dir": "output/tables",
        "reports_dir": "output/reports",
        "logo_left": "assets/logos/engineer-logo.png",
        "logo_right": "assets/logos/client-logo.png",
    },
    "outputs": {
        "table_4_1": "Table_4-1.csv",
        "table_4_2": "Table_4-2.csv",
        "table_4_3": "Table_4-3.csv",
        "table_defects": "Table_Defects.csv",
        "table_defects_refined": "Table_Defects_refined.csv",
        "appendix_b_csv": "Appendix - Asset Register.csv",
        "appendix_b_html": "Appendix - Asset Register.html",
        "appendix_b_pdf": "Appendix - Asset Register.pdf",
        "defect_list_html": "Appendix - Defects Register.html",
        "defect_list_pdf": "Appendix - Defects Register.pdf",
        "site_photos_html": "Appendix - Site Photos.html",
        "site_photos_pdf": "Appendix - Site Photos.pdf",
    },
}


def load_config(project_root: Path) -> dict[str, Any]:
    config_path = project_root / "config" / "project.json"
    if not config_path.exists():
        return dict(DEFAULT_CONFIG)

    with config_path.open(encoding="utf-8") as f:
        user_config = json.load(f)

    config = dict(DEFAULT_CONFIG)
    config.update({k: v for k, v in user_config.items() if k not in ("paths", "outputs")})
    paths = {**DEFAULT_CONFIG["paths"], **user_config.get("paths", {})}
    if "logo_right" in user_config.get("paths", {}):
        paths["logo_right"] = user_config["paths"]["logo_right"]
    config["paths"] = paths
    config["outputs"] = {**DEFAULT_CONFIG["outputs"], **user_config.get("outputs", {})}
    return config

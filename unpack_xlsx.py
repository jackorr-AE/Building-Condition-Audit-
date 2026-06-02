from fulcrum_report.paths import ProjectPaths
from fulcrum_report.xlsx_io import FulcrumWorkbook, unpack_xlsx


def main() -> int:
    paths = ProjectPaths()
    if paths.fulcrum_xlsx.exists():
        unpack_xlsx(paths.fulcrum_xlsx, paths.unpack_dir)
        print(f"Unpacked {paths.fulcrum_xlsx} -> {paths.unpack_dir}")
    elif (paths.unpack_xl / "sharedStrings.xml").exists():
        print(f"Using existing unpack at {paths.unpack_dir}")
    else:
        raise FileNotFoundError(
            f"Place '{paths.fulcrum_xlsx.name}' in the project root, or ensure {paths.unpack_dir} exists."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

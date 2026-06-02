from fulcrum_report.paths import ProjectPaths
from fulcrum_report.xlsx_io import FulcrumWorkbook


def main() -> int:
    paths = ProjectPaths()
    wb = FulcrumWorkbook.from_project(paths)

    print("Defects headers:")
    if wb.sheet4:
        for h in wb.sheet4[0].keys():
            print(" -", h)

    from collections import Counter

    counts = Counter()
    for r in wb.sheet4:
        for h, v in r.items():
            if (v or "").strip():
                counts[h] += 1

    print("\nNon-empty counts:")
    for h, c in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"{h}: {c}")

    print("\nSample defect rows (up to 15 with defect_repair_description):")
    shown = 0
    for r in wb.sheet4:
        desc = (r.get("defect_repair_description") or "").strip()
        if not desc:
            continue
        print("---")
        print("location_defect:", (r.get("location_defect") or "").strip())
        print("asset_type_defects:", (r.get("asset_type_defects") or "").strip())
        print("defect_repair_description:", desc)
        print("_parent_id:", (r.get("_parent_id") or "").strip())
        shown += 1
        if shown >= 15:
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

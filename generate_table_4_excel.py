"""Export formatted Excel copies of Tables 4-1 and 4-2 for Word copy-paste."""

from fulcrum_report.paths import ProjectPaths
from fulcrum_report.table_excel_format import default_title_for_csv, write_table_xlsx

TABLE_4_1_LABELS = {"Room / Area"}
TABLE_4_2_LABELS = {"Area"}


def main() -> int:
    paths = ProjectPaths()

    exports: list[tuple] = [
        (
            paths.table_4_1,
            paths.table_4_1.with_suffix(".xlsx"),
            default_title_for_csv(paths.table_4_1, "4-1"),
            TABLE_4_1_LABELS,
            "Table 4-1",
        ),
        (
            paths.table_4_2,
            paths.table_4_2.with_suffix(".xlsx"),
            default_title_for_csv(paths.table_4_2, "4-2"),
            TABLE_4_2_LABELS,
            "Table 4-2",
        ),
    ]

    if paths.table_4_3.exists():
        exports.append(
            (
                paths.table_4_3,
                paths.table_4_3.with_suffix(".xlsx"),
                default_title_for_csv(paths.table_4_3, "4-3"),
                TABLE_4_2_LABELS,
                "Table 4-3",
            )
        )

    for csv_path, xlsx_path, title, labels, sheet_name in exports:
        if not csv_path.exists():
            print(f"Skip {sheet_name}: missing {csv_path}")
            continue
        write_table_xlsx(
            csv_path,
            xlsx_path,
            title=title,
            row_label_columns=labels,
            sheet_name=sheet_name,
        )
        print(f"Wrote {xlsx_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

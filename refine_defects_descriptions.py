import csv
import re

from fulcrum_report.paths import ProjectPaths

TIMEFRAME_PATTERNS = [
    re.compile(r"\bwithin\s+([0-9]+(?:\s*-\s*[0-9]+)?\s+(?:months?|years?))\b", re.IGNORECASE),
    re.compile(r"\bin\s+([0-9]+(?:\s*-\s*[0-9]+)?\s+(?:months?|years?))\b", re.IGNORECASE),
]


def extract_timeframes(text: str) -> list[str]:
    found: list[str] = []
    for pattern in TIMEFRAME_PATTERNS:
        for m in pattern.finditer(text or ""):
            tf = re.sub(r"\s+", " ", m.group(1).strip())
            if tf and tf not in found:
                found.append(tf)
    return found


def strip_timeframe_phrases(text: str) -> str:
    out = re.sub(
        r",?\s*\b(?:within|in)\s+[0-9]+(?:\s*-\s*[0-9]+)?\s+(?:months?|years?)\b\.?",
        ". ",
        text or "",
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", out).strip(" .")


def description_then_action_text(desc: str) -> str:
    raw = (desc or "").strip()
    if not raw:
        return ""
    text = strip_timeframe_phrases(raw)
    text = re.sub(r"\s+\.", ".", text)
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    if text and not text.endswith("."):
        text += "."
    return text


def main() -> int:
    paths = ProjectPaths()
    if not paths.table_defects.exists():
        raise FileNotFoundError(f"Run generate_defects_table.py first. Missing: {paths.table_defects}")

    with paths.table_defects.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    out_rows = []
    for row in rows:
        desc = row.get("Defect / Repair Description", "")
        timeframes = extract_timeframes(desc)
        out = dict(row)
        out["Defect / Repair Description"] = description_then_action_text(desc)
        out["Timeframe"] = "; ".join(timeframes)
        out_rows.append(out)

    fieldnames = ["Area", "Location", "Asset Type", "Defect / Repair Description", "Timeframe", "Photo Reference"]
    paths.table_defects_refined.parent.mkdir(parents=True, exist_ok=True)
    with paths.table_defects_refined.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    print(f"Wrote {paths.table_defects_refined}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

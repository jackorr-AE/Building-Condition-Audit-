# North Quay Inspection Report — Conversation Context

Use this file to resume the AI-assisted reporting session on another computer.
Drop this file (and the full workspace folder) into your new environment and share it with the AI as background context.

---

## Project Goal

Generate formatted building inspection report tables from Fulcrum field data, matching the layout of `Example Report.pdf`. The output will eventually be a full report using the two logos provided.

---

## Files in This Workspace

| File | Purpose |
|------|---------|
| `Example Report.pdf` | Target report layout and table formatting to replicate |
| `Fulcrum Export.xlsx` | Source inspection data (4 worksheets, see below) |
| `AWB Logo.png` | Logo 1 — use in report headers |
| `Asset Engineers Logo.png` | Logo 2 — use in report headers |
| `REFERENCE_FILES.md` | Summary of what each file is for |
| `Table_4-1.csv` | **Draft** CSV for Table 4-1 (internal rooms). Needs to be regenerated — see status below. |
| `_xlsx_unpack/` | Unpacked contents of `Fulcrum Export.xlsx` (it's a ZIP). XML files inside are parsed directly by Python since pandas/openpyxl are not installed in this environment. |

---

## Fulcrum Export.xlsx — Data Structure

The workbook has 4 sheets, all linked through record IDs:

### Sheet 1: `General Collective Items`
- **One row per location** (room or external area)
- **Primary/parent sheet** — all other sheets link back here via `_parent_id` → `_record_id`
- Key columns:
  - `A: _record_id` — unique ID for each location row (used as parent link)
  - `B: _title` — short room name (NOT unique — e.g. "Bathroom / Toilets" appears twice)
  - `G: location` — **full location name** (unique, use this as "Room / Area")
  - `H: location_comments`
  - `J: condition_floor`
  - `O: condition_wall`
  - `T: condition_ceiling`
  - `Y: condition_lights`
  - `AC: other_internal_collective_items` — freetext additional internal items
  - `AE: condition_taps`
  - `AK: condition_basins`
  - `AP: condition_toiletpans`
  - `AV: condition_joinery`
  - `AY: other_collectable_item_internal`
  - Columns `AZ` onward → external condition fields (carpark, fencing, lawn, etc.)

### Sheet 2: `Additional Collective Items`
- Child records linked to Sheet 1 via `C: _parent_id`
- Describes **external** collectable items (smoking area structure, water tanks, windows, carpark, etc.)
- Key columns: `Q: description_of_collectable_item_external`, `R: type_of_collectable_item_external`, `U: condition_othercollectable_external`
- **All rows in this sheet are External** — not relevant for internal table

### Sheet 3: `Assets`
- Child records linked to Sheet 1 via `C: _parent_id`
- One row per individual asset
- Key columns:
  - `C: _parent_id` → links to Sheet 1 `_record_id`
  - `S: location_repeat` — location name (mirrors Sheet 1 `location`)
  - `U: asset_type` — see full list below
  - `W: condition_asset`
  - `AB: last_test_result`
  - `AD: door_type`, `AG: do_they_lock_doors`
  - `AM: do_they_lock_windows`

**Asset types present in the data:**
- `Defibrillator`
- `Doors/Windows/Gates, Doors` ← used for "Doors" column
- `Doors/Windows/Gates, Gates` ← external only
- `Electrical, Distribution Board`
- `Electrical, Miscellaneous`
- `Electrical, Switchboards`
- `Fire, Fire Extinguisher`
- `Fire, Fire Hydrant/Hose Reel`
- `HVAC, Ceiling Exhaust Fans`
- `HVAC, Reverse Cycle`
- `Plumbing, Hot Water Unit`
- `Plumbing, Oily Water Seperator`
- `Security, Security Alarm System`

### Sheet 4: `Defects`
- Child records linked to Sheet 1 via `C: _parent_id`
- Key columns: `V: location_defect`, `W: asset_type_defects`, `X: defect_repair_description`
- Contains defect descriptions per location (mostly External in this dataset, plus a few internal)

---

## Internal Locations (16 rows — Sheet 1, excluding External × 2 and Yard Shed)

| Row | location (col G) | _record_id (col A, truncated) |
|-----|-----------------|-------------------------------|
| 4  | Office 4 (1st Floor) | bb1298e0... |
| 5  | Office 3 (1st Floor) | 56a95af3... |
| 6  | Office 2 (Ground Floor) | 8f36850d... |
| 7  | Main Area | cfbd828c... |
| 8  | Reception | 01c5c1b4... |
| 9  | Server Room | 99abfc21... |
| 10 | Main Area (1st Floor) | df733b48... |
| 11 | Staircase | 45979aec... |
| 12 | Staff Room | a2d93c82... |
| 13 | Storage Room | df176cab... |
| 14 | Female Bathroom / Toilets | b5cc4ab7... |
| 15 | Office 1 (Ground Floor) | 438c11e1... |
| 16 | Male Bathroom / Toilets | d5f96687... |
| 17 | Guard Room | cabaf49b... |
| 19 | Male Toilet (Rear) | 093b67b6... |
| 20 | Female Toilet (Rear) | 69a0fd80... |

---

## Technical Notes (Environment Constraints)

- **pandas and openpyxl are NOT installed** — do not try to `pip install` them; it's been tried and fails.
- **Workaround:** `Fulcrum Export.xlsx` was copied to `_Fulcrum_export_copy.xlsx` then extracted using .NET's `ZipFile` class in PowerShell into `_xlsx_unpack/`. All parsing is done with Python's built-in `xml.etree.ElementTree`.
- **Shell is PowerShell** — use `python -c "..."` for inline Python. Heredoc (`<<EOF`) syntax does not work.
- All Python scripts should be written to be executed as single-line `-c` arguments or saved as `.py` files.

---

## Target Table: Table 4-1 — Overall Condition of Rooms and Components (Internal)

The target layout (from `Example Report.pdf` and the screenshot image provided) has these columns:

| Column | Data Source | Logic |
|--------|------------|-------|
| Room / Area | `location`, col G, Sheet 1 | Use `location` not `_title` — `_title` is not unique |
| Walls | `condition_wall`, Sheet 1 | Direct |
| Flooring | `condition_floor`, Sheet 1 | Direct |
| Ceilings | `condition_ceiling`, Sheet 1 | "Not Applicable" for Staircase |
| Lights | `condition_lights`, Sheet 1 | Direct |
| Doors | `condition_asset` from Sheet 3 | Filter `asset_type = 'Doors/Windows/Gates, Doors'`, link via `_parent_id`. Use **worst** condition where multiple doors per room. |
| Plumbing | Sheet 1 | Worst of `condition_taps`, `condition_basins`, `condition_toiletpans`. Blank for rooms with no plumbing. |
| Cabinetry & Fixed Furniture | `condition_joinery`, Sheet 1 | Direct. Blank where not recorded. |

### Optional additional columns (pending user decision):
- **HVAC** — from Sheet 3 assets (`HVAC, Reverse Cycle` + `HVAC, Ceiling Exhaust Fans`), worst per room
- **Fire Safety** — from Sheet 3 assets (`Fire, Fire Extinguisher`), condition + test result
- **Electrical** — from Sheet 3 assets (`Electrical, *`), worst per room
- **Internal Notes** — `other_internal_collective_items`, col AC, Sheet 1

---

## Current Status

### Completed
- `REFERENCE_FILES.md` created
- `_xlsx_unpack/` — Excel file unpacked and XML accessible
- Data structure fully analysed across all 4 sheets
- **Reusable toolkit** — `fulcrum_report/` shared library + `config/project.json`
- All scripts refactored to use project config (no hardcoded paths)
- `Table_4-1.csv` regenerated with correct logic (`location`, separate Lights/Cabinetry columns, `_parent_id` door linking)
- Defect deduplication enabled (18 Fulcrum rows → 12 unique defects)
- `run_pipeline.py` orchestrates full table + report generation
- See `README.md` for starting new projects

### Configuration (in `config/project.json`)
- Doors column: **average** condition where multiple doors per room
- "Not Applicable" abbreviated to **N/A**
- HVAC, Fire Safety, Electrical columns: not included in Table 4-1 (can be added later)
- Internal Notes column: not included

### Next Steps (optional)
- Regenerate HTML/PDF reports when logos and photos are available
- Review defect rows with empty descriptions in Fulcrum source (e.g. fencing row)
- Run `sync_fulcrum_from_reports.py` after manual CSV edits to push changes back to Fulcrum export

---

## Known Issues with Existing `Table_4-1.csv`

The existing file was a first draft and has several problems that will be fixed in the next regeneration:
1. `Room` column used `_title` → duplicate "Bathroom / Toilets" entries (should use `location`)
2. "Electrical Cabinetry & Fixed Furniture" was one merged column (should be "Lights" + "Cabinetry & Fixed Furniture" separately)
3. "General Comments" column was added (not in the target image)
4. "Windows" column was added as "NA" (not in the target image, no data for it)
5. Door conditions were matched by location name only — should use `_parent_id` link for accuracy

---

## Condition Rating Scale

Used for "worst" logic across multiple sub-components:

| Condition | Rank (worst=0) |
|-----------|---------------|
| Very Poor | 0 |
| Poor | 1 |
| Fair | 2 |
| Good | 3 |
| Excellent | 4 |
| Not Applicable | ignored |
| (blank) | ignored |

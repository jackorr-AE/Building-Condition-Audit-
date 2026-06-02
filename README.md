# Building Condition Audit

Toolkit for generating building inspection report tables and branded HTML/PDF outputs from **Fulcrum** field data exports.

Each building audit lives in its own folder under `projects/`. Shared scripts and the `fulcrum_report` library sit at the toolkit root.

## Folder layout

```
Building Condition Audit/
├── fulcrum_report/              # shared library
├── config/project.template.json # template for new projects
├── run_pipeline.py
├── generate_*.py                # shared scripts
├── projects/
│   ├── North Quay/
│   │   ├── config/project.json
│   │   ├── data/
│   │   │   ├── Fulcrum Export.xlsx
│   │   │   └── _xlsx_unpack/
│   │   ├── assets/
│   │   │   ├── logos/
│   │   │   └── photos/
│   │   └── output/
│   │       ├── tables/          # CSV tables
│   │       └── reports/         # HTML and PDF
│   └── 26126 - Brookton DHS Demountable/
│       └── ...
└── README.md
```

## Quick start

1. Install dependencies (photo scripts only):
   ```
   pip install -r requirements.txt
   ```

2. List available projects:
   ```
   python run_pipeline.py --list
   ```

3. Run the pipeline for a project:
   ```
   python run_pipeline.py --project "North Quay"
   python run_pipeline.py --project "26126 - Brookton DHS Demountable"
   ```

   Individual scripts also accept `--project`:
   ```
   python generate_table_4_1.py --project "North Quay"
   ```

## Adding a new project

1. Create a folder under `projects/` (e.g. `projects/My Building/`)

2. Copy the folder structure from an existing project or create:
   - `config/project.json` (copy from `config/project.template.json`)
   - `data/`
   - `assets/logos/`
   - `assets/photos/`
   - `output/tables/`
   - `output/reports/`

3. Add your source files:
   - `data/Fulcrum Export.xlsx`
   - Logo PNGs in `assets/logos/`
   - Fulcrum photos in `assets/photos/`

4. Edit `config/project.json`:
   - `project_name`
   - `internal_locations` — room names from Fulcrum sheet 1
   - `external_areas` — see North Quay config as an example
   - `outputs` (optional) — custom CSV/HTML filenames, e.g. Table 4-1/4-2 display names
   - `paths.logo_right` — set to `null` for Asset Engineers logo only (no client logo)

5. Run: `python run_pipeline.py --project "My Building"`

## Pipeline steps

| Step | Script | Output location |
|------|--------|-----------------|
| 1 | `unpack_xlsx.py` | `data/_xlsx_unpack/` |
| 2–7 | Table generators | `output/tables/` |
| 8–10 | Report generators | `output/reports/` |

Optional reverse sync after manual CSV edits:
```
python sync_fulcrum_from_reports.py --project "North Quay"
```

## Fulcrum data model

Four linked sheets: General Collective Items, Additional Collective Items, Assets, Defects. Join key: `_parent_id` → `_record_id`. Use **`location`** (not `_title`) for display names.

See `projects/North Quay/CONVERSATION_CONTEXT.md` for detailed field mapping.

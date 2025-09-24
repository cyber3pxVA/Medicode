# DRG Source Data (Not Committed)

This project supports optional DRG (MS-DRG) enrichment. Raw CMS distribution files MUST **NOT** be committed to the repository.

## Do Not Commit
Add or keep these patterns in `.gitignore`:
```
medical-coding-app/drg_source/
*.zip
*.ZIP
```
(We already place a `.gitkeep` so the empty folder exists without data.)

## Where to Place Files
Download the official **MS-DRG Definitions / Data Files** ZIP for the target Fiscal Year from:
https://www.cms.gov/medicare/payment/prospective-payment-systems/acute-inpatient-pps/ms-drg-classifications-and-software

Put the raw ZIP (and any extracted tables) under:
```
medical-coding-app/drg_source/FY2025/
```
(Adjust `FY2025` for other years.)

## Generating a Mapping CSV
The application consumes a simplified mapping file referenced by the environment variable `DRG_MAPPING_PATH` (default `drg_mapping_improved.csv`).

Because CMS does not publish a direct one-to-one ICD-10 → DRG table (grouping is rule-based), any CSV you build here is **heuristic** and must NOT be treated as official for billing.

Recommended workflow:
1. Place raw DRG list file (e.g. `MS-DRG Long Titles.csv`) inside the FY folder.
2. Curate or derive an ICD root → DRG association list (manual or external lawful source).
3. Run the helper script:
   ```bash
   docker compose exec web python scripts/build_drg_mapping.py \
       --drg-titles drg_source/FY2025/MS-DRG_Long_Titles.csv \
       --icd-map drg_source/FY2025/icd_roots_to_drg.csv \
       --out drg_mapping_improved.csv
   ```
4. Restart the container (or just refresh page) to load the new mapping.

## File Format Expected by App
`drg_mapping_improved.csv` should contain:
```
ICD10,DRG,DRG_DESCRIPTION
E11,683,DIABETES W/O CC/MCC
I10,305,HYPERTENSION W/O MCC
```
Multiple DRGs per ICD code = separate lines.

## Disclaimer
This heuristic enrichment is NOT a substitute for the official CMS GROUPER. For production clinical / billing workflows you must run the certified GROUPER logic with full claim context.

## Licensing
Refer to CMS licensing/usage terms. Do not redistribute proprietary artifacts. This repository only stores *derived* heuristic mappings that you create, not raw CMS distributed content.

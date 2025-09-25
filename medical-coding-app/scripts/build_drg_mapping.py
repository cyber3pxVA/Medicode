#!/usr/bin/env python3
"""Build a heuristic MS-DRG mapping CSV used by the app.

This does NOT implement the official CMS GROUPER. It simply joins
ICD root -> DRG candidate pairs with DRG title metadata.

Inputs:
  --drg-titles: CSV containing at minimum DRG and DRG_DESCRIPTION columns.
                Example columns: DRG,WEIGHTS,GEOMETRIC_MEAN_LOS,ARITH_MEAN_LOS,DRG_DESCRIPTION
  --icd-map:    CSV mapping ICD10 roots (or full codes) to DRG numbers.
                Expected columns: ICD10,DRG
  --out:        Output mapping CSV with columns: ICD10,DRG,DRG_DESCRIPTION

Typical usage (inside container):
  python scripts/build_drg_mapping.py \
      --drg-titles drg_source/FY2025/MS-DRG_Long_Titles.csv \
      --icd-map drg_source/FY2025/icd_roots_to_drg.csv \
      --out drg_mapping.csv

You may maintain the icd_roots_to_drg.csv manually or derive it from
local analytics. Each line associates an ICD root (e.g. E11) with a
DRG that is clinically plausible. Multiple lines per ICD root allowed.

Safety / Compliance:
- Do not distribute licensed CMS raw artifacts.
- This script only produces a derived, heuristic mapping.

"""
from __future__ import annotations
import argparse
import csv
import sys
from pathlib import Path

REQUIRED_DRG_TITLE_COLUMNS = {"DRG", "DRG_DESCRIPTION"}
REQUIRED_ICD_MAP_COLUMNS = {"ICD10", "DRG"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def validate_columns(rows: list[dict[str, str]], required: set[str], label: str):
    if not rows:
        raise ValueError(f"{label} CSV has no rows")
    missing = required - set(rows[0].keys())
    if missing:
        raise ValueError(f"{label} CSV missing columns: {', '.join(sorted(missing))}")


def build_mapping(drg_title_rows, icd_map_rows):
    # Build DRG -> description lookup (dedupe: keep first occurrence)
    drg_lookup: dict[str, str] = {}
    for r in drg_title_rows:
        drg = r.get("DRG", "").strip()
        desc = r.get("DRG_DESCRIPTION", "").strip()
        if drg and drg not in drg_lookup:
            drg_lookup[drg] = desc or ""

    output_rows = []
    seen = set()
    for r in icd_map_rows:
        icd = r.get("ICD10", "").strip().upper()
        drg = r.get("DRG", "").strip()
        if not icd or not drg:
            continue
        key = (icd, drg)
        if key in seen:
            continue
        seen.add(key)
        desc = drg_lookup.get(drg, "")
        output_rows.append({"ICD10": icd, "DRG": drg, "DRG_DESCRIPTION": desc})
    return output_rows


def write_csv(path: Path, rows):
    fieldnames = ["ICD10", "DRG", "DRG_DESCRIPTION"]
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Build heuristic DRG mapping CSV.")
    p.add_argument('--drg-titles', required=True, help='CSV with DRG,DRG_DESCRIPTION columns')
    p.add_argument('--icd-map', required=True, help='CSV with ICD10,DRG columns (roots or full codes)')
    p.add_argument('--out', default='drg_mapping.csv', help='Output CSV path')
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    drg_titles_path = Path(args.drg_titles)
    icd_map_path = Path(args.icd_map)
    out_path = Path(args.out)

    if not drg_titles_path.exists():
        print(f"ERROR: DRG titles file not found: {drg_titles_path}", file=sys.stderr)
        return 2
    if not icd_map_path.exists():
        print(f"ERROR: ICD map file not found: {icd_map_path}", file=sys.stderr)
        return 2

    drg_title_rows = read_csv(drg_titles_path)
    icd_map_rows = read_csv(icd_map_path)
    validate_columns(drg_title_rows, REQUIRED_DRG_TITLE_COLUMNS, "DRG titles")
    validate_columns(icd_map_rows, REQUIRED_ICD_MAP_COLUMNS, "ICD map")

    mapping_rows = build_mapping(drg_title_rows, icd_map_rows)
    if not mapping_rows:
        print("WARNING: No mapping rows produced.", file=sys.stderr)

    write_csv(out_path, mapping_rows)
    print(f"Wrote {len(mapping_rows)} rows -> {out_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

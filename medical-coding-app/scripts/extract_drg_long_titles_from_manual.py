#!/usr/bin/env python3
"""Extract DRG long titles from a CMS MS-DRG Definitions Manual text bundle.

Heuristic parser: scans one or more .txt files for lines that begin with a
three-digit DRG code followed by at least one space and then a description.

Example line patterns:
 001 HEART TRANSPLANT OR IMPLANT ...
 042 NERVOUS SYSTEM NEOPLASMS W MCC
 683 DIABETES W/O CC/MCC

Some manuals may wrap descriptions across lines; we capture only the first
line (primary long title). Adjust logic if you want to merge continuations.

Outputs a CSV with columns:
  DRG,DRG_DESCRIPTION

Usage:
  python scripts/extract_drg_long_titles_from_manual.py \
      --input-dir drg_source/FY2026/msdrgv43.icd10_ro_definitionsmanual_text \
      --out drg_source/FY2026/drg_long_titles_v43.csv

Then feed into build script:
  python scripts/build_drg_mapping.py \
      --drg-titles drg_source/FY2026/drg_long_titles_v43.csv \
      --icd-map drg_source/FY2026/icd_roots_to_drg.csv \
      --out drg_mapping_improved.csv

Limitations:
- Ignores DRG ranges that appear in narrative (e.g., "DRGs 981-983").
- Stops description at end of line; multi-line wrapped text is truncated.
- Removes leading/trailing whitespace and normalizes internal spaces.

"""
from __future__ import annotations
import argparse
import csv
import re
from pathlib import Path

DRG_LINE_RE = re.compile(r"^(?P<drg>\d{3})\s+(?P<desc>[A-Z0-9][A-Z0-9 ,;/'()\-\+&]*[A-Z0-9)])?", re.IGNORECASE)
# Fallback simpler pattern if above misses legitimate mixed case:
DRG_SIMPLE_RE = re.compile(r"^(?P<drg>\d{3})\s+(?P<desc>.+?)\s*$")


def extract_from_file(path: Path, seen: set[str]):
    rows = []
    with path.open('r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            raw = line.rstrip('\n')
            if not raw or len(raw) < 6:
                continue
            m = DRG_LINE_RE.match(raw)
            if not m:
                m = DRG_SIMPLE_RE.match(raw)
            if not m:
                continue
            drg = m.group('drg')
            desc = m.group('desc') or ''
            # Exclude obvious false positives where desc starts with 'DRG' (narrative like 'DRGs 981-983')
            if desc.upper().startswith('DRG '):
                continue
            # Basic cleanup
            desc_clean = ' '.join(desc.split())
            key = (drg, desc_clean)
            if key in seen:
                continue
            seen.add(key)
            rows.append({'DRG': drg, 'DRG_DESCRIPTION': desc_clean})
    return rows


def parse_dir(input_dir: Path):
    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input directory not found: {input_dir}")
    all_rows = []
    seen: set[str] = set()
    txt_files = sorted(input_dir.glob('*.txt'))
    if not txt_files:
        raise SystemExit(f"No .txt files in {input_dir}")
    for txt in txt_files:
        extracted = extract_from_file(txt, seen)
        all_rows.extend(extracted)
    # Deduplicate DRG numbers keeping first description if multiple
    final = []
    seen_drg = set()
    for r in all_rows:
        if r['DRG'] in seen_drg:
            continue
        seen_drg.add(r['DRG'])
        final.append(r)
    final.sort(key=lambda r: int(r['DRG']))
    return final


def write_csv(path: Path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['DRG', 'DRG_DESCRIPTION'])
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description='Extract DRG long titles from manual text files.')
    ap.add_argument('--input-dir', required=True, help='Directory containing manual .txt files')
    ap.add_argument('--out', required=True, help='Output CSV path')
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    out_path = Path(args.out)
    rows = parse_dir(input_dir)
    if not rows:
        raise SystemExit('No DRG rows extracted — adjust regex or verify input files.')
    write_csv(out_path, rows)
    print(f"Extracted {len(rows)} DRG rows -> {out_path}")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
from __future__ import annotations
"""Extract MS-DRG long titles (heuristic) from a manual text bundle.

Keeps first occurrence of each 3-digit DRG and attempts to join simple
continuation lines. Produces CSV with columns: DRG,DRG_DESCRIPTION

This is intentionally simple; adjust regex if you need broader coverage.
"""
import argparse
import csv
import re
from pathlib import Path

DRG_LINE_RE = re.compile(r"^(\s*)(\d{3})\s+([A-Z0-9][A-Z0-9 &'`,;:\-/()]+.*?)\s*$")
CONTINUATION_RE = re.compile(r"^\s{4,}([A-Z0-9&',;:\-/() ]{6,})$")


def extract_from_file(path: Path, seen: set[str]):
    rows = []
    pending = None  # (drg, desc)
    try:
        lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception:
        return []
    for line in lines:
        m = DRG_LINE_RE.match(line)
        if m:
            # flush previous
            if pending and pending[0] not in seen:
                rows.append(pending)
                seen.add(pending[0])
            drg = m.group(2)
            desc = m.group(3).strip()
            pending = (drg, desc)
            continue
        if pending:
            cm = CONTINUATION_RE.match(line)
            if cm:
                frag = cm.group(1).strip()
                if frag and frag not in pending[1]:
                    pending = (pending[0], pending[1] + ' ' + frag)
    if pending and pending[0] not in seen:
        rows.append(pending)
        seen.add(pending[0])
    return rows


def walk(input_dir: Path):
    seen: set[str] = set()
    collected = []
    for f in sorted(input_dir.rglob('*.txt')):
        collected.extend(extract_from_file(f, seen))
    return collected


def write_csv(rows, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['DRG', 'DRG_DESCRIPTION'])
        for drg, desc in sorted(rows, key=lambda r: int(r[0])):
            w.writerow([drg, ' '.join(desc.split())])


def parse_args():
    ap = argparse.ArgumentParser(description='Heuristically extract DRG long titles from manual text bundle.')
    ap.add_argument('--input-dir', required=True)
    ap.add_argument('--out', required=True)
    return ap.parse_args()


def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        raise SystemExit(f"Input directory not found: {input_dir}")
    rows = walk(input_dir)
    if not rows:
        print('WARNING: No DRG rows extracted.')
    write_csv(rows, Path(args.out))
    print(f"Extracted {len(rows)} DRG titles -> {args.out}")


if __name__ == '__main__':
    main()

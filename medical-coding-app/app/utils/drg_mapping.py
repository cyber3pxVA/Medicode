"""DRG Mapping Utility (Open Data Based)

Loads an ICD-10 -> MS-DRG mapping from a CSV file provided by the user.

Expected CSV columns (case-insensitive):
    ICD10, DRG, DRG_DESCRIPTION

Only open, publicly shareable mapping sources should be used (e.g., CMS released
public DRG definitions—ensure license compliance separately). The repository does
NOT include full mapping; user supplies via environment variable or default path.

Environment Variables:
    DRG_MAPPING_PATH: Path to the mapping CSV (default: drg_mapping.csv in project root of medical-coding-app)

Usage:
    from app.utils.drg_mapping import get_drg_for_icd10
    drgs = get_drg_for_icd10('E11')  # returns list of {drg, description}
"""
from __future__ import annotations
import csv
import os
from functools import lru_cache
from typing import List, Dict

DEFAULT_PATH = os.environ.get("DRG_MAPPING_PATH", os.path.join(os.getcwd(), "drg_mapping.csv"))

REQUIRED_COLUMNS = {"icd10", "drg", "drg_description"}

@lru_cache(maxsize=1)
def _load_mapping() -> Dict[str, List[Dict[str, str]]]:
    mapping: Dict[str, List[Dict[str, str]]] = {}
    path = DEFAULT_PATH
    if not os.path.exists(path):
        return mapping  # Silent: feature becomes a no-op if mapping not provided
    try:
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            lower_fieldnames = {c.lower() for c in reader.fieldnames or []}
            if not REQUIRED_COLUMNS.issubset(lower_fieldnames):
                # Attempt flexible mapping
                col_map = {}
                for req in REQUIRED_COLUMNS:
                    for actual in reader.fieldnames or []:
                        if actual.lower() == req:
                            col_map[req] = actual
                            break
                if set(col_map.keys()) != REQUIRED_COLUMNS:
                    return mapping
            else:
                col_map = {c: c for c in reader.fieldnames or [] if c.lower() in REQUIRED_COLUMNS}
            for row in reader:
                icd = row[col_map.get('icd10')].strip().upper()
                drg = row[col_map.get('drg')].strip()
                desc = row[col_map.get('drg_description')].strip()
                if not icd or not drg:
                    continue
                mapping.setdefault(icd, []).append({
                    'drg': drg,
                    'description': desc
                })
    except Exception:
        # Fail silently; will simply not enrich results
        return {}
    return mapping

def get_drg_for_icd10(icd_code: str) -> List[Dict[str, str]]:
    if not icd_code:
        return []
    code = icd_code.strip().upper()
    m = _load_mapping()
    return m.get(code, [])

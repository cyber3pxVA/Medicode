"""DRG Provider Module

Purpose:
    Hard isolate all DRG logic behind a single optional interface so the rest of the
    application can ignore DRGs entirely if disabled or if the mapping file is missing.

Feature Flag:
    Set environment variable ENABLE_DRG=1 to activate enrichment. Anything else (or unset)
    causes all public functions to return empty results quickly without touching the mapping file.

Environment Variables:
    ENABLE_DRG: '1' to enable; default off
    DRG_MAPPING_PATH: Path to CSV mapping (same semantics as previous util)

Public Functions:
    drg_enabled() -> bool
    get_drg_for_icd10(code) -> list[{drg, description}]
    enrich_codes_with_drgs(codes) -> None (in-place adds drg_codes)

The previous implementation in utils.drg_mapping remains for backward compatibility but
should be considered INTERNAL and may be removed later.
"""
from __future__ import annotations
import os
from typing import List, Dict

# Lazy import original util only if feature enabled
_DEF_DISABLED: List[Dict[str, str]] = []


def drg_enabled() -> bool:
    return os.environ.get('ENABLE_DRG', '0') == '1'


def _lazy_import():  # type: ignore
    if not drg_enabled():
        return None
    try:
        from app.utils.drg_mapping import get_drg_for_icd10 as _orig
        return _orig
    except Exception:
        return None


def get_drg_for_icd10(icd_code: str) -> List[Dict[str, str]]:
    if not drg_enabled():
        return _DEF_DISABLED
    getter = _lazy_import()
    if getter is None:
        return _DEF_DISABLED
    try:
        return getter(icd_code) or []
    except Exception:
        return _DEF_DISABLED


def enrich_codes_with_drgs(codes: List[Dict]):
    """Mutate list of concept dicts adding 'drg_codes' only when enabled.

    Each code dict is expected (not required) to have 'icd10_codes': List[{'code': str, 'desc': str}]
    Adds: 'drg_codes': List[{'drg': str, 'description': str}]
    """
    if not drg_enabled():
        for c in codes:
            c['drg_codes'] = []
        return
    getter = _lazy_import()
    if getter is None:
        for c in codes:
            c['drg_codes'] = []
        return
    for c in codes:
        drg_set: List[Dict[str, str]] = []
        for icd_entry in c.get('icd10_codes', []) or []:
            if isinstance(icd_entry, dict):
                code_val = icd_entry.get('code')
            else:
                code_val = None
            if not code_val:
                continue
            try:
                drgs = getter(code_val) or []
            except Exception:
                drgs = []
            # Deduplicate DRGs by drg id
            existing_ids = {d['drg'] for d in drg_set if 'drg' in d}
            for d in drgs:
                if d.get('drg') not in existing_ids:
                    drg_set.append(d)
                    existing_ids.add(d.get('drg'))
        c['drg_codes'] = drg_set

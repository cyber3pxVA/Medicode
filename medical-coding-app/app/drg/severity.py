"""Severity / triad selection helpers for heuristic DRG enrichment.

Goal:
    Given enriched concepts (each possibly containing `icd10_codes` and the
    list of `drg_codes` derived from mapping), pick a principal diagnosis
    and select the most severe DRG variant (MCC > CC > BASE) available for
    that principal based on secondary diagnoses evidence.

IMPORTANT:
    This is *heuristic*. Real MS-DRG grouping considers procedure codes,
    age, sex, discharge status, ventilator hours, and numerous special
    cases. We only look at diagnosis codes and descriptive strings.

Public function:
    apply_drg_severity_selection(codes: list[dict]) -> dict | None
        Mutates the `codes` list (adds 'chosen_drg' to principal concept)
        and returns a rationale dict describing the decision.
"""
from __future__ import annotations
from typing import List, Dict, Optional, Tuple
import re

try:
    from app.drg.provider import get_drg_for_icd10, drg_enabled
except Exception:  # Safety – if provider not present, degrade gracefully.
    def drg_enabled():  # type: ignore
        return False
    def get_drg_for_icd10(_code):  # type: ignore
        return []

SEVERITY_ORDER = ["MCC", "CC", "BASE"]
ROOT_PRIORITY = [  # clinical acuity preference heuristic
    'A41',  # sepsis
    'J18',  # pneumonia
    'I21',  # acute MI example (future)
    'I63',  # stroke
    'I10',  # hypertension (lower acuity)
]


def classify_severity(desc: str) -> str:
    if not desc:
        return "BASE"
    up = desc.upper()
    if "WITH MCC" in up or " W MCC" in up:
        return "MCC"
    if "WITH CC" in up or " W CC" in up:
        return "CC"
    if "W/O CC/MCC" in up or "W/O MCC/CC" in up or "WITHOUT CC/MCC" in up:
        return "BASE"
    # Fall back – some descriptions omit explicit tier language.
    return "BASE"


def _icd_root(code: str) -> str:
    if not code:
        return code
    code = code.upper()
    if '.' in code:
        return code.split('.')[0]
    # Trim to at least 3 chars (letter + 2 digits) for root comparison
    return code[:3] if len(code) > 3 else code


def build_root_index(concepts: List[Dict]) -> Dict[str, Dict[str, List[Dict]]]:
    """Return structure: root -> { 'concepts': [...], 'drgs': [variant dicts] }"""
    idx: Dict[str, Dict[str, List[Dict]]] = {}
    for c in concepts:
        for icd in unique_icd_codes(c):
            root = _icd_root(icd)
            slot = idx.setdefault(root, {'concepts': [], 'drgs': []})
            if c not in slot['concepts']:
                slot['concepts'].append(c)
            for rec in c.get('drg_codes') or []:
                # Normalize severity field if missing
                r = dict(rec)
                r['severity'] = classify_severity(r.get('description', ''))
                # Dedup by drg id
                if all(r.get('drg') != existing.get('drg') for existing in slot['drgs']):
                    slot['drgs'].append(r)
    return idx


def score_root(root: str, data: Dict[str, List[Dict]]) -> Tuple[int, int, int]:
    """Return a tuple for sorting: (severity_span_score, mcc_count, total_variants)"""
    variants = data.get('drgs', [])
    severities = [v.get('severity') for v in variants]
    sev_set = set(severities)
    span = 0
    if 'MCC' in sev_set:
        span += 2
    if 'CC' in sev_set:
        span += 1
    mcc_count = sum(1 for s in severities if s == 'MCC')
    return (span, mcc_count, len(variants))


def pick_principal_root(concepts: List[Dict]) -> Optional[str]:
    idx = build_root_index(concepts)
    if not idx:
        return None
    # Score roots; prefer one with MCC span > CC span > BASE and more variants as tie-breaker
    best = None
    best_score = (-1, -1, -1)
    for root, data in idx.items():
        score = score_root(root, data)
        if score > best_score:
            best_score = score
            best = root
    if best:
        return best
    # Fallback ordering by ROOT_PRIORITY if scores tie or nothing selected
    for pref in ROOT_PRIORITY:
        if pref in idx:
            return pref
    return None


def unique_icd_codes(concept: Dict) -> List[str]:
    out = []
    for entry in concept.get('icd10_codes') or []:
        if isinstance(entry, dict):
            code = entry.get('code')
        else:
            code = str(entry)
        if code and code not in out:
            out.append(code)
    return out


def collect_variants(principal_icd: str):
    # Root strategy: exact, root without dot, first 3 chars.
    variants = []
    seen_drg_ids = set()
    # 1. All DRGs directly tied to exact ICD (already enriched later)
    for rec in get_drg_for_icd10(principal_icd) or []:
        sid = rec.get('drg')
        if sid and sid not in seen_drg_ids:
            rec = dict(rec)
            rec['severity'] = classify_severity(rec.get('description', ''))
            variants.append(rec)
            seen_drg_ids.add(sid)
    base_root = principal_icd.split('.')[0]
    if base_root != principal_icd:
        for rec in get_drg_for_icd10(base_root) or []:
            sid = rec.get('drg')
            if sid and sid not in seen_drg_ids:
                rec = dict(rec)
                rec['severity'] = classify_severity(rec.get('description', ''))
                variants.append(rec)
                seen_drg_ids.add(sid)
    # 3-char root
    if len(base_root) > 3:
        short_root = base_root[:3]
        for rec in get_drg_for_icd10(short_root) or []:
            sid = rec.get('drg')
            if sid and sid not in seen_drg_ids:
                rec = dict(rec)
                rec['severity'] = classify_severity(rec.get('description', ''))
                variants.append(rec)
                seen_drg_ids.add(sid)
    return variants


def evidence_severity(secondary: List[Dict]) -> tuple[bool, bool]:
    has_mcc = False
    has_cc = False
    for c in secondary:
        for rec in c.get('drg_codes') or []:
            sev = classify_severity(rec.get('description', ''))
            if sev == 'MCC':
                has_mcc = True
            elif sev == 'CC':
                has_cc = True
        if has_mcc:
            break
    return has_mcc, (has_cc or has_mcc)


def choose_variant(variants: List[Dict], has_mcc: bool, has_cc: bool) -> Optional[Dict]:
    if not variants:
        return None
    # Build dict by severity preferring first occurrence.
    by_sev = {}
    for v in variants:
        sev = v.get('severity', 'BASE')
        if sev not in by_sev:
            by_sev[sev] = v
    if has_mcc and 'MCC' in by_sev:
        return by_sev['MCC']
    if has_cc and 'CC' in by_sev:
        return by_sev['CC']
    # Base fallback (either explicit BASE or any variant)
    return by_sev.get('BASE') or variants[0]


def apply_drg_severity_selection(codes: List[Dict]) -> Optional[Dict]:
    if not drg_enabled():
        return None
    principal_root = pick_principal_root(codes)
    if not principal_root:
        return None
    # Gather variants for principal root by querying mapping directly
    variants = collect_variants(principal_root)
    if not variants:
        return None
    # Evidence from other roots
    idx = build_root_index(codes)
    secondary_concepts = []
    for root, data in idx.items():
        if root == principal_root:
            continue
        secondary_concepts.extend(data['concepts'])
    has_mcc, has_cc_any = evidence_severity(secondary_concepts)
    chosen = choose_variant(variants, has_mcc, has_cc_any)
    # Attach chosen to first concept owning an ICD code with that root (prefer explicit code variant)
    attach_concept = None
    for c in idx[principal_root]['concepts']:
        if any(_icd_root(ic) == principal_root for ic in unique_icd_codes(c)):
            attach_concept = c
            break
    if attach_concept and chosen:
        attach_concept['chosen_drg'] = {
            'drg': chosen.get('drg'),
            'description': chosen.get('description'),
            'severity': chosen.get('severity')
        }
    # Derive a representative principal ICD (first ICD of principal root found)
    principal_icd = None
    for c in idx[principal_root]['concepts']:
        for ic in unique_icd_codes(c):
            if _icd_root(ic) == principal_root:
                principal_icd = ic
                break
        if principal_icd:
            break

    rationale = {
        'principal_root': principal_root,
        'principal_icd': principal_icd,  # backward compat for earlier tests
        'principal_terms': [c.get('term') for c in idx[principal_root]['concepts']],
        'available_variants': [
            {'drg': v.get('drg'), 'description': v.get('description'), 'severity': v.get('severity')}
            for v in variants
        ],
        'secondary_mcc_present': has_mcc,
        'secondary_cc_present': (has_cc_any and not has_mcc),
        'chosen_severity': chosen.get('severity') if chosen else None,
        'chosen_drg': chosen.get('drg') if chosen else None,
        'scoring_debug': {
            root: score_root(root, data) for root, data in idx.items()
        }
    }
    return rationale

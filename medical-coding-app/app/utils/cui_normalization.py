"""CUI Normalization Utility

Maps variant / overly specific CUIs returned by QuickUMLS or the RAG pipeline
to more general canonical CUIs that are more likely to have downstream code
coverage (ICD-10, SNOMED). This is a minimal, opt-in layer.

Design:
  - A static dictionary `CUI_NORMALIZATION_MAP` provides explicit mappings.
  - If a CUI is normalized, the original is preserved under `original_cui` in
    the response entry so audit trails remain intact.
  - Mapping is intentionally conservative: only include cases where clinical
    meaning is equivalent for aggregation purposes.

Extension:
  - To extend, edit `CUI_NORMALIZATION_MAP` or load from a JSON file whose
    path is supplied via env var `CUI_NORMALIZATION_PATH` (optional future step).

NOTE: This is *not* a hierarchical traversal. It is a curated alias list.
      Use carefully to avoid semantic drift.
"""
from __future__ import annotations
import os
import json
from typing import Dict

# Base static map (curated). Example: certain OMIM-specific diabetes CUIs -> general diabetes mellitus CUI.
CUI_NORMALIZATION_MAP: Dict[str, str] = {
    # Noninsulin-dependent diabetes mellitus 2 -> Type 2 diabetes mellitus
    "C1832387": "C0011860",  # maps to common Type 2 diabetes mellitus concept
}

def load_external_overrides() -> Dict[str, str]:
    """Optionally load external JSON mapping (simple {"from":"to", ...})."""
    path = os.environ.get("CUI_NORMALIZATION_PATH")
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        # Filter only string->string entries
        return {str(k): str(v) for k,v in data.items() if isinstance(k,str) and isinstance(v,str)}
    except Exception:
        return {}

_EXT_OVERRIDES = load_external_overrides()

def get_canonical_cui(cui: str) -> str:
    """Return canonical CUI if a mapping exists, else the original."""
    if not cui:
        return cui
    return _EXT_OVERRIDES.get(cui, CUI_NORMALIZATION_MAP.get(cui, cui))

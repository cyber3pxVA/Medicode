"""Simple rule-based negation detection for clinical text.

This is a lightweight alternative to full NegEx/medSpaCy context module.
We scan for negation cues near target spans/terms.

Functions:
    is_negated(term, text) -> bool
    mark_negations(matches, text, key_term='term') -> list[dict]

Limitations:
    - Window-based heuristic; may miss complex syntactic scope.
    - Does not handle double negation intentionally.
"""
from __future__ import annotations
import re
from typing import List, Dict

NEGATION_CUES = [
    'no', 'denies', 'denied', 'without', 'not', "hasn't", "hadn't", "wasn't", "weren't", "isn't",
    'negative for', 'free of', 'absence of'
]

# Precompile regex patterns (word boundary, case-insensitive)
CUE_PATTERNS = [re.compile(r'\b' + re.escape(cue) + r'\b', re.IGNORECASE) for cue in NEGATION_CUES]

# Maximum character distance from cue to term to consider it negated (bidirectional)
WINDOW_CHARS = 40  # legacy fallback window

SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[.!?])\s+')

def is_negated(term: str, text: str) -> bool:
    """Return True if term appears negated within its sentence.

    Strategy:
      1. Split text into rough sentences (regex punctuation heuristic).
      2. For each sentence containing the term (case-insensitive):
         - Apply cue proximity window restricted to that sentence span only.
      3. Fall back to global window logic if sentence split fails.
    """
    if not term or not text:
        return False
    tl = term.lower()
    # Sentence segmentation (cheap heuristic)
    sentences = SENTENCE_SPLIT_REGEX.split(text)
    if not sentences or len(sentences) == 1:
        sentences = [text]
    found_any = False
    SCOPE_BREAKERS = {'but', 'however', 'nevertheless', 'yet', 'although'}
    for sent in sentences:
        sent_lower = sent.lower()
        if tl not in sent_lower:
            continue
        found_any = True
        # Phrase-level early detection for multi-token cues like 'no evidence of'
        PHRASE_CUES = ['no evidence of', 'absence of', 'negative for', 'free of']
        for phrase in PHRASE_CUES:
            p_idx = sent_lower.find(phrase)
            if p_idx != -1:
                t_idx = sent_lower.find(tl)
                if t_idx != -1 and p_idx < t_idx:
                    inter = sent_lower[p_idx+len(phrase):t_idx]
                    # Abort if a scope breaker appears between phrase and term
                    if not any(b in inter.split() for b in SCOPE_BREAKERS):
                        return True
        # Tokenize crude
        tokens = re.findall(r"\w+|[^\w\s]", sent_lower)
        # Precompute cue indices
        cue_positions = []
        for i, tok in enumerate(tokens):
            for pat in CUE_PATTERNS:
                if pat.fullmatch(tok):
                    cue_positions.append(i)
                    break
        # Break scope at conjunction tokens after cue
        for occurrence in [m.start() for m in re.finditer(re.escape(tl), sent_lower)]:
            # Map character index to token index (approximate)
            char_count = 0
            term_token_index = None
            for i, tok in enumerate(tokens):
                char_count += len(tok)
                if char_count >= occurrence + len(tl):
                    term_token_index = i
                    break
            if term_token_index is None:
                continue
            # Any cue before term without scope breaker between?
            for cue_idx in cue_positions:
                if cue_idx < term_token_index:
                    intervening = tokens[cue_idx+1:term_token_index]
                    if any(t in SCOPE_BREAKERS for t in intervening):
                        continue  # scope broken
                    return True
    if not found_any:
        return False
    return False

def mark_negations(matches: List[Dict], text: str, key_term: str = 'term') -> List[Dict]:
    for m in matches:
        term = m.get(key_term)
        try:
            m['negated'] = bool(is_negated(term, text))
        except Exception:
            m['negated'] = False
    return matches

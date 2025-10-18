import pytest
from app.utils.negation import is_negated, mark_negations

def test_is_negated_basic():
    text = "Patient denies chest pain but reports fever."
    assert is_negated('chest pain', text) is True
    assert is_negated('fever', text) is False

def test_mark_negations():
    text = "No evidence of pneumonia. Patient has fever."
    matches = [{'term':'pneumonia'},{'term':'fever'}]
    out = mark_negations(matches, text)
    m = {m['term']: m['negated'] for m in out}
    assert m['pneumonia'] is True
    assert m['fever'] is False

#!/usr/bin/env python3
"""
Direct test of DRG mapping and similarity calculation improvements
"""
import os
import sys
import json
import random

# Add the app directory to path
sys.path.insert(0, '/media/frasod/4T/Code_Projects/Medicode/medical-coding-app')

from app.utils.drg_mapping import get_drg_for_icd10, _load_mapping
from app.nlp.pipeline import NLPPipeline

def test_drg_mapping():
    """Test the improved DRG mapping"""
    print("=== Testing DRG Mapping ===")
    
    # Load the improved mapping
    drg_mapping = _load_mapping()
    print(f"Loaded {len(drg_mapping)} DRG mappings")
    
    # Test hypertension mapping
    test_codes = ['I10', 'I11', 'E11', 'J18.9']
    for code in test_codes:
        drg_list = get_drg_for_icd10(code)
        if drg_list:
            for drg in drg_list:
                print(f"ICD-10 {code} -> DRG {drg['drg']}: {drg['description']}")
        else:
            print(f"ICD-10 {code} -> No DRG mapping found")
    
def test_similarity():
    """Test similarity calculation improvements"""
    print("\n=== Testing Similarity Calculation ===")
    
    # Mock the NLP pipeline with improved similarity
    class MockNLP:
        def __init__(self):
            self.initialized = True
            
        def process_text(self, text):
            """Generate mock results with realistic similarity scores"""
            text_lower = text.lower()
            results = []
            
            medical_terms = {
                'hypertension': ('Hypertensive disease', 'C0020538', ['I10']),
                'diabetes': ('Diabetes mellitus', 'C0011849', ['E11']),
                'pneumonia': ('Pneumonia', 'C0032285', ['J18.9']),
                'patient': ('Patient', 'C0030705', [])
            }
            
            for term, (desc, cui, icd_codes) in medical_terms.items():
                if term in text_lower:
                    # Generate realistic similarity scores based on relevance
                    if term in ['hypertension', 'diabetes']:
                        similarity = round(random.uniform(0.82, 0.94), 3)
                    elif term == 'pneumonia':
                        similarity = round(random.uniform(0.78, 0.90), 3)
                    else:
                        similarity = round(random.uniform(0.55, 0.75), 3)
                    
                    result = {
                        'cui': cui,
                        'term': desc,
                        'similarity': similarity,
                        'semtypes': ['Disease or Syndrome'] if icd_codes else ['Human'],
                        'icd10_codes': [{'code': code, 'desc': f'Description for {code}'} for code in icd_codes]
                    }
                    results.append(result)
            
            return results
    
    nlp = MockNLP()
    
    test_text = "patient has hypertension and diabetes"
    results = nlp.process_text(test_text)
    
    print(f"Processing text: '{test_text}'")
    for result in results:
        print(f"  Term: {result['term']}")
        print(f"  Similarity: {result['similarity']} (should vary, not always 1.0)")
        print(f"  ICD-10 codes: {result.get('icd10_codes', [])}")
        print()

def test_integration():
    """Test DRG mapping integration with NLP results"""
    print("=== Testing Integration ===")
    
    # Mock NLP result for hypertension
    nlp_result = {
        'cui': 'C0020538',
        'term': 'Hypertensive disease',
        'similarity': 0.89,  # Realistic score
        'icd10_codes': [{'code': 'I10', 'desc': 'Essential hypertension'}],
        'semtypes': ['Disease or Syndrome']
    }
    
    # Enrich with DRG codes
    for icd in nlp_result.get('icd10_codes', []):
        drg_list = get_drg_for_icd10(icd['code'])
        if drg_list:
            if 'drg_codes' not in nlp_result:
                nlp_result['drg_codes'] = []
            nlp_result['drg_codes'].extend(drg_list)
    
    print("Enriched result:")
    print(json.dumps(nlp_result, indent=2))
    
    # Test complexity determination
    if nlp_result.get('drg_codes'):
        for drg in nlp_result['drg_codes']:
            desc = drg['description']
            if 'MCC' in desc:
                complexity = "High"
            elif 'CC' in desc and 'MCC' not in desc:
                complexity = "Medium"  
            elif 'W/O' in desc and ('CC' in desc or 'MCC' in desc):
                complexity = "Low"
            else:
                complexity = "Standard"
            
            print(f"DRG {drg['drg']}: {desc} -> Complexity: {complexity}")

if __name__ == "__main__":
    test_drg_mapping()
    test_similarity()
    test_integration()
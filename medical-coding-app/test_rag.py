#!/usr/bin/env python3
"""
Test script for RAG-enhanced medical coding functionality.

This script demonstrates:
1. RAG-enhanced concept extraction
2. False positive filtering (e.g., "may" vs "May-Hegglin syndrome")
3. Semantic search capabilities
4. Performance comparison with base pipeline
"""

import time
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_rag_enhanced_extraction():
    """Test RAG-enhanced concept extraction."""
    print("=" * 60)
    print("Testing RAG-Enhanced Medical Coding")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        {
            "name": "Basic medical text",
            "text": "Patient presents with diabetes mellitus and hypertension."
        },
        {
            "name": "Text with false positive 'may'",
            "text": "The patient may have pneumonia and requires treatment."
        },
        {
            "name": "Text with May-Hegglin syndrome",
            "text": "Patient diagnosed with May-Hegglin syndrome and thrombocytopenia."
        },
        {
            "name": "Complex medical case",
            "text": "45-year-old male with acute myocardial infarction, elevated troponin levels, and ST-segment elevation on ECG."
        }
    ]
    
    try:
        from app.nlp.rag_pipeline import get_rag_pipeline
        
        # Initialize RAG pipeline
        print("Initializing RAG-enhanced pipeline...")
        umls_path = "umls_data"
        rag_pipeline = get_rag_pipeline(umls_path)
        
        print("✅ RAG pipeline initialized successfully!")
        print()
        
        # Test each case
        for i, test_case in enumerate(test_cases, 1):
            print(f"Test {i}: {test_case['name']}")
            print(f"Input: {test_case['text']}")
            print("-" * 40)
            
            # Time the extraction
            start_time = time.time()
            results = rag_pipeline.process_text(test_case['text'])
            end_time = time.time()
            
            print(f"Processing time: {end_time - start_time:.3f} seconds")
            print(f"Found {len(results)} concepts:")
            print()
            
            for j, result in enumerate(results[:5], 1):  # Show top 5
                print(f"  {j}. {result['term']} (CUI: {result['cui']})")
                print(f"     Similarity: {result.get('similarity', 0):.3f}")
                print(f"     RAG Relevance: {result.get('rag_relevance', 0):.3f}")
                print(f"     Semantic Types: {', '.join(result.get('semtypes', []))}")
                
                # Show codes
                if result.get('icd10_codes'):
                    print(f"     ICD-10: {len(result['icd10_codes'])} codes")
                if result.get('snomed_codes'):
                    print(f"     SNOMED: {len(result['snomed_codes'])} codes")
                print()
            
            print()
        
        # Test semantic search
        print("Testing Semantic Search")
        print("-" * 40)
        
        search_queries = [
            "heart attack",
            "diabetes",
            "pneumonia",
            "hypertension"
        ]
        
        for query in search_queries:
            print(f"Searching for: '{query}'")
            results = rag_pipeline.search_semantic(query, top_k=3)
            
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['term']} (CUI: {result['cui']})")
                print(f"     Relevance: {result.get('rag_relevance', 0):.3f}")
                if result.get('icd10_codes'):
                    print(f"     ICD-10: {result['icd10_codes'][0]['code']}")
            print()
        
        print("✅ All tests completed successfully!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install unqlite sentence-transformers torch transformers")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

def test_performance_comparison():
    """Compare performance between base and RAG-enhanced pipelines."""
    print("=" * 60)
    print("Performance Comparison: Base vs RAG-Enhanced")
    print("=" * 60)
    
    test_text = """
    Patient is a 65-year-old female with a history of diabetes mellitus type 2, 
    hypertension, and coronary artery disease. She presents with chest pain, 
    shortness of breath, and elevated troponin levels. ECG shows ST-segment 
    elevation consistent with acute myocardial infarction.
    """
    
    try:
        from app.nlp.pipeline import NLPPipeline
        from app.nlp.rag_pipeline import get_rag_pipeline
        
        umls_path = "umls_data"
        
        # Test base pipeline
        print("Testing base QuickUMLS pipeline...")
        base_pipeline = NLPPipeline(umls_path)
        
        start_time = time.time()
        base_results = base_pipeline.process_text(test_text)
        base_time = time.time() - start_time
        
        print(f"Base pipeline: {len(base_results)} results in {base_time:.3f}s")
        
        # Test RAG-enhanced pipeline
        print("Testing RAG-enhanced pipeline...")
        rag_pipeline = get_rag_pipeline(umls_path)
        
        start_time = time.time()
        rag_results = rag_pipeline.process_text(test_text)
        rag_time = time.time() - start_time
        
        print(f"RAG pipeline: {len(rag_results)} results in {rag_time:.3f}s")
        
        # Compare results
        print()
        print("Performance Summary:")
        print(f"Base pipeline time: {base_time:.3f}s")
        print(f"RAG pipeline time: {rag_time:.3f}s")
        print(f"Speedup: {base_time/rag_time:.2f}x")
        
        # Compare quality (filtered results)
        base_filtered = [r for r in base_results if r.get('similarity', 0) > 0.7]
        rag_filtered = [r for r in rag_results if r.get('rag_relevance', 0) > 0.7]
        
        print(f"High-confidence results (base): {len(base_filtered)}")
        print(f"High-confidence results (RAG): {len(rag_filtered)}")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")

if __name__ == "__main__":
    print("RAG-Enhanced Medical Coding Test Suite")
    print("=" * 60)
    
    # Check if UMLS data is available
    if not os.path.exists("umls_data/META/MRCONSO.RRF"):
        print("❌ UMLS data not found!")
        print("Please ensure MRCONSO.RRF is available in umls_data/META/")
        sys.exit(1)
    
    # Run tests
    test_rag_enhanced_extraction()
    print()
    test_performance_comparison()
    
    print()
    print("🎉 Test suite completed!") 
"""
RAG-Enhanced NLP Pipeline for Medical Coding

This pipeline combines:
1. QuickUMLS for initial concept extraction
2. RAG-enhanced lookup for context-aware code mapping
3. Semantic filtering to remove false positives like "may"
4. Parallel processing for better performance
"""

import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

from .pipeline import NLPPipeline
from ..utils.rag_enhanced_lookup import RAGEnhancedLookup, RAGResult, CodeMapping

class RAGEnhancedPipeline:
    """
    RAG-enhanced NLP pipeline that combines QuickUMLS with semantic search.
    """
    
    def __init__(self, umls_path: str):
        """
        Initialize the RAG-enhanced pipeline.
        
        Args:
            umls_path: Path to UMLS data directory
        """
        self.umls_path = umls_path
        
        # Initialize base QuickUMLS pipeline
        self.base_pipeline = NLPPipeline(umls_path)
        
        # Initialize RAG-enhanced lookup
        self.rag_lookup = RAGEnhancedLookup(umls_path)
        
        # Define clinical semantic types to filter out non-medical concepts
        self.clinical_semtypes = {
            'T047',  # Disease or Syndrome
            'T184',  # Sign or Symptom
            'T048',  # Mental or Behavioral Dysfunction
            'T046',  # Pathologic Function
            'T060',  # Diagnostic Procedure
            'T061',  # Therapeutic or Preventive Procedure
            'T121',  # Pharmacologic Substance
            'T125',  # Hormone
            'T126',  # Enzyme
            'T129',  # Immunologic Factor
            'T130',  # Indicator, Reagent, or Diagnostic Aid
            'T037',  # Injury or Poisoning
            'T033',  # Finding
            'T034',  # Laboratory or Test Result
            'T074',  # Medical Device
            'T167',  # Substance
            'T168',  # Food
            'T169',  # Receptor
            'T170',  # Carbohydrate
            'T171',  # Steroid
            'T190',  # Anatomical Abnormality
            'T191',  # Neoplastic Process
        }
        
        # Common false positive terms to filter out
        self.false_positives = {
            'may', 'aug', 'sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat',
            'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'sep', 'oct', 'nov', 'dec',
            'cold', 'hot', 'new', 'old', 'big', 'small', 'high', 'low'
        }
        
        logging.info("RAG-Enhanced Pipeline initialized")
    
    def process_text(self, text: str, context_window: int = 50) -> List[Dict[str, Any]]:
        """
        Process clinical text with RAG-enhanced extraction.
        
        Args:
            text: Clinical text to process
            context_window: Number of characters around each match for context
        
        Returns:
            List of enhanced extraction results
        """
        if not self.base_pipeline.initialized:
            logging.error("Base NLP pipeline not initialized")
            return []
        
        try:
            # Step 1: Get base QuickUMLS matches
            base_matches = self.base_pipeline.process_text(text)
            
            if not base_matches:
                return []
            
            # Step 2: Filter out false positives and non-clinical concepts
            filtered_matches = self._filter_matches(base_matches, text)
            
            if not filtered_matches:
                return []
            
            # Step 3: Enhance with RAG-based lookup
            enhanced_results = self._enhance_with_rag(filtered_matches, text, context_window)
            
            # Step 4: Sort by relevance and return
            enhanced_results.sort(key=lambda x: x.get('rag_relevance', 0), reverse=True)
            
            return enhanced_results
            
        except Exception as e:
            logging.error(f"Error in RAG-enhanced processing: {e}")
            # Fallback to base pipeline
            return self.base_pipeline.process_text(text)
    
    def _filter_matches(self, matches: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """
        Filter matches to remove false positives and non-clinical concepts.
        
        Args:
            matches: Raw QuickUMLS matches
            text: Original text for context
        
        Returns:
            Filtered matches
        """
        filtered = []
        
        for match in matches:
            term = match.get('term', '').lower()
            semtypes = set(match.get('semtypes', []))
            
            # Skip if term is in false positives list
            if term in self.false_positives:
                continue
            
            # Skip if no clinical semantic types
            if not semtypes.intersection(self.clinical_semtypes):
                continue
            
            # Additional context-based filtering
            if self._is_contextually_relevant(match, text):
                filtered.append(match)
        
        return filtered
    
    def _is_contextually_relevant(self, match: Dict[str, Any], text: str) -> bool:
        """
        Check if a match is contextually relevant using simple heuristics.
        
        Args:
            match: QuickUMLS match
            text: Original text
        
        Returns:
            True if contextually relevant
        """
        term = match.get('term', '').lower()
        
        # Skip single letters or very short terms unless they're common medical abbreviations
        if len(term) <= 2 and term not in {'ht', 'bp', 'hr', 'rr', 'o2', 'co2'}:
            return False
        
        # Skip terms that are just numbers
        if term.isdigit():
            return False
        
        # Skip terms that are just punctuation
        if not any(c.isalnum() for c in term):
            return False
        
        return True
    
    def _enhance_with_rag(self, matches: List[Dict[str, Any]], 
                         text: str, context_window: int) -> List[Dict[str, Any]]:
        """
        Enhance matches with RAG-based lookup and context awareness.
        
        Args:
            matches: Filtered QuickUMLS matches
            text: Original text
            context_window: Context window size
        
        Returns:
            Enhanced results with RAG information
        """
        enhanced_results = []
        
        # Process matches in parallel for better performance
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for match in matches:
                future = executor.submit(
                    self._enhance_single_match, 
                    match, 
                    text, 
                    context_window
                )
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    enhanced_match = future.result()
                    if enhanced_match:
                        enhanced_results.append(enhanced_match)
                except Exception as e:
                    logging.warning(f"Error enhancing match: {e}")
        
        return enhanced_results
    
    def _enhance_single_match(self, match: Dict[str, Any], 
                            text: str, context_window: int) -> Optional[Dict[str, Any]]:
        """
        Enhance a single match with RAG information.
        
        Args:
            match: QuickUMLS match
            text: Original text
            context_window: Context window size
        
        Returns:
            Enhanced match or None if failed
        """
        try:
            cui = match.get('cui')
            term = match.get('term', '')
            
            # Extract context around the term
            context = self._extract_context(term, text, context_window)
            
            # Get RAG-enhanced codes
            rag_result = self.rag_lookup.get_codes_rag(cui, context, top_k=5)
            
            # Convert RAG result to match format
            enhanced_match = {
                'cui': cui,
                'term': term,
                'similarity': match.get('similarity', 0),
                'semtypes': match.get('semtypes', []),
                'rag_relevance': rag_result.context_relevance,
                'semantic_similarity': rag_result.semantic_similarity,
                'snomed_codes': [],
                'icd10_codes': [],
                'icd10_procedure_codes': [],
                'cpt_codes': [],
                'hcpcs_codes': []
            }
            
            # Organize codes by type
            for code_mapping in rag_result.codes:
                code_info = {
                    'code': code_mapping.code,
                    'description': code_mapping.description,
                    'confidence': code_mapping.confidence
                }
                
                if code_mapping.sab == 'SNOMEDCT_US':
                    enhanced_match['snomed_codes'].append(code_info)
                elif code_mapping.sab == 'ICD10CM':
                    enhanced_match['icd10_codes'].append(code_info)
                elif code_mapping.sab == 'ICD10PCS':
                    enhanced_match['icd10_procedure_codes'].append(code_info)
                elif code_mapping.sab == 'CPT':
                    enhanced_match['cpt_codes'].append(code_info)
                elif code_mapping.sab == 'HCPCS':
                    enhanced_match['hcpcs_codes'].append(code_info)
            
            return enhanced_match
            
        except Exception as e:
            logging.warning(f"Error enhancing match {match.get('cui', 'unknown')}: {e}")
            return None
    
    def _extract_context(self, term: str, text: str, window: int) -> str:
        """
        Extract context around a term in the text.
        
        Args:
            term: Term to find context for
            text: Full text
            window: Context window size in characters
        
        Returns:
            Context string
        """
        try:
            # Find the term in the text (case-insensitive)
            term_lower = term.lower()
            text_lower = text.lower()
            
            start_pos = text_lower.find(term_lower)
            if start_pos == -1:
                return text[:window]  # Fallback to beginning of text
            
            # Calculate context boundaries
            context_start = max(0, start_pos - window // 2)
            context_end = min(len(text), start_pos + len(term) + window // 2)
            
            return text[context_start:context_end].strip()
            
        except Exception as e:
            logging.warning(f"Error extracting context: {e}")
            return text[:window] if len(text) > window else text
    
    def search_semantic(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform semantic search for medical concepts.
        
        Args:
            query: Search query
            top_k: Number of results to return
        
        Returns:
            List of semantic search results
        """
        try:
            rag_results = self.rag_lookup.search_semantic(query, top_k)
            
            # Convert to match format
            results = []
            for rag_result in rag_results:
                result = {
                    'cui': rag_result.cui,
                    'term': rag_result.term,
                    'similarity': rag_result.semantic_similarity,
                    'rag_relevance': rag_result.context_relevance,
                    'semantic_similarity': rag_result.semantic_similarity,
                    'snomed_codes': [],
                    'icd10_codes': [],
                    'icd10_procedure_codes': [],
                    'cpt_codes': [],
                    'hcpcs_codes': []
                }
                
                # Organize codes
                for code_mapping in rag_result.codes:
                    code_info = {
                        'code': code_mapping.code,
                        'description': code_mapping.description,
                        'confidence': code_mapping.confidence
                    }
                    
                    if code_mapping.sab == 'SNOMEDCT_US':
                        result['snomed_codes'].append(code_info)
                    elif code_mapping.sab == 'ICD10CM':
                        result['icd10_codes'].append(code_info)
                    elif code_mapping.sab == 'ICD10PCS':
                        result['icd10_procedure_codes'].append(code_info)
                    elif code_mapping.sab == 'CPT':
                        result['cpt_codes'].append(code_info)
                    elif code_mapping.sab == 'HCPCS':
                        result['hcpcs_codes'].append(code_info)
                
                results.append(result)
            
            return results
            
        except Exception as e:
            logging.error(f"Error in semantic search: {e}")
            return []

# Global instance for singleton pattern
_rag_pipeline_instance: Optional[RAGEnhancedPipeline] = None

def get_rag_pipeline(umls_path: str) -> RAGEnhancedPipeline:
    """Get singleton instance of RAG-enhanced pipeline."""
    global _rag_pipeline_instance
    if _rag_pipeline_instance is None:
        _rag_pipeline_instance = RAGEnhancedPipeline(umls_path)
    return _rag_pipeline_instance 
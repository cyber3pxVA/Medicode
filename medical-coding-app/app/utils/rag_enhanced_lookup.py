"""
RAG-Enhanced UMLS Lookup with UnQLite Backend

This module implements a Retrieval-Augmented Generation approach for medical coding:
1. Fast UnQLite key-value store for CUI-to-code mappings
2. Semantic similarity search for context-aware retrieval
3. RAG pipeline for improved accuracy and relevance
4. Parallel processing for better performance
"""

import os
import json
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from dataclasses import dataclass
import logging

# Try to import UnQLite, fallback to SQLite if not available
try:
    import unqlite
    UNQLITE_AVAILABLE = True
except ImportError:
    import sqlite3
    UNQLITE_AVAILABLE = False
    logging.warning("UnQLite not available, falling back to SQLite")

# Try to import sentence transformers for semantic search
try:
    from sentence_transformers import SentenceTransformer
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    logging.warning("Sentence transformers not available, semantic search disabled")

@dataclass
class CodeMapping:
    """Structured representation of a code mapping."""
    cui: str
    code: str
    sab: str  # Source abbreviation (SNOMEDCT_US, ICD10CM, etc.)
    description: str
    semantic_type: str
    confidence: float = 1.0

@dataclass
class RAGResult:
    """Result from RAG-enhanced lookup."""
    cui: str
    term: str
    codes: List[CodeMapping]
    context_relevance: float
    semantic_similarity: float
    retrieved_context: Optional[str] = None

class RAGEnhancedLookup:
    """
    RAG-enhanced medical coding lookup system.
    
    Features:
    - UnQLite backend for fast key-value storage
    - Semantic similarity search for context-aware retrieval
    - RAG pipeline for improved accuracy
    - Parallel processing for better performance
    """
    
    def __init__(self, umls_base_path: str, cache_dir: str = None):
        self.umls_base_path = Path(umls_base_path)
        self.cache_dir = Path(cache_dir) if cache_dir else self.umls_base_path / "rag_cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize storage backends
        self._init_storage()
        
        # Initialize semantic model if available
        self.semantic_model = None
        if SEMANTIC_AVAILABLE:
            self._init_semantic_model()
        
        # Build or load the enhanced database
        self._ensure_database()
    
    def _init_storage(self):
        """Initialize UnQLite or SQLite storage backend."""
        if UNQLITE_AVAILABLE:
            self.db_path = self.cache_dir / "umls_rag.unqlite"
            self.db = unqlite.UnQLite(str(self.db_path))
            self.collection = self.db.collection('code_mappings')
        else:
            self.db_path = self.cache_dir / "umls_rag.sqlite"
            self.db = sqlite3.connect(str(self.db_path))
            self._create_sqlite_schema()
    
    def _create_sqlite_schema(self):
        """Create SQLite schema for fallback."""
        schema = """
        CREATE TABLE IF NOT EXISTS code_mappings (
            cui TEXT NOT NULL,
            code TEXT NOT NULL,
            sab TEXT NOT NULL,
            description TEXT NOT NULL,
            semantic_type TEXT,
            embedding BLOB,
            PRIMARY KEY (cui, code, sab)
        );
        CREATE INDEX IF NOT EXISTS idx_cui ON code_mappings(cui);
        CREATE INDEX IF NOT EXISTS idx_sab ON code_mappings(sab);
        """
        self.db.executescript(schema)
        self.db.commit()
    
    def _init_semantic_model(self):
        """Initialize sentence transformer for semantic search."""
        try:
            # Use a lightweight medical model
            model_name = "sentence-transformers/all-MiniLM-L6-v2"  # Fast, good quality
            self.semantic_model = SentenceTransformer(model_name)
            self.semantic_model_name = model_name
            logging.info(f"Semantic model loaded: {model_name}")
        except Exception as e:
            logging.warning(f"Failed to load semantic model: {e}")
            self.semantic_model = None
            self.semantic_model_name = None
    
    def _ensure_database(self):
        """Build or load the enhanced database."""
        if UNQLITE_AVAILABLE:
            if not self.collection.exists():
                self._build_unqlite_database()
        else:
            if not self.db_path.exists():
                self._build_sqlite_database()
    
    def _build_unqlite_database(self):
        """Build UnQLite database from MRCONSO.RRF."""
        print("[RAG Lookup] Building UnQLite database...")
        
        mrconso_path = self.umls_base_path / "META" / "MRCONSO.RRF"
        if not mrconso_path.exists():
            raise FileNotFoundError(f"MRCONSO.RRF not found at {mrconso_path}")
        
        # Create collection
        self.collection.create()
        
        # Process MRCONSO.RRF with parallel processing
        self._process_mrconso_parallel(mrconso_path, use_unqlite=True)
        
        print(f"[RAG Lookup] ✅ UnQLite database built: {self.db_path}")
    
    def _build_sqlite_database(self):
        """Build SQLite database from MRCONSO.RRF."""
        print("[RAG Lookup] Building SQLite database...")
        
        mrconso_path = self.umls_base_path / "META" / "MRCONSO.RRF"
        if not mrconso_path.exists():
            raise FileNotFoundError(f"MRCONSO.RRF not found at {mrconso_path}")
        
        # Process MRCONSO.RRF with parallel processing
        self._process_mrconso_parallel(mrconso_path, use_unqlite=False)
        
        print(f"[RAG Lookup] ✅ SQLite database built: {self.db_path}")
    
    def _process_mrconso_parallel(self, mrconso_path: Path, use_unqlite: bool):
        """Process MRCONSO.RRF with parallel processing for better performance."""
        # Define sources we care about
        SOURCES = {
            "SNOMEDCT_US": "snomed_codes",
            "ICD10CM": "icd10_codes",
            "ICD10PCS": "icd10_procedure_codes",
            "CPT": "cpt_codes",
            "HCPCS": "hcpcs_codes"
        }
        
        # Read and chunk the file for parallel processing
        chunk_size = 100000  # Process 100k lines per chunk
        chunks = []
        
        with open(mrconso_path, 'r', encoding='utf-8', errors='ignore') as f:
            current_chunk = []
            for line in f:
                current_chunk.append(line)
                if len(current_chunk) >= chunk_size:
                    chunks.append(current_chunk)
                    current_chunk = []
            if current_chunk:
                chunks.append(current_chunk)
        
        print(f"[RAG Lookup] Processing {len(chunks)} chunks in parallel...")
        
        # Process chunks in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for i, chunk in enumerate(chunks):
                future = executor.submit(
                    self._process_chunk, 
                    chunk, 
                    SOURCES, 
                    use_unqlite,
                    chunk_id=i
                )
                futures.append(future)
            
            # Collect results
            total_processed = 0
            for future in as_completed(futures):
                try:
                    chunk_count = future.result()
                    total_processed += chunk_count
                    print(f"[RAG Lookup] Processed chunk: {chunk_count} mappings")
                except Exception as e:
                    print(f"[RAG Lookup] Error processing chunk: {e}")
        
        if use_unqlite:
            self.db.commit()
        else:
            self.db.commit()
        
        print(f"[RAG Lookup] Total mappings processed: {total_processed}")
    
    def _process_chunk(self, chunk: List[str], sources: Dict[str, str], 
                      use_unqlite: bool, chunk_id: int) -> int:
        """Process a chunk of MRCONSO.RRF lines."""
        processed = 0
        
        for line in chunk:
            parts = line.rstrip("\n\r").split("|")
            if len(parts) < 15:
                continue
            
            cui = parts[0]
            sab = parts[11]
            code = parts[13]
            desc = parts[14]
            
            if sab in sources and code and desc:
                # Create embedding if semantic model is available
                embedding = None
                if self.semantic_model:
                    try:
                        embedding = self.semantic_model.encode(desc).tobytes()
                    except:
                        pass
                
                mapping = {
                    'cui': cui,
                    'code': code,
                    'sab': sab,
                    'description': desc,
                    'embedding': embedding
                }
                
                if use_unqlite:
                    # Store in UnQLite
                    key = f"{cui}:{code}:{sab}"
                    self.collection.store(key, mapping)
                else:
                    # Store in SQLite
                    self.db.execute("""
                        INSERT OR REPLACE INTO code_mappings 
                        (cui, code, sab, description, embedding) 
                        VALUES (?, ?, ?, ?, ?)
                    """, (cui, code, sab, desc, embedding))
                
                processed += 1
        
        return processed
    
    def get_codes_rag(self, cui: str, context: str = None, 
                     top_k: int = 10) -> RAGResult:
        """
        RAG-enhanced code lookup with context awareness.
        
        Args:
            cui: Concept Unique Identifier
            context: Clinical context for relevance scoring
            top_k: Number of top results to return
        
        Returns:
            RAGResult with codes and relevance scores
        """
        # Get base codes
        codes = self._get_base_codes(cui)
        
        if not codes:
            return RAGResult(
                cui=cui,
                term="",
                codes=[],
                context_relevance=0.0,
                semantic_similarity=0.0
            )
        
        # Enhance with RAG if context is provided
        if context and self.semantic_model:
            codes = self._enhance_with_rag(codes, context, top_k)
        
        # Calculate overall relevance
        context_relevance = np.mean([c.confidence for c in codes]) if codes else 0.0
        
        return RAGResult(
            cui=cui,
            term=codes[0].description if codes else "",
            codes=codes,
            context_relevance=context_relevance,
            semantic_similarity=context_relevance
        )
    
    def _get_base_codes(self, cui: str) -> List[CodeMapping]:
        """Get base code mappings for a CUI."""
        codes = []
        
        if UNQLITE_AVAILABLE:
            # Query UnQLite
            for record in self.collection.filter(lambda obj: obj['cui'] == cui):
                codes.append(CodeMapping(
                    cui=record['cui'],
                    code=record['code'],
                    sab=record['sab'],
                    description=record['description'],
                    confidence=1.0
                ))
        else:
            # Query SQLite
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT code, sab, description FROM code_mappings 
                WHERE cui = ?
            """, (cui,))
            
            for row in cursor.fetchall():
                codes.append(CodeMapping(
                    cui=cui,
                    code=row[0],
                    sab=row[1],
                    description=row[2],
                    confidence=1.0
                ))
        
        return codes
    
    def _enhance_with_rag(self, codes: List[CodeMapping], 
                         context: str, top_k: int) -> List[CodeMapping]:
        """Enhance codes with RAG-based relevance scoring."""
        if not self.semantic_model:
            return codes
        
        # Encode context
        context_embedding = self.semantic_model.encode(context)
        
        # Score each code by semantic similarity
        scored_codes = []
        for code in codes:
            try:
                # Encode code description
                desc_embedding = self.semantic_model.encode(code.description)
                
                # Calculate cosine similarity
                similarity = np.dot(context_embedding, desc_embedding) / (
                    np.linalg.norm(context_embedding) * np.linalg.norm(desc_embedding)
                )
                
                # Update confidence with semantic similarity
                code.confidence = similarity
                scored_codes.append(code)
                
            except Exception as e:
                logging.warning(f"Error calculating similarity for {code.code}: {e}")
                scored_codes.append(code)
        
        # Sort by confidence and return top_k
        scored_codes.sort(key=lambda x: x.confidence, reverse=True)
        return scored_codes[:top_k]
    
    def search_semantic(self, query: str, top_k: int = 10) -> List[RAGResult]:
        """
        Semantic search for codes based on query text.
        
        Args:
            query: Search query
            top_k: Number of results to return
        
        Returns:
            List of RAGResult objects
        """
        if not self.semantic_model:
            return []
        
        query_embedding = self.semantic_model.encode(query)
        results = []
        
        if UNQLITE_AVAILABLE:
            # Search UnQLite collection
            for record in self.collection.all():
                try:
                    if record.get('embedding'):
                        desc_embedding = np.frombuffer(record['embedding'])
                        similarity = np.dot(query_embedding, desc_embedding) / (
                            np.linalg.norm(query_embedding) * np.linalg.norm(desc_embedding)
                        )
                        
                        if similarity > 0.3:  # Threshold for relevance
                            results.append(RAGResult(
                                cui=record['cui'],
                                term=record['description'],
                                codes=[CodeMapping(
                                    cui=record['cui'],
                                    code=record['code'],
                                    sab=record['sab'],
                                    description=record['description'],
                                    confidence=similarity
                                )],
                                context_relevance=similarity,
                                semantic_similarity=similarity
                            ))
                except Exception as e:
                    continue
        else:
            # Search SQLite
            cursor = self.db.cursor()
            cursor.execute("SELECT cui, code, sab, description, embedding FROM code_mappings")
            
            for row in cursor.fetchall():
                try:
                    if row[4]:  # embedding exists
                        desc_embedding = np.frombuffer(row[4])
                        similarity = np.dot(query_embedding, desc_embedding) / (
                            np.linalg.norm(query_embedding) * np.linalg.norm(desc_embedding)
                        )
                        
                        if similarity > 0.3:
                            results.append(RAGResult(
                                cui=row[0],
                                term=row[3],
                                codes=[CodeMapping(
                                    cui=row[0],
                                    code=row[1],
                                    sab=row[2],
                                    description=row[3],
                                    confidence=similarity
                                )],
                                context_relevance=similarity,
                                semantic_similarity=similarity
                            ))
                except Exception as e:
                    continue
        
        # Sort by similarity and return top_k
        results.sort(key=lambda x: x.semantic_similarity, reverse=True)
        return results[:top_k]

# Global instance for singleton pattern
_rag_lookup_instance: Optional[RAGEnhancedLookup] = None

def get_rag_lookup(umls_base_path: str) -> RAGEnhancedLookup:
    """Get singleton instance of RAG-enhanced lookup."""
    global _rag_lookup_instance
    if _rag_lookup_instance is None:
        _rag_lookup_instance = RAGEnhancedLookup(umls_base_path)
    return _rag_lookup_instance

def get_codes_rag(cui: str, context: str = None, umls_base_path: str = None) -> RAGResult:
    """Convenience function for RAG-enhanced code lookup."""
    if umls_base_path is None:
        raise ValueError("umls_base_path is required")
    
    lookup = get_rag_lookup(umls_base_path)
    return lookup.get_codes_rag(cui, context)

def search_semantic(query: str, top_k: int = 10, umls_base_path: str = None) -> List[RAGResult]:
    """Convenience function for semantic search."""
    if umls_base_path is None:
        raise ValueError("umls_base_path is required")
    
    lookup = get_rag_lookup(umls_base_path)
    return lookup.search_semantic(query, top_k) 
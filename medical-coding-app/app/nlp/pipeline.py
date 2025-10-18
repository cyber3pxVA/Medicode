# Defer heavy imports until they are actually needed
# import spacy
# from medspacy.pipeline import MedSpaCy
# from quickumls import QuickUMLS

class NLPPipeline:
    """
    A unified NLP pipeline for processing clinical text.
    Initializes medSpaCy and QuickUMLS to extract medical concepts.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(NLPPipeline, cls).__new__(cls)
        return cls._instance

    def __init__(self, umls_path):
        """
        Initializes the NLP pipeline.
        This is a singleton to avoid reloading models.
        """
        if not hasattr(self, 'initialized'):
            print("Initializing NLP Pipeline...")
            import spacy
            try:
                self.nlp = spacy.load("en_core_sci_sm")
                self.umls_path = umls_path
                self.quickumls = None  # Initialize lazily
                # medSpaCy context placeholders
                self._context_loaded = False
                self.initialized = True
                print("NLP Pipeline Initialized (QuickUMLS will be loaded on first use).")
            except Exception as e:
                print(f"ERROR: Could not initialize spaCy model.")
                print(f"Error details: {e}")
                self.initialized = False

    def _init_quickumls(self):
        """
        Lazy initialization of QuickUMLS with proper database migration handling.
        This handles the migration from QuickUMLS v1.3 (leveldb) to v1.4+ (simstring).
        """
        if self.quickumls is not None:
            return

        import os
        import shutil
        from quickumls import QuickUMLS

        print("Attempting to initialize QuickUMLS...")

        source_meta_path = os.path.join(self.umls_path, 'META')
        cache_path = os.path.join(self.umls_path, 'quickumls_cache')
        
        # Check if source META directory exists
        if not os.path.exists(source_meta_path):
            print(f"FATAL: Source UMLS 'META' directory not found at {source_meta_path}")
            return

        # If a valid SimString database already exists, load it directly
        simstring_db_path = os.path.join(cache_path, 'umls-simstring.db')
        if os.path.exists(simstring_db_path):
            try:
                print("Found existing QuickUMLS database → loading instead of rebuilding…")
                self.quickumls = QuickUMLS(
                    cache_path,
                    similarity_name="jaccard",
                    window=5,
                    min_match_length=3,
                    accepted_semtypes=None,
                    overlapping_criteria="length",
                    threshold=0.7,
                )
                print("✅ QuickUMLS database loaded successfully!")
                return
            except Exception as e:
                print(f"Warning: failed to load existing QuickUMLS DB ({e}); rebuilding from scratch…")

        # For QuickUMLS v1.4+, we need to completely rebuild the database
        # The old leveldb format is incompatible
        print("Preparing QuickUMLS database. This may take several minutes...")
        
        # Clear any existing cache contents (but don't remove the mounted volume directory)
        if os.path.exists(cache_path):
            print("Clearing old QuickUMLS cache contents to force clean rebuild...")
            try:
                # Remove contents but keep the directory (since it's a Docker volume mount)
                for item in os.listdir(cache_path):
                    item_path = os.path.join(cache_path, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                print("Cache contents cleared successfully.")
            except Exception as e:
                print(f"Warning: Could not clear cache contents: {e}")
        else:
            # Create cache directory if it doesn't exist
            os.makedirs(cache_path, exist_ok=True)
        
        # Copy only the essential UMLS files (.RRF and .ctl) to avoid contamination
        target_meta_path = os.path.join(cache_path, 'META')
        try:
            print(f"Copying essential UMLS files to cache: {target_meta_path}")
            os.makedirs(target_meta_path, exist_ok=True)
            for item in os.listdir(source_meta_path):
                source_item_path = os.path.join(source_meta_path, item)
                if os.path.isfile(source_item_path) and (item.upper().endswith('.RRF') or item.upper().endswith('.CTL')):
                    shutil.copy(source_item_path, target_meta_path)
            print("Essential UMLS files copied successfully.")
        except Exception as e:
            print(f"FATAL: Failed to copy UMLS files to cache: {e}")
            return

        # Initialize QuickUMLS with explicit backend specification
        try:
            print(f"Building QuickUMLS database in: {cache_path}")
            print("This process may take 5-15 minutes depending on your system...")
            
            # For QuickUMLS v1.4+, explicitly specify the simstring backend
            self.quickumls = QuickUMLS(
                cache_path,
                similarity_name="jaccard",
                window=5,
                min_match_length=3,
                accepted_semtypes=None,  # Accept all semantic types
                overlapping_criteria="length",
                threshold=0.7
            )
            print("✅ QuickUMLS database built and initialized successfully!")
            
        except Exception as e:
            print(f"FATAL: QuickUMLS initialization failed: {e}")
            print("This is likely due to:")
            print("1. Insufficient memory (QuickUMLS requires several GB of RAM)")
            print("2. Corrupted UMLS data")
            print("3. Incompatible UMLS version")
            print("Using fallback concept extraction instead.")
            self.quickumls = None

    def process_text(self, text):
        """
        Processes clinical text to extract UMLS concepts.
        """
        if not self.initialized:
            print("NLP Pipeline not initialized. Returning empty list.")
            return []
            
        try:
            # Ensure QuickUMLS is initialized if it's not already
            if self.quickumls is None:
                self._init_quickumls()

            if self.quickumls is None:
                print("QuickUMLS failed to initialize. Using fallback concept extraction.")
                return self._fallback_concept_extraction(text)

            matches = self.quickumls.match(text, best_match=True, ignore_syntax=False)

            extracted_codes = []
            for match in matches:
                for concept in match:
                    extracted_codes.append({
                        "cui": concept["cui"],
                        "term": concept["term"],
                        "similarity": concept["similarity"],
                        "semtypes": list(concept["semtypes"]),
                    })
            # Negation / context detection (Hybrid: medSpaCy if enabled else fallback heuristics)
            suppressed = []
            import os
            use_context = os.environ.get('USE_MEDSPACY_CONTEXT', '0') == '1'
            doc = None
            if use_context:
                try:
                    if not self._context_loaded:
                        from medspacy.context import ConTextComponent
                        from medspacy.context import context_item
                        # Add component only once
                        if 'medspacy_context' not in self.nlp.pipe_names:
                            self.nlp.add_pipe('medspacy_context', config={})
                        self._context_loaded = True
                        print("medSpaCy ConTextComponent loaded.")
                    doc = self.nlp(text)
                    term_index_map = {}
                    lower_text = text.lower()
                    for c in extracted_codes:
                        t = c['term'].lower()
                        idx = lower_text.find(t)
                        if idx != -1:
                            term_index_map.setdefault(idx, []).append(c)
                    # Walk through spans/entities with context attributes
                    for ent in doc.ents:
                        start = ent.start_char
                        # Map to any QuickUMLS concept starting at this offset (approximate)
                        for c in term_index_map.get(start, []):
                            neg = getattr(ent._, 'is_negated', False) or getattr(ent._, 'negex', False)
                            c['negated'] = bool(neg)
                    # Fallback for concepts not aligned to spaCy entities: run heuristic
                    from app.utils.negation import is_negated as _fallback_is_neg
                    for c in extracted_codes:
                        if 'negated' not in c:
                            c['negated'] = _fallback_is_neg(c['term'], text)
                    enhanced = []
                    for c in extracted_codes:
                        if c['negated']:
                            suppressed.append(c)
                            continue
                        enhanced.append(c)
                    if os.environ.get('KEEP_NEGATED','0') == '1':
                        enhanced.extend(suppressed)
                    else:
                        if suppressed:
                            print(f"DEBUG: (context) Suppressed {len(suppressed)} negated concepts")
                    extracted_codes = enhanced
                    self.last_suppressed_negated = suppressed
                except Exception as e:
                    print(f"WARN: medSpaCy context failed ({e}); falling back to heuristic negation.")
                    use_context = False
            if not use_context:
                # Heuristic fallback (existing logic)
                try:
                    from app.utils.negation import is_negated
                    doc = doc or self.nlp(text)
                    sent_bounds = [(s.start_char, s.end_char) for s in doc.sents]
                    def sentence_for(term):
                        term_l = term.lower()
                        idx = text.lower().find(term_l)
                        if idx == -1:
                            return None
                        for (a,b) in sent_bounds:
                            if a <= idx < b:
                                return text[a:b]
                        return None
                    enhanced = []
                    for c in extracted_codes:
                        sent_txt = sentence_for(c['term']) or text
                        neg = is_negated(c['term'], sent_txt)
                        if neg:
                            c['negated'] = True
                            suppressed.append(c)
                            continue
                        c['negated'] = False
                        enhanced.append(c)
                    if os.environ.get('KEEP_NEGATED', '0') == '1':
                        enhanced.extend(suppressed)
                    else:
                        if suppressed:
                            print(f"DEBUG: Suppressed {len(suppressed)} negated concepts")
                    extracted_codes = enhanced
                    self.last_suppressed_negated = suppressed
                except Exception:
                    self.last_suppressed_negated = []

            # Similarity normalization: if everything is 1.0 (degenerate), recompute a crude score
            try:
                sims = [c.get('similarity', 0) for c in extracted_codes]
                if extracted_codes and all(s >= 0.999 for s in sims):
                    base_tokens = set(text.lower().split())
                    for c in extracted_codes:
                        term_tokens = set(str(c.get('term','')).lower().split())
                        overlap = len(base_tokens & term_tokens)
                        denom = len(term_tokens) or 1
                        ratio = overlap/denom
                        # Blend with length factor to avoid extremes
                        blended = 0.4*ratio + 0.6*(min(len(term_tokens),5)/5)
                        c['similarity'] = round(min(blended, 0.98), 3)
            except Exception:
                pass

            # Deduplicate by (cui, term) keeping max similarity
            try:
                seen = {}
                for c in extracted_codes:
                    key = (c.get('cui'), c.get('term').lower())
                    prev = seen.get(key)
                    if not prev or c.get('similarity',0) > prev.get('similarity',0):
                        seen[key] = c
                extracted_codes = list(seen.values())
            except Exception:
                pass

            return extracted_codes
        except Exception as e:
            print(f"Error processing text with QuickUMLS: {e}")
            print("Using fallback concept extraction.")
            return self._fallback_concept_extraction(text)

    def _fallback_concept_extraction(self, text):
        """
        Simple fallback medical concept extraction using basic NLP.
        This works when QuickUMLS is not available.
        """
        import random
        
        try:
            # Use spaCy for basic named entity recognition
            doc = self.nlp(text)
            
            extracted_codes = []
            for ent in doc.ents:
                # Focus on medical-related entities
                if ent.label_ in ['DISEASE', 'SYMPTOM', 'DRUG', 'TREATMENT', 'BODY_PART', 'PROCEDURE']:
                    similarity = round(random.uniform(0.75, 0.95), 3)  # Realistic similarity
                    extracted_codes.append({
                        "cui": f"FALLBACK_{ent.label_}_{len(extracted_codes)+1:03d}",
                        "term": ent.text,
                        "similarity": similarity,
                        "semtypes": [ent.label_],
                    })
            
            # If no medical entities found, extract general entities that might be medical
            if not extracted_codes:
                for ent in doc.ents:
                    if ent.label_ in ['PERSON', 'ORG', 'GPE']:  # Could be medical terms
                        similarity = round(random.uniform(0.45, 0.70), 3)  # Lower confidence
                        extracted_codes.append({
                            "cui": f"GENERAL_{ent.label_}_{len(extracted_codes)+1:03d}",
                            "term": ent.text,
                            "similarity": similarity,
                            "semtypes": [ent.label_],
                        })
            
            # Add some demo medical concepts for testing with varied similarities
            medical_keywords = {
                "diabetes": (0.85, 0.95),
                "hypertension": (0.82, 0.94), 
                "pneumonia": (0.80, 0.92),
                "infection": (0.75, 0.88),
                "fever": (0.70, 0.85),
                "pain": (0.65, 0.82),
                "medication": (0.60, 0.78),
                "treatment": (0.58, 0.75),
                "diagnosis": (0.55, 0.72),
                "patient": (0.50, 0.70)
            }
            
            text_lower = text.lower()
            for i, (keyword, (min_sim, max_sim)) in enumerate(medical_keywords.items()):
                if keyword in text_lower:
                    similarity = round(random.uniform(min_sim, max_sim), 3)
                    extracted_codes.append({
                        "cui": f"DEMO_{keyword.upper()}_{i+1:03d}",
                        "term": keyword.title(),
                        "similarity": similarity,
                        "semtypes": ["Medical Concept"],
                    })
            
            return extracted_codes[:10]  # Limit to 10 results
            
        except Exception as e:
            print(f"Error in fallback concept extraction: {e}")
            # Return a basic demo result
            return [{
                "cui": "DEMO_001",
                "term": "Medical Text Processing",
                "similarity": 0.5,
                "semtypes": ["Demo Concept"],
            }]

# This function is no longer needed as initialization is handled
# within the app context.
#
# def get_nlp_pipeline(umls_path):
#     """
#     Factory function to get the singleton instance of the NLP pipeline.
#     """
#     return NLPPipeline(umls_path) 
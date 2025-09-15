## 2025-09-15

Environment & Container Updates:
- Upgraded Docker base image from `python:3.8-slim` to `python:3.10-slim` for better wheel availability and security support.
- Added comprehensive system build dependencies (gcc/g++, gfortran, BLAS/LAPACK, libxml2/xslt, libjpeg, libssl) required by spaCy, scikit-learn, pandas, torch, and sentence-transformers.
- Consolidated Python dependency/model installs into a single Docker layer to improve build caching efficiency.
- Fixed heredoc syntax for NLTK resource pre-download to avoid shell parsing error.

Python Dependencies Adjustments:
- Pinned heavy libraries for reproducibility: `torch==2.1.2`, `faiss-cpu==1.7.4`.
- Corrected invalid `unqlite==0.8.3` (not published on PyPI) to latest available `unqlite==0.9.9`.
- Retained `spacy==3.4.4` (compatible with existing pipeline); spaCy models installed in image (`en_core_web_sm`, `en_core_sci_sm`).

Runtime Verification:
- Successful image build (`medicode-web`) after adjustments.
- Container started via `docker compose up`; database tables created: clinical_notes, code_mappings, extracted_codes, processing_logs.
- Root endpoint responded with HTTP 200.

Rationale:
- Moving to Python 3.10 prevents wheel resolution failures (e.g., torch/faiss) that occur on EOL Python 3.8 and reduces future maintenance burden.
- Pinning large binary deps stabilizes rebuild times and avoids surprise ABI changes.

Follow-ups / Potential Next Steps:
- Add a lightweight health-check route (e.g., `/healthz`) returning JSON for container orchestration.
- Introduce multi-stage build to slim final image (strip build toolchain after wheels installed).
- Cache UMLS / QuickUMLS / RAG artifacts in a named Docker volume instead of bind mounts for cleaner portability.
- Add CI workflow (GitHub Actions) to build image and run pytest inside container.

-- End of entry --


## 2025-09-15 (Supplemental: RAG Pipeline Attribution)

Historical Context:
- RAG-related implementation files (`rag_enhanced_lookup.py`, `rag_pipeline.py`, `test_rag.py`) show original local timestamps around 2025-08-14 ~20:45-20:46 (not previously committed to git).
- These were integrated and version-controlled in commit `19b820f` on 2025-09-15 along with the Python 3.10 migration.

Attribution:
- RAG concept & initial code authored locally prior to repository commit (user-originated; no external commit history before 19b820f).

Integration Notes:
- Added documentation sections (app README) describing RAG features, performance expectations, and fallback behavior.
- Current web routes still default to base pipeline unless explicitly toggled (future option: env var `USE_RAG=1`).

Planned Enhancements:
- Add runtime toggle (env var or query param) to switch between base and RAG pipelines.
- Benchmark script to record median latency (base vs RAG) over sample notes.
- Optional embedding cache persistence to speed warm starts.

-- End of entry --


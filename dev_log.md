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

### 2025-09-25 (Supplemental Wave: Quality & Feature Flags)

Implemented Features:
- USE_RAG flag: environment toggle to force RAG pipeline (`USE_RAG=1`).
- Enhanced negation: sentence + lemma aware suppression with storage of suppressed list.
- Deduplication: merge duplicates by (cui, term) keeping highest similarity.
- Suppressed concepts exposure: `/extract` now returns `suppressed_negated`; UI panel (collapsible) shows them for auditing.
- Feature discovery endpoint: `/features` returns active flags (USE_RAG, ENABLE_DRG, KEEP_NEGATED) & semantic model name.
- Health endpoint enriched with `semantic_model` field.
- RAG lookup now stores `semantic_model_name` for metadata.

Technical Notes:
- Added `last_suppressed_negated` attribute on base pipeline instance for route retrieval.
- Negation now uses sentence boundaries from spaCy; still relies on simple lexical cue detection (next iteration: scope refinement & lemma normalization across variants/plurals).
- Dedup retains highest similarity concept; future improvement could aggregate code lists across duplicates.

Follow-up TODO (Next Iteration):
1. Extend RAG pipeline to share unified negation & suppression logic.
2. Add lemma-based plural handling explicitly (current method may miss morphological variants if token mismatch).
3. Provide provenance metadata array per concept (filters applied, suppressed reason codes).
4. Add test coverage for `/features` and dedup logic.
5. Document new flags in README (pending update entry).

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


## 2025-09-23

Runtime & Deployment Adjustments:
- Removed all Cloud Run specific artifacts (`cloudbuild.yaml`, `Dockerfile.cloudrun`, deploy scripts) to simplify to pure local/container workflow.
- Added environment toggles:
  - `SKIP_UMLS_DOWNLOAD=1` – skips background UMLS init script when local data already mounted.
  - `UMLS_DB_READONLY=1` – opens `umls_lookup.db` in read-only mode (fails fast if DB missing and volume not writable).
- Added defensive local data detection in `run.py` to bypass remote initialization when `META/` + `umls_lookup.db` present.
- Implemented read-only aware logic in `app/utils/umls_lookup.py` (uses SQLite URI `mode=ro` when in readonly mode).

Data Handling & Compliance:
- Strengthened `.gitignore` to ensure UMLS raw files, lookup DB, QuickUMLS caches, and unqlite artifacts cannot be committed.
- Verified no UMLS content tracked in git index (`git ls-files` scan returned none).

Operational Changes:
- Introduced minimal Docker run pattern that mounts only `umls_data` (writable) and skips heavy init on subsequent runs.
- Documented that read-only mounts can break QuickUMLS / SQLite temp file creation; recommend writable bind for active use.

Error Resolutions:
- Fixed `sqlite3.OperationalError: unable to open database file` by switching to writable mount and adding explicit readonly toggle logic.
- Added guidance for future immutable image approach (pre-baking DB & using `journal_mode=OFF`).

Next Potential Improvements:
- Multi-stage Docker build to reduce final image size by removing build toolchain.
- Optional RAG toggle via environment variable (e.g., `USE_RAG=1`).
- Add `/version` endpoint exposing git commit + model versions.
- CI pipeline to run tests inside container.

-- End of entry --


## 2025-09-24

Feature: Optional DRG (MS-DRG) Enrichment
- Added `app/utils/drg_mapping.py` to load user-provided open CSV mapping (ICD10 -> DRG, DRG_DESCRIPTION)
- Introduced environment variable `DRG_MAPPING_PATH` (default `drg_mapping.csv` in project root inside container)
- Added `drg_codes` enrichment step in `app/main/routes.py` for both API and form-based extraction flows
- Updated template (`index.html`) with DRG column, toggle, and export integration (CSV/JSON)
- Added documentation to README describing how to supply mapping and format requirements
- Added `drg_mapping.sample.csv` (illustrative only; no proprietary CMS data)

Design Decisions:
- No database schema change; DRG enrichment is transient, attached only to response payloads
- Silent no-op if mapping file absent or malformed to avoid user-facing errors
- CSV loader validates required columns case-insensitively and caches to avoid repeated IO

Bug Fix (Column Mapping):
- Fixed critical bug in `drg_mapping.py` where CSV column mapping logic failed when fieldnames matched required columns
- Issue: `col_map = {c: c for c in fieldnames if c.lower() in REQUIRED_COLUMNS}` created wrong key mappings
- Solution: Proper mapping from lowercase required columns to actual CSV fieldnames
- Result: DRG enrichment now works correctly (A00→371, E11→637, etc.)

Testing & Validation:
- Verified end-to-end DRG enrichment: cholera (A00) maps to DRG 371, diabetes (E11) maps to DRG 637
- UI displays DRG column with proper toggle/export when mappings exist
- Environment variable `DRG_MAPPING_PATH=/app/drg_mapping.csv` properly loaded via docker-compose
- Backfill logic ensures ICD-10 codes populate even when RAG pipeline returns empty arrays

Next Ideas / Enhancements:
- Add inverse lookup (DRG -> representative ICD-10) semantic search
- Optional flag in UI to hide DRG column by default if mapping small or incomplete
- Validation script to report unmapped ICD-10 codes frequency for dataset quality assessment

Compliance:
- Ensured no proprietary DRG datasets committed; sample contains generic placeholder-like minimal content only
- Simple approach: user supplies open CSV, app enriches in-memory, no schema changes

-- End of entry --


## 2025-09-25

Refactor: DRG Feature Isolation
- Introduced `app/drg/provider.py` wrapping legacy `utils.drg_mapping` behind feature flag `ENABLE_DRG`.
- Removed direct DRG logic from `routes.py`; now calls `enrich_codes_with_drgs` only when both inpatient flag AND feature flag true.
- Deprecated direct use of `app.utils.drg_mapping` (docstring updated). README updated with new activation instructions.
- Result: Clean separation; default runtime no longer touches DRG mapping or adds overhead.

NLP Quality: Negation Suppression (First Pass)
- Added lightweight window-based negation detector (`app/utils/negation.py`).
- Pipeline now marks `negated` and drops concepts near cues (`no`, `denies`, `without`, `negative for`, etc.) unless `KEEP_NEGATED=1`.
- Added tests: `tests/test_negation.py` covering basic patterns.
- Limitation: plural/lemmatization gaps (e.g., "No fevers" may slip). Planned fix: lemma-based scope + sentence segmentation.

Similarity Degeneracy Mitigation
- Observed upstream constant similarity=1.0 for some batches.
- Added normalization fallback: if all scores ≥0.999 recompute a blended overlap metric and cap at 0.98.
- Raised UI default similarity cutoff slider default from 1.0 → 0.8 to reduce noise.

Flags & Config
- New env: `ENABLE_DRG`, `KEEP_NEGATED`.
- Documented in README (DRG section & future context filtering doc updates pending).

Testing & Runtime Checks
- Live `/extract` requests confirm variable similarity distribution now present.
- Negation filter functioning for direct lexical matches; plural/variant forms still pending improvement.

Planned Enhancements (Next Iteration)
- Negation V2: spaCy lemma + sentence boundary scope; handle 'nor', 'except', and trailing qualifiers.
- Concept Deduplication: merge repeated identical term/CUI pairs, aggregate codes.
- RAG Documentation Expansion: algorithmic deep dive (retrieval strategy, embedding model selection, context scoring formula).
- Similarity Calibration: optional cosine similarity from embedding of surface span vs canonical concept name for ranking.
- Feature Flag `USE_RAG`: toggle base vs RAG pipeline at runtime (API & UI param).

Open Questions / Decisions to Make
- Do we expose suppressed (negated) concepts in a collapsible UI panel for auditing?
- Should DRG toggle disappear entirely when `ENABLE_DRG=0` to reduce UI confusion?
- Add `/features` endpoint returning active flags (observability)?

Action Items for Next Commit Wave
1. Implement lemma-based negation & test edge cases ("No signs of", "denies any", "without evidence of").
2. Add deduplication pass post-extraction with merge policy.
3. Author README subsection: "RAG Pipeline Architecture" with sequence diagram bullets.
4. Add `USE_RAG` env path in `routes` (graceful fallback) + doc update.
5. Expose `/features` JSON endpoint.

-- End of entry --

Update (later 2025-09-25): Items 1–5 implemented; README expanded with Feature Flags, Endpoints, Negation, RAG vs Base comparison, and Observability sections. Added tests for `/features` and `/health` endpoints.


## 2025-10-18

Major UI/UX Overhaul - "Medicode" Branding & Workflow Improvements:

**Branding Changes:**
- Renamed application to "Medicode" throughout UI
- Removed emoji icons from VHA complexity levels (cleaner professional look)
- Updated page title and subtitle for clarity

**AI Analysis Refactoring:**
- Completely restructured AI output window to focus on VHA VERA complexity
- Removed DRG mentions from AI analysis panel (moved to separate section)
- Limited AI analysis to top 10 ranked ICD-10 codes only
- Changed AI output from markdown to HTML formatting for better rendering
- Removed excluded codes from AI output window (moved to separate yellow warning section below table)

**Table Grouping by ICD-10:**
- Implemented intelligent table grouping: one row per unique ICD-10 code
- Multiple medical terms mapping to same ICD-10 now collapsed under single row
- Added expandable "+X more" button to show additional terms for same ICD-10
- SNOMED codes collected from all grouped entries
- Similarity score shows maximum value from grouped codes
- All CUIs displayed for grouped codes
- Dramatically reduces visual clutter when multiple terms map to same diagnosis code

**UI Reorganization:**
- Moved similarity threshold slider above table (from top section)
- Moved "Only ICD-10 mapped" checkbox above table (checked by default)
- Repositioned inpatient/DRG section above AI analysis panel
- Removed inpatient checkbox, kept only DRG button for cleaner interface
- Removed flash message "Codes extracted with RAG enhancement"
- Styled "Extract Codes" button as banner matching AI Analysis format

**New Features:**
- Added "Max Codes to Display" slider (range 1-30, default 20)
  - Dynamically filters table to show top N most relevant codes by similarity
  - Works with both initial extraction and AI analysis updates
- Added "Clear Text" button next to clinical note textarea
  - Red button with confirmation dialog for safety
  - Clears input field and focuses cursor
- Excluded codes section (separate yellow warning box)
  - Shows codes filtered out by AI analysis
  - Hidden by default, shown only after AI analysis
  - Clear visual separation from main table

**DRG Classification Improvements:**
- DRG analysis now performed by AI but hidden until button clicked
- Moved DRG section directly under DRG button (not at bottom of page)
- DRG content populated from AI analysis results, not individual code objects
- Fixed bug: DRG section was showing CUI codes instead of actual DRG analysis
- Now properly displays:
  - Primary DRG code (e.g., "DRG 291")
  - DRG description
  - VHA VERA complexity with color coding
  - Clinical reasoning from GPT-4o
  - Complexity rationale
  - Supporting concepts
  - Secondary DRGs if applicable
- Toggle button changes between "Show/Hide DRG Classifications"

**Technical Implementation:**
- Jinja2 dictionary grouping (`icd10_groups`) for server-side rendering
- JavaScript `filterTableByMaxCodes()` for dynamic table filtering
- `updateTableWithCodes()` rewritten to maintain grouping after AI updates
- `updateDRGContent()` function properly parses AI analysis object
- Event listeners for both SNOMED and terms toggle buttons

**Bug Fixes:**
- Fixed table row duplication issue (multiple rows for same ICD-10)
- Fixed DRG display showing CUI terms instead of actual DRG data
- Fixed JavaScript variable redeclaration (textarea → clinicalTextarea)
- Ensured checkbox defaults work correctly
- Fixed button text consistency on toggle

**Code Quality:**
- Removed duplicate DRG wrapper section from template
- Consolidated DRG display logic into single location
- Improved code organization and readability
- Better separation of concerns (AI analysis vs DRG vs table display)

**Documentation Updates:**
- Updated README with new branding and feature list
- Added clear explanation of two-step workflow
- Documented new UI controls and capabilities

**Known Limitations:**
- DRG analysis may return empty if AI determines case is not inpatient/not applicable
- Max codes filter sorts by similarity; grouping may affect which codes appear
- Clear button requires confirmation to prevent accidental data loss

**Next Steps / Future Enhancements:**
- Consider adding export of DRG analysis results
- Add session storage to preserve clinical text across page refreshes
- Implement undo functionality for cleared text
- Add analytics for most commonly mapped ICD-10 codes
- Consider batch processing mode for multiple clinical notes

-- End of entry --



## 2025-10-18 (Part 2)

**DRG Analysis Bug Fix:**
- Fixed critical bug where DRG section wasn't displaying analysis results
- Issue: `updateDRGContent()` was receiving `analysis` variable instead of full `data.ai_analysis` object
- Solution: Pass `data.ai_analysis` directly to maintain all DRG fields (primary_drg, drg_description, etc.)
- Added console.log debugging to track data flow
- DRG now properly displays when AI analysis determines inpatient classification applicable

**Clear Button Enhancement:**
- Changed from simple textarea clear to full page reset
- Now clears textarea AND reloads page (window.location.href = '/')
- Removes all extraction results, AI analysis, and DRG sections
- Confirmation dialog updated: "Are you sure you want to clear everything and start fresh?"
- Provides true clean slate for new analysis

**History Feature Implementation:**

Database Changes:
- Added new `ClinicalNoteHistory` model to track all clinical note submissions
- Fields:
  - `id`: Primary key
  - `clinical_text`: Full clinical note text
  - `preview`: First 200 characters for list display
  - `created_at`: Timestamp (auto-generated)
  - `codes_count`: Number of codes extracted (updated after processing)
- Auto-creates table on first run via SQLAlchemy migrations

Backend Routes:
- `GET /history?limit=10`: Returns list of recent clinical notes
  - Ordered by created_at DESC
  - Returns: id, preview, created_at (ISO format), codes_count
  - Default limit 10 entries
- `GET /history/<int:history_id>`: Returns full clinical note text
  - Returns: id, clinical_text, created_at, codes_count
  - Used when user clicks on history item

Route Integration:
- Main route now saves to history on every POST with clinical text
- Creates preview automatically (first 200 chars)
- Updates codes_count after NLP extraction completes
- Graceful error handling (prints debug, doesn't break flow if save fails)

UI Components:
- Added blue "📜 History" button next to Clear button
- Collapsible history panel with clean list design:
  - Date/time stamp
  - Preview text (first 200 chars + "...")
  - Codes count badge
  - Hover effects for better UX
- Click history item to load text into textarea
- "Close" button to hide panel
- Max height with scroll (300px) for long history lists
- Empty state: "No history found" message
- Error state: "Failed to load history" message

JavaScript Features:
- Async/await pattern for clean API calls
- Dynamic HTML generation for history items
- Event delegation for click handlers
- Hover effects (mouseenter/mouseleave)
- Panel toggle (show/hide on History button click)
- Automatic panel close when item selected

Technical Notes:
- History saved BEFORE NLP processing (ensures capture even if extraction fails)
- Codes count updated AFTER deduplication
- Uses last entry matching clinical_text for update (prevents duplicates from race conditions)
- ISO 8601 timestamps for consistent date formatting
- SQLAlchemy session management with rollback on errors

User Workflow:
1. Enter clinical text
2. Click "Extract Codes" → Text saved to history with timestamp
3. After extraction completes → Codes count updated in history
4. Click "📜 History" → See list of past submissions
5. Click any history item → Load text into textarea
6. Process again or modify as needed

Future Enhancements:
- Add delete button for individual history items
- Add search/filter functionality
- Export history to CSV
- Add pagination for >10 entries
- Show AI analysis results in history preview
- Add tags/categories for organizing notes

Known Behaviors:
- Duplicate submissions create separate history entries (by design for auditing)
- History persists across Docker container restarts (SQLite database)
- No automatic cleanup of old history (manual database management needed)

-- End of entry --


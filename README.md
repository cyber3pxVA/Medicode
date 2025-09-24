# Medical Coding Application

## ⚠️ IMPORTANT: UMLS License Compliance

**This application requires UMLS Metathesaurus data, which is licensed content from the U.S. National Library of Medicine.**

🔒 **Access is restricted to users with valid UMLS licenses only.**

📋 **To obtain a UMLS license:** Visit https://uts.nlm.nih.gov/license.html

📖 **Read the full compliance notice:** [UMLS_LICENSE_NOTICE.md](UMLS_LICENSE_NOTICE.md)

---

## Overview
This application runs **entirely inside Docker**. All Python dependencies (NLP, ML, database), spaCy models, and supporting system libraries are baked into the image. **Install Docker & Docker Compose; do not install Python locally for this project.**

Recent update (2025-09-15): Upgraded base image to Python 3.10 and pinned heavy dependencies (`torch==2.1.2`, `faiss-cpu==1.7.4`, fixed `unqlite` version) to ensure reproducible builds.

RAG Pipeline Timeline & Attribution:
- Initial local draft of RAG components (untracked files: `rag_enhanced_lookup.py`, `rag_pipeline.py`, `test_rag.py`) created ~2025-08-14 (based on filesystem timestamps) prior to git integration.
- Added to version control and documented in commit `19b820f` (2025-09-15) alongside environment modernization.
- Concept & implementation originated within this project (no prior external git history).
- Current app defaults to base pipeline; RAG code is available for testing (`test_rag.py`) and future route integration.

## 🔐 Security & Access Control

### Authentication
- No authentication is bundled in this public repo. The app is intended for local use by individuals who already have UMLS access rights. If you deploy it publicly, add your own access controls (e.g., reverse proxy auth, SSO, or a simple login) to ensure only properly licensed users can use UMLS-backed features.

### UMLS License Compliance
- No UMLS data is stored in this repository; you must supply your own data locally.
- Do not redistribute UMLS data or derived artifacts. Keep your data outside of version control and public containers.
- If you expose the app beyond your machine, ensure only users with valid UMLS licenses can access it and keep an audit trail as required by your policies.

---

## About This Project & How It Works

**What engines/services does it use?**
- **QuickUMLS**: Fast engine for matching medical terms to UMLS concepts (CUIs)
- **spaCy & medSpaCy**: NLP libraries for processing clinical language
- **SQLite**: Lightweight database for fast code lookups (SNOMED, ICD-10)
- **UMLS Metathesaurus**: The official source of medical concepts and codes (user must provide)
- **Flask**: Web framework for the user interface and API

**Folder Structure (Key Parts):**

```
medical-coding-app/
│
├── app/                  # Main application code
│   ├── main/             # Web routes, forms, and main logic
│   ├── nlp/              # NLP pipeline (QuickUMLS, spaCy)
│   ├── models/           # Database models
│   ├── utils/            # Utilities (UMLS lookup, audit, export, semantic types)
│   ├── static/           # CSS and static files
│   └── templates/        # HTML templates
│
├── umls_data/            # UMLS data (user-provided, not included)
│   ├── META/             # Raw UMLS files (MRCONSO.RRF, etc.)
│   └── quickumls_cache/  # QuickUMLS database/cache
│
├── umls/                 # Scripts for installing/processing UMLS data
├── Dockerfile            # Docker build instructions
├── docker-compose.yml    # Docker Compose config
└── README.md             # This file
```

**How does the pipeline work? (Simple Terms)**
1. **User enters clinical text** in the web UI and clicks "Extract" (or presses Enter).
2. The app sends the text to the backend Flask server.
3. The **NLP pipeline** (in `app/nlp/pipeline.py`) uses **QuickUMLS** and **spaCy** to:
   - Split the text into sentences and words
   - Find phrases that match medical concepts in the UMLS Metathesaurus
   - Assign each match a CUI (Concept Unique Identifier), semantic type, and similarity score
4. For each CUI, the app looks up related **SNOMED CT** and **ICD-10** codes using a fast **SQLite** database built from the UMLS files (see `app/utils/umls_lookup.py`).
5. The results (CUI, term, codes, types, confidence) are shown in the web UI for review and export.

**In short:**
- The app uses NLP to find medical concepts in your text
- It matches them to UMLS CUIs using QuickUMLS
- It finds related SNOMED/ICD-10 codes for each concept
- Everything runs inside Docker for easy setup and reproducibility

---

## Quick Start (Updated 2025-09-23)

Run with a writable bind mount for UMLS data (recommended):
```
docker build -t medical-coding-app:latest ./medical-coding-app

docker run -d --name medical-coding-app \
  -p 5000:8080 \
  -e PORT=8080 \
  -e FLASK_DEBUG=1 \
  -e SKIP_UMLS_DOWNLOAD=1 \
  -e UMLS_DB_READONLY=0 \
  -e UMLS_PATH=/app/umls_data \
  -v "$(pwd)/medical-coding-app/umls_data:/app/umls_data" \
  medical-coding-app:latest
```
Then open: http://localhost:5000

Health endpoints:
- `GET /health` – basic liveness
- `GET /ready` – readiness & UMLS init state

## New Environment Toggles
| Variable | Default | Purpose |
|----------|---------|---------|
| `SKIP_UMLS_DOWNLOAD` | 0 | When `1`, bypasses background remote UMLS init script if local data already present. |
| `UMLS_DB_READONLY` | 0 | When `1`, opens `umls_lookup.db` in SQLite read-only URI mode (fails if DB missing). |
| `UMLS_PATH` | `umls_data` | Base directory containing `META/` and lookup DB. |
| `INPATIENT_DRG_DEFAULT` | `0` | When `1`, UI inpatient checkbox starts checked (DRG enrichment active if mapping present). |

If you mount `umls_data` read-only you must pre-populate `umls_lookup.db` and QuickUMLS cache; otherwise use a writable mount.

## UMLS Data Safety (Reinforced)
The `.gitignore` now blocks:
- Raw Metathesaurus files (MRCONSO, MRREL, etc.)
- Lookup DB (`umls_lookup.db`), QuickUMLS caches, UnQLite artifacts
Ensure you do NOT `git add` any derived or raw UMLS content.

## Optional: DRG (MS-DRG) Enrichment

You can enrich ICD-10 codes with heuristic MS-DRG labels using a derived mapping CSV. This project deliberately does *not* ship CMS raw GROUPER logic or official proprietary distribution files.

### Steps
1. Read `medical-coding-app/DRG_SOURCE_NOTICE.md` for compliance & structure.
2. Download CMS MS-DRG Definitions/Data Files ZIP for the fiscal year (e.g., FY2025) manually from the CMS site.
3. Place the raw ZIP (and any extracted CSV like `MS-DRG Long Titles.csv`) under:
  ```
  medical-coding-app/drg_source/FY2025/
  ```
4. Create (or curate) an `icd_roots_to_drg.csv` mapping (columns: `ICD10,DRG`). This is heuristic—not official grouping output.
5. Run inside the container to build the simplified mapping consumed by the app:
  ```bash
  docker compose exec web python scripts/build_drg_mapping.py \
     --drg-titles drg_source/FY2025/MS-DRG_Long_Titles.csv \
     --icd-map drg_source/FY2025/icd_roots_to_drg.csv \
     --out drg_mapping_improved.csv
  ```
6. Set (or confirm) environment variable (in `.env` or docker compose) so the app loads it:
  ```
  DRG_MAPPING_PATH=/app/drg_mapping_improved.csv
  ```
7. Refresh the UI – DRG column appears for matched ICD roots.

If you only have the definitions manual text bundle (folder with many `.txt` files), extract long titles first:
```bash
docker compose exec web python scripts/extract_drg_long_titles_from_manual.py \
  --input-dir drg_source/FY2026/msdrgv43.icd10_ro_definitionsmanual_text \
  --out drg_source/FY2026/drg_long_titles_v43.csv
```
Then pass that CSV as `--drg-titles`.

### Caveats & Disclaimer
- This is **not** a substitute for running the official CMS GROUPER (which requires full claim context, diagnoses, procedures, sex, discharge status, etc.).
- The mapping here is a *many-to-many heuristic* for exploratory enrichment only.
- Do not commit raw CMS ZIPs or extracted proprietary tables—`.gitignore` already blocks `drg_source/` and `*.zip`.

Detailed rationale and format expectations: `medical-coding-app/DRG_SOURCE_NOTICE.md`.

## Troubleshooting Snapshot
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `sqlite3.OperationalError: unable to open database file` | Read-only mount, DB not prebuilt | Mount writable or prebuild DB, set `UMLS_DB_READONLY=1` only after DB exists |
| QuickUMLS IO error | Cache needs write access | Use writable volume for `quickumls_cache` |
| Slow first run | Building lookup DB & cache | Re-runs will skip with `SKIP_UMLS_DOWNLOAD=1` |

<!-- ...existing content below retained ... -->

---

## Prerequisites
* **Docker** (Desktop on Win/Mac or Engine on Linux)
* **Docker Compose** (v2+ bundled with recent Docker installs)
* **UMLS Data** placed under `medical-coding-app/umls_data/META` (not distributed)

---

docker compose up --build
## Run (Docker Only)
From repository root:
```sh
docker compose up --build
```
What happens on first run:
1. Python 3.10 image builds with all NLP dependencies & models.
2. Database tables auto-created (SQLite at `site.db`).
3. QuickUMLS cache reused or built if absent.
4. App serves at http://127.0.0.1:5000 (mapped from container port 5000).

---

## Environment Variables and Secrets
- Use a `.env` file in the `medical-coding-app` directory to store secrets for Docker use.
- **Never commit your `.env` file to git.** It is already listed in `.gitignore`.
- Docker and the app will read environment variables from this file inside the container.

Example `.env` file:
```
UMLS_API_KEY=your_real_key_here
```

---

## Stopping the App
To stop the app, press `Ctrl+C` in the terminal or run:
```sh
docker compose down
```

---

## Troubleshooting

### QuickUMLS Database Issues
If you encounter QuickUMLS database errors, the application will automatically rebuild the database on startup. This process may take a few minutes the first time.

### NLTK Data Conflicts
The Docker image includes pre-downloaded NLTK data to prevent conflicts between multiple containers.

---

## What is a CUI?

CUI = Concept Unique Identifier.

- Issued by the UMLS Metathesaurus (Unified Medical Language System).
- Each CUI represents one biomedical concept, no matter how many synonyms or source vocabularies refer to it.
- Example: the concept “Hypertension” has CUI C0020538; whether it’s called “high blood pressure,” “HTN,” or an ICD-10 code, they all map to that same CUI.
- Using CUIs lets you link, deduplicate, or compare terms across different coding systems (ICD-10, SNOMED CT, RxNorm, etc.) because they all converge on the same unique identifier in UMLS.
- So in your app the CUI column shows the standardized UMLS concept each extracted term maps to.

---

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Features
- Clinical text input interface
- Real-time code extraction
- Confidence scoring for mappings
- Manual validation workflow
- Export functionality (CSV, JSON)
- Audit trail logging

## Technology Stack
| Layer | Components |
|-------|------------|
| Runtime | Python 3.10 (Docker slim base) |
| Web/API | Flask, Flask-WTF, SQLAlchemy |
| NLP Core | spaCy 3.4.4, en_core_web_sm, en_core_sci_sm, NLTK |
| Concept Mapping | QuickUMLS 1.4.x |
| RAG / Semantic | sentence-transformers, transformers, torch 2.1.2, faiss-cpu 1.7.4 |
| Storage | SQLite (primary), UnQLite (fast CUI/code cache) |
| Data Source | UMLS Metathesaurus (user supplied) |

Pinned heavy binaries: `torch==2.1.2`, `faiss-cpu==1.7.4`, `unqlite==0.9.9` for reproducibility.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

---

## Developer Shortcuts

You can manage the application entirely from your IDE terminal. Use the following Docker Compose commands:

- **Start the application:**
  ```sh
  docker compose up --build
  ```
- **Stop the application:**
  ```sh
  docker compose down
  ```
- **Access a shell inside the running container (for debugging or management):**
  ```sh
  docker compose exec web bash
  ```

All development, testing, and management should be done inside Docker. Local (non-Docker) execution is not supported or recommended.

---

## UMLS Data Requirement

Due to licensing restrictions, this project does **NOT** include UMLS Metathesaurus data or any derived files (QuickUMLS cache, lookup DB, etc).

**To use this app:**
1. Register for a free UMLS license: https://uts.nlm.nih.gov/
2. Download the UMLS Metathesaurus release (e.g., 2024AA).
3. Extract the `META` folder into `medical-coding-app/umls_data/META/`.
4. Run the app with Docker as usual. The required lookup tables and caches will be built automatically on first run.

**Note:** The initial build may take several minutes as the app processes the UMLS data.

If you are sharing this project, do **not** upload UMLS data or any derived files to public repositories or images.

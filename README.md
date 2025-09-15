# Medical Coding Application

## Overview
This application runs **entirely inside Docker**. All Python dependencies (NLP, ML, database), spaCy models, and supporting system libraries are baked into the image. **Install Docker & Docker Compose; do not install Python locally for this project.**

Recent update (2025-09-15): Upgraded base image to Python 3.10 and pinned heavy dependencies (`torch==2.1.2`, `faiss-cpu==1.7.4`, fixed `unqlite` version) to ensure reproducible builds.

RAG Pipeline Timeline & Attribution:
- Initial local draft of RAG components (untracked files: `rag_enhanced_lookup.py`, `rag_pipeline.py`, `test_rag.py`) created ~2025-08-14 (based on filesystem timestamps) prior to git integration.
- Added to version control and documented in commit `19b820f` (2025-09-15) alongside environment modernization.
- Concept & implementation originated within this project (no prior external git history).
- Current app defaults to base pipeline; RAG code is available for testing (`test_rag.py`) and future route integration.

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

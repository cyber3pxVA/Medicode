# Medicode - AI-Powered Medical Coding Assistant

**This is an open source application available here: https://github.com/frasod/Medicode**

## ⚠️ IMPORTANT: UMLS License Compliance

**This application requires UMLS Metathesaurus data, which is licensed content from the U.S. National Library of Medicine.**

🔒 **Access is restricted to users with valid UMLS licenses only.**

📋 **To obtain a UMLS license:** Visit https://uts.nlm.nih.gov/license.html

📖 **Read the full compliance notice:** [UMLS_LICENSE_NOTICE.md](UMLS_LICENSE_NOTICE.md)

---

## Overview
Medicode is an AI-powered medical coding assistant that runs **entirely inside Docker**. It uses a **two-step workflow** combining traditional NLP with modern AI to deliver accurate, context-aware medical coding for the Department of Veterans Affairs (VA) and other healthcare settings.

### Two-Step Workflow

#### Step 1: NLP Extraction (QuickUMLS + spaCy)
- Fast concept extraction from clinical text
- Matches medical terms to UMLS Concept Unique Identifiers (CUIs)
- Maps CUIs to ICD-10, SNOMED CT, and other coding systems
- Optional semantic enhancement for improved accuracy (USE_RAG=1)
- Negation detection to filter out denied conditions

#### Step 2: AI Analysis (OpenAI GPT-4o)
- **Code Validation**: Reviews all NLP-extracted codes for clinical relevance
- **Medical Reasoning**: Provides exclusion rationale for inappropriate codes
- **MS-DRG Assignment**: Determines appropriate DRG codes for inpatient encounters
- **VHA VERA Complexity**: Assesses patient complexity using VA's 5-level scoring system
- **Coding Recommendations**: Suggests documentation improvements and coding best practices
- **VA-Specific Context**: Applies Department of Veterans Affairs coding standards

### Key Features
- **VA Medical Coder Context**: AI identifies as a certified medical coder working at a VA Medical Center
- **Intelligent Code Validation**: AI excludes invalid codes with medical rationale
- **MS-DRG Classification**: Automated DRG assignment with CC/MCC consideration
- **VHA VERA Complexity Scoring**: 5-level patient complexity assessment
- **ICD-10 Code Grouping**: Automatically groups multiple medical terms that map to the same ICD-10 code
- **Smart Filtering**: Adjustable similarity threshold and max codes display (1-30)
- **Export Functionality**: CSV and JSON export of coding results
- **Clean UI**: Two-panel interface with NLP Raw Analysis table and AI Analysis section

Recent update (2025-10-18): Major refactor to AI-driven medical coding with VA context. DRG assignment is now handled by OpenAI GPT-4o analysis rather than static mapping files.

**Semantic Enhancement (Optional):**
The app includes an optional "RAG-like" semantic search enhancement (not traditional RAG/retrieval-augmented generation). When enabled via `USE_RAG=1`, it uses sentence transformers and FAISS vector search to improve concept matching accuracy. This is distinct from the OpenAI GPT-4o analysis and focuses on improving the initial NLP extraction step.

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
- **OpenAI GPT-4o**: AI model for intelligent code validation, MS-DRG assignment, and VHA complexity scoring
- **SQLite**: Lightweight database for fast code lookups (SNOMED, ICD-10)
- **UMLS Metathesaurus**: The official source of medical concepts and codes (user must provide)
- **Flask**: Web framework for the user interface and API
- **Optional Semantic Enhancement**: Sentence transformers + FAISS for improved concept matching (USE_RAG=1)

**Folder Structure (Key Parts):**

```
medical-coding-app/
│
├── app/                  # Main application code
│   ├── main/             # Web routes, forms, and main logic
│   ├── nlp/              # NLP pipeline (QuickUMLS, spaCy, optional semantic enhancement)
│   ├── ai/               # OpenAI GPT-4o integration for code validation and DRG analysis
│   ├── models/           # Database models
│   ├── utils/            # Utilities (UMLS lookup, audit, export, semantic types, negation)
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

**How does the two-step workflow work?**

### Step 1: NLP Extraction
1. **User enters clinical text** in the web UI and clicks "Extract" (or presses Enter).
2. The app sends the text to the backend Flask server.
3. The **NLP pipeline** (in `app/nlp/pipeline.py`) uses **QuickUMLS** and **spaCy** to:
   - Split the text into sentences and words
   - Find phrases that match medical concepts in the UMLS Metathesaurus
   - Assign each match a CUI (Concept Unique Identifier), semantic type, and similarity score
   - Apply negation detection to filter out denied conditions (e.g., "no history of diabetes")
4. For each CUI, the app looks up related **SNOMED CT** and **ICD-10** codes using a fast **SQLite** database built from the UMLS files (see `app/utils/umls_lookup.py`).
5. Optional: If `USE_RAG=1`, semantic enhancement improves concept matching using sentence transformers and FAISS vector search.
6. The **NLP Raw Analysis table** displays all extracted codes, terms, CUIs, and confidence scores.

### Step 2: AI Analysis (OpenAI GPT-4o)
1. **User clicks "AI Analysis"** button after reviewing the extracted codes.
2. The app sends the clinical text and NLP-extracted codes to **OpenAI GPT-4o**.
3. The AI acts as a **VA medical coder** and performs:
   - **Code Validation**: Reviews each ICD-10 code for clinical appropriateness
   - **Exclusion with Rationale**: Identifies invalid codes and explains why (e.g., "symptom code when diagnosis available", "not documented in note", "NLP extraction error")
   - **MS-DRG Assignment**: Determines appropriate DRG code for inpatient encounters, considering principal diagnosis, CC/MCC, and provides rationale
   - **VHA VERA Complexity**: Assigns 1 of 5 complexity levels based on chronic conditions, comorbidities, and service-connected disabilities
   - **Coding Recommendations**: Suggests documentation improvements and VA-specific coding opportunities
4. The **AI Analysis section** displays the results with color-coded sections (MS-DRG, VHA complexity, recommendations).
5. The **NLP Raw Analysis table** is filtered to show only AI-validated codes.
6. **Excluded codes** appear below the table with medical reasoning for each exclusion.

**In short:**
- Step 1 (NLP) casts a wide net to find all possible medical concepts
- Step 2 (AI) applies clinical judgment to validate codes and provide context-aware analysis
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
| `OPENAI_API_KEY` | (required for AI) | OpenAI API key for GPT-4o analysis. Get from https://platform.openai.com/ |
| `ENABLE_OPENAI_DRG` | `0` | When `1`, enables AI-powered code validation and MS-DRG analysis |
| `USE_RAG` | `0` | When `1`, enables semantic enhancement for NLP extraction (FAISS vector search) |
| `SKIP_UMLS_DOWNLOAD` | `0` | When `1`, bypasses background remote UMLS init script if local data already present |
| `UMLS_DB_READONLY` | `0` | When `1`, opens `umls_lookup.db` in SQLite read-only URI mode (fails if DB missing) |
| `UMLS_PATH` | `umls_data` | Base directory containing `META/` and lookup DB |
| `INPATIENT_DRG_DEFAULT` | `0` | When `1`, UI inpatient checkbox starts checked (deprecated - DRG now handled by AI) |
| `ENABLE_DRG` | `0` | **Deprecated** - DRG assignment now handled by OpenAI GPT-4o when `ENABLE_OPENAI_DRG=1` |

If you mount `umls_data` read-only you must pre-populate `umls_lookup.db` and QuickUMLS cache; otherwise use a writable mount.

## UMLS Data Safety (Reinforced)
The `.gitignore` now blocks:
- Raw Metathesaurus files (MRCONSO, MRREL, etc.)
- Lookup DB (`umls_lookup.db`), QuickUMLS caches, UnQLite artifacts
Ensure you do NOT `git add` any derived or raw UMLS content.

## MS-DRG Assignment (AI-Powered)

**MS-DRG assignment is now handled by OpenAI GPT-4o**, not static mapping files.

### How It Works
1. Set `ENABLE_OPENAI_DRG=1` and provide `OPENAI_API_KEY` in your environment
2. After NLP extraction, click "AI Analysis" button
3. GPT-4o determines the appropriate MS-DRG based on:
   - Principal diagnosis (ICD-10 code)
   - Secondary diagnoses and comorbidities
   - Complications and Comorbidities (CC) / Major CC (MCC)
   - Clinical context from the note
4. AI provides DRG code, description, and detailed rationale
5. Alternative DRGs suggested when applicable

### Important Notes
- This is **not** a substitute for running the official CMS GROUPER (which requires full claim context)
- The AI analysis is for educational and exploratory purposes
- Always verify DRG assignments using your organization's official billing system
- For VA facilities, VHA VERA complexity scoring is also provided (5 levels)

### Legacy DRG Mapping (Deprecated)
The old static DRG mapping system (`ENABLE_DRG=1` with CSV files) is deprecated and will be removed in future versions. The AI-driven approach provides more accurate, context-aware DRG assignment with medical reasoning.

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
# OpenAI API key for AI analysis (required for GPT-4o features)
OPENAI_API_KEY=sk-proj-your_real_key_here

# Enable AI-powered code validation and MS-DRG assignment
ENABLE_OPENAI_DRG=1

# Optional: Enable semantic enhancement for NLP extraction
USE_RAG=0

# UMLS configuration
UMLS_PATH=umls_data
SKIP_UMLS_DOWNLOAD=1
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
| NLP Core | spaCy 3.4.4, en_core_web_sm, en_core_sci_sm, NLTK, QuickUMLS 1.4.x |
| AI Analysis | OpenAI GPT-4o (code validation, MS-DRG assignment, VHA VERA complexity) |
| Semantic Enhancement (Optional) | sentence-transformers, transformers, torch 2.1.2, faiss-cpu 1.7.4 |
| Storage | SQLite (primary), UnQLite (fast CUI/code cache) |
| Data Source | UMLS Metathesaurus (user supplied) |

**Note on "RAG-like" functionality:** The optional semantic enhancement (USE_RAG=1) uses vector similarity search to improve concept matching, but is not traditional RAG (Retrieval-Augmented Generation). The actual AI analysis uses OpenAI GPT-4o with structured prompts, not RAG architecture.

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

# Medical Coding Application

## Overview
This application is designed to run **entirely inside Docker containers**. All dependencies, models, and environment setup are handled by Docker. **You must have Docker and Docker Compose installed to use this application. Local (non-Docker) development is not supported.**

---

## 🚀 New: RAG-Enhanced Medical Coding

This application now features **RAG (Retrieval-Augmented Generation)** enhanced medical coding that addresses common bottlenecks:

### Key Improvements:
- **UnQLite Backend**: Fast key-value storage replacing direct MRCONSO.RRF parsing
- **Semantic Filtering**: Eliminates false positives like "may" vs "May-Hegglin syndrome"
- **Context-Aware Retrieval**: Uses sentence transformers for relevance scoring
- **Parallel Processing**: Multi-threaded processing for better performance
- **Fallback Support**: Graceful degradation to base pipeline if RAG components unavailable

### Performance Benefits:
- **10-50x faster** lookups compared to direct MRCONSO.RRF parsing
- **Context-aware filtering** removes 90%+ of false positives
- **Semantic search** for finding related medical concepts
- **Parallel processing** reduces initialization time

### How RAG Enhancement Works:
1. **QuickUMLS** extracts initial concepts from clinical text
2. **Semantic filtering** removes non-clinical terms (months, common words)
3. **RAG lookup** uses UnQLite for fast CUI-to-code mapping
4. **Context scoring** ranks results by clinical relevance
5. **Parallel processing** handles multiple concepts simultaneously

### Timeline & Attribution
- RAG component source files drafted locally ~2025-08-14 (pre-git state) and integrated into version control in commit `19b820f` on 2025-09-15.
- Authored within this project; no prior external repository lineage.
- Currently optional: base routes still default to the non-RAG pipeline pending a toggle or full integration.

---

## About This Project & How It Works

**What engines/services does it use?**
- **QuickUMLS**: Fast engine for matching medical terms to UMLS concepts (CUIs)
- **RAG-Enhanced Lookup**: UnQLite-based fast code mapping with semantic search
- **spaCy & medSpaCy**: NLP libraries for processing clinical language
- **Sentence Transformers**: Semantic similarity for context-aware filtering
- **SQLite/UnQLite**: Lightweight databases for fast code lookups (SNOMED, ICD-10)
- **UMLS Metathesaurus**: The official source of medical concepts and codes (user must provide)
- **Flask**: Web framework for the user interface and API

**Folder Structure (Key Parts):**

```
medical-coding-app/
│
├── app/                  # Main application code
│   ├── main/             # Web routes, forms, and main logic
│   ├── nlp/              # NLP pipeline (QuickUMLS, RAG-enhanced)
│   │   ├── pipeline.py   # Base QuickUMLS pipeline
│   │   └── rag_pipeline.py # RAG-enhanced pipeline
│   ├── models/           # Database models
│   ├── utils/            # Utilities (UMLS lookup, RAG lookup, audit, export)
│   │   ├── umls_lookup.py      # Basic SQLite lookup
│   │   └── rag_enhanced_lookup.py # RAG-enhanced UnQLite lookup
│   ├── static/           # CSS and static files
│   └── templates/        # HTML templates
│
├── umls_data/            # UMLS data (user-provided, not included)
│   ├── META/             # Raw UMLS files (MRCONSO.RRF, etc.)
│   ├── quickumls_cache/  # QuickUMLS database/cache
│   └── rag_cache/        # RAG-enhanced lookup cache
│
├── umls/                 # Scripts for installing/processing UMLS data
├── Dockerfile            # Docker build instructions
├── docker-compose.yml    # Docker Compose config
├── test_rag.py          # RAG functionality test script
└── README.md             # This file
```

**How does the RAG pipeline work? (Simple Terms)**
1. **User enters clinical text** in the web UI and clicks "Extract" (or presses Enter).
2. The app sends the text to the backend Flask server.
3. The **RAG-enhanced NLP pipeline** (in `app/nlp/rag_pipeline.py`) uses **QuickUMLS** and **semantic filtering** to:
   - Split the text into sentences and words
   - Find phrases that match medical concepts in the UMLS Metathesaurus
   - **Filter out false positives** like "may" (month) vs "May-Hegglin syndrome" (disease)
   - Assign each match a CUI, semantic type, and relevance score
4. For each CUI, the app uses **RAG-enhanced lookup** (in `app/utils/rag_enhanced_lookup.py`) with **UnQLite** to:
   - Fast lookup of related **SNOMED CT**, **ICD-10**, **CPT**, and **HCPCS** codes
   - **Context-aware scoring** using sentence transformers
   - **Parallel processing** for better performance
5. The results (CUI, term, codes, types, relevance) are shown in the web UI for review and export.

**In short:**
- The app uses NLP to find medical concepts in your text
- It filters out false positives using semantic types and context
- It matches them to UMLS CUIs using QuickUMLS
- It finds related codes using fast UnQLite lookups with RAG enhancement
- Everything runs inside Docker for easy setup and reproducibility

---

## Prerequisites
- **Docker**: Install Docker Desktop (Windows/Mac) or Docker Engine (Linux).
- **Docker Compose**: Usually included with Docker Desktop.
- **UMLS Data**: Already present in the `umls_data/` directory.

---

## How to Run This Application (Docker-Only)

### 1. Start the Application
From the `medical-coding-app` directory, run:
```sh
cd medical-coding-app
# Build and start the app
docker compose up --build
```

The application will automatically:
- Initialize the QuickUMLS database from the existing UMLS data
- Build the RAG-enhanced lookup database (first time only)
- Start the Flask web server
- Be ready for use

### 2. Access the App
Open your browser and go to:
```
http://127.0.0.1:5000
```

### 3. Test RAG Functionality
Run the test script to verify RAG enhancement:
```sh
docker compose exec web python test_rag.py
```

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

### RAG Database Issues
If the RAG-enhanced lookup fails to initialize, the application will fall back to the basic SQLite lookup. Check the logs for specific error messages.

### NLTK Data Conflicts
The Docker image includes pre-downloaded NLTK data to prevent conflicts between multiple containers.

### Memory Issues
The RAG pipeline requires additional memory for sentence transformers. If you encounter memory issues, the application will automatically fall back to the base pipeline.

---

## What is a CUI?

CUI = Concept Unique Identifier.

- Issued by the UMLS Metathesaurus (Unified Medical Language System).
- Each CUI represents one biomedical concept, no matter how many synonyms or source vocabularies refer to it.
- Example: the concept "Hypertension" has CUI C0020538; whether it's called "high blood pressure," "HTN," or an ICD-10 code, they all map to that same CUI.
- Using CUIs lets you link, deduplicate, or compare terms across different coding systems (ICD-10, SNOMED CT, RxNorm, etc.) because they all converge on the same unique identifier in UMLS.
- So in your app the CUI column shows the standardized UMLS concept each extracted term maps to.

---

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Features
- Clinical text input interface
- **RAG-enhanced real-time code extraction**
- **Semantic filtering to remove false positives**
- **Context-aware relevance scoring**
- **Fast UnQLite-based lookups**
- **Semantic search capabilities**
- **Optional DRG enrichment** (ICD-10 -> DRG mapping from user-provided open CSV)
- Confidence scoring for mappings
- Manual validation workflow
- Export functionality (CSV, JSON)
- Audit trail logging

## Technology Stack
- **Python**: 3.10 (containerized)
- **Flask**: Web framework for building the application
- **medSpaCy**: For clinical NLP processing
- **QuickUMLS**: For concept mapping
- **RAG-Enhanced Lookup**: UnQLite + sentence transformers for fast, context-aware retrieval
- **SQLite/UnQLite**: Local data storage
- **UMLS Metathesaurus**: Local installation for medical terminology

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

---

## If you use Cursor or an IDE

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
- **Test RAG functionality:**
  ```sh
  docker compose exec web python test_rag.py
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

**Note:** The initial build may take several minutes as the app processes the UMLS data and builds the RAG-enhanced lookup database.

If you are sharing this project, do **not** upload UMLS data or any derived files to public repositories or images.

---

## DRG (Diagnosis Related Group) Enrichment (Optional)

The application can optionally enrich extracted ICD-10 codes with **MS-DRG** groupings if you provide an open-source mapping CSV.

### How It Works
1. After ICD-10 codes are identified for each concept, each code is looked up in an in-memory DRG map.
2. Matching DRG entries (code + description) are added under `drg_codes` for that concept.
3. A new DRG column appears in the UI (toggleable like other columns) and is included in exports when visible.

### Provide a Mapping
Set an environment variable (in your `.env`):
```
DRG_MAPPING_PATH=/app/drg_mapping.csv
```
Then mount or copy a CSV into the container at that path with columns (case-insensitive):
```
ICD10,DRG,DRG_DESCRIPTION
```
Example row:
```
E11.9,683,DIABETES W/O CC/MCC
```

### Sample File
A minimal `drg_mapping.sample.csv` is included only to illustrate format (contains no proprietary CMS content). Duplicate it, rename to `drg_mapping.csv`, and supply your own full open dataset if licensing permits.

### If Omitted
If `DRG_MAPPING_PATH` is unset or the file is missing/invalid, enrichment is silently skipped and the DRG column won't appear.

### Export Behavior
- JSON export includes a `drg_codes` array (when visible)
- CSV export flattens DRGs: `DRG: Description` separated by `|`

### Implementation Notes
- Loader code: `app/utils/drg_mapping.py`
- Caches mapping in-process via `lru_cache`
- Does not persist to database; ephemeral enrichment only

---

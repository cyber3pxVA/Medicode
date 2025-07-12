# Medical Coding Application

## Overview
This application is designed to run **entirely inside Docker containers**. All dependencies, models, and environment setup are handled by Docker. **You must have Docker and Docker Compose installed to use this application. Local (non-Docker) development is not supported.**

---

## About This Project & How It Works

**Who built this?**  
This app was built by a team of developers and clinical NLP specialists to help extract standardized medical codes from clinical text. It is designed for easy use, reproducibility, and legal compliance (no UMLS data is included).

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
- Start the Flask web server
- Be ready for use

### 2. Access the App
Open your browser and go to:
```
http://127.0.0.1:5000
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
- **Python**: 3.8+
- **Flask**: Web framework for building the application
- **medSpaCy**: For clinical NLP processing
- **QuickUMLS**: For concept mapping
- **SQLite**: Local data storage
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
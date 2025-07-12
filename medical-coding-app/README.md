# Medical Coding Application

## Overview
This application is designed to run **entirely inside Docker containers**. All dependencies, models, and environment setup are handled by Docker. **You must have Docker and Docker Compose installed to use this application. Local (non-Docker) development is not supported.**

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
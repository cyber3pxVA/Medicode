# UMLS Metathesaurus Documentation

## Overview
The UMLS (Unified Medical Language System) Metathesaurus is a comprehensive resource that provides a large set of biomedical concepts and their relationships. It is essential for the medical coding application to accurately extract and map clinical codes from text.

## Installation (Docker-Only)
To use the UMLS Metathesaurus in this project, follow these steps **inside the Docker container**:

1. **Obtain UMLS License**: Register at the UMLS website to obtain a license.
2. **Download UMLS Files**: After obtaining the license, download the UMLS Metathesaurus files from the UMLS website and place them in the `temp_download` directory.
3. **Install UMLS Locally in Docker**: Start the Docker container and run the install script:
   ```sh
   docker compose exec web bash
   python umls/install_umls.py --api_key YOUR_UMLS_API_KEY
   ```
   This will process the UMLS data and build the QuickUMLS database inside the container.

## Usage
Once the UMLS Metathesaurus is installed, the application will automatically access the necessary files from the correct directory inside Docker. No local (host) installation is required or supported.

## Configuration
Make sure to configure the application settings in `config.py` or via environment variables (e.g., in your `.env` file) to point to the UMLS installation directory. This will allow the application to correctly interface with the Metathesaurus.

## Support
For any issues related to UMLS installation or usage, refer to the official UMLS documentation or seek support from the UMLS user community.
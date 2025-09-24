#!/bin/bash
cd /media/frasod/4T/Code_Projects/Medicode/medical-coding-app
export SKIP_UMLS_DOWNLOAD=1
export UMLS_DB_READONLY=1
export UMLS_PATH=umls_data
export DRG_MAPPING_PATH=drg_mapping_improved.csv
export PORT=8081
python3 run.py
#!/usr/bin/env python3
"""
Initialize UMLS data from Google Cloud Storage for Cloud Run deployment.
This script downloads UMLS data if not present locally.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_from_gcs():
    """Download UMLS data from Google Cloud Storage if not present."""
    
    umls_path = Path("/app/umls_data")
    bucket_name = os.environ.get("UMLS_GCS_BUCKET")
    
    if not bucket_name:
        logger.error("UMLS_GCS_BUCKET environment variable not set!")
        return False
    
    # Check if UMLS data already exists
    if (umls_path / "META").exists() and (umls_path / "umls_lookup.db").exists():
        logger.info("UMLS data already exists, skipping download")
        return True
    
    logger.info(f"Downloading UMLS data from gs://{bucket_name}/umls_data/")
    
    try:
        # Create umls_data directory
        umls_path.mkdir(exist_ok=True)
        
        # Download UMLS data from Cloud Storage
        cmd = [
            "gsutil", "-m", "cp", "-r", 
            f"gs://{bucket_name}/umls_data/*", 
            str(umls_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to download UMLS data: {result.stderr}")
            return False
            
        logger.info("UMLS data downloaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error downloading UMLS data: {e}")
        return False

def setup_quickumls_cache():
    """Initialize QuickUMLS cache if needed."""
    cache_path = Path("/app/umls_data/quickumls_cache")
    
    if cache_path.exists() and any(cache_path.iterdir()):
        logger.info("QuickUMLS cache already exists")
        return True
    
    logger.info("QuickUMLS cache will be built on first request")
    return True

if __name__ == "__main__":
    logger.info("Initializing UMLS data for Cloud Run...")
    
    # Check if we're in Cloud Run (has specific env vars)
    if os.environ.get("K_SERVICE"):
        logger.info("Running in Cloud Run environment")
        
        if not download_from_gcs():
            logger.error("Failed to initialize UMLS data")
            sys.exit(1)
            
        if not setup_quickumls_cache():
            logger.error("Failed to setup QuickUMLS cache")
            sys.exit(1)
            
        logger.info("UMLS initialization complete")
    else:
        logger.info("Not in Cloud Run, skipping GCS download")
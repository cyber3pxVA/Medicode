import argparse
import requests
import zipfile
import os
import shutil

def download_file(url, api_key, target_dir):
    """
    Downloads a file from a URL requiring API key authentication.
    """
    headers = {'Authorization': f'Bearer {api_key}'}
    local_filename = os.path.join(target_dir, url.split('/')[-1])
    
    print(f"Downloading from {url}...")
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"Downloaded to {local_filename}")
    return local_filename

def unzip_file(zip_path, extract_to):
    """
    Unzips a file to a specified directory.
    """
    print(f"Unzipping {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"Unzipped to {extract_to}")

def main():
    parser = argparse.ArgumentParser(description="Download and install UMLS data for QuickUMLS.")
    parser.add_argument("--api_key", required=True, help="Your UMLS API key.")
    parser.add_argument("--output_path", default="../umls_data", help="The path to install the QuickUMLS data to.")
    parser.add_argument("--umls_version", default="2023AA", help="The UMLS version to download.")
    args = parser.parse_args()

    download_dir = "temp_download"
    unzip_dir = os.path.join(download_dir, args.umls_version)
    os.makedirs(args.output_path, exist_ok=True)
    os.makedirs(unzip_dir, exist_ok=True)

    print("="*80)
    print("IMPORTANT: UMLS Download")
    print("="*80)
    print("This script cannot automatically download the UMLS zip file.")
    print("You must manually download the UMLS Metathesaurus zip file for your chosen version.")
    print(f"1. Go to: https://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html")
    print(f"2. Log in and download the '{args.umls_version}-1-meta.nlm' zip file.")
    print(f"3. Place the downloaded zip file into the '{download_dir}' directory.")
    input("Press Enter to continue after you have placed the zip file...")

    zip_files = [f for f in os.listdir(download_dir) if f.endswith('.zip')]
    if not zip_files:
        print("No zip file found in the 'temp_download' directory. Exiting.")
        return
    zip_path = os.path.join(download_dir, zip_files[0])

    unzip_file(zip_path, unzip_dir)

    # Find the directory that contains the RRF files
    meta_dir_parent = os.path.join(unzip_dir, os.listdir(unzip_dir)[0])
    meta_dir = os.path.join(meta_dir_parent, "META")

    print(f"Copying META directory from {meta_dir} to {args.output_path}...")
    dest_meta_dir = os.path.join(args.output_path, "META")
    if os.path.exists(dest_meta_dir):
        shutil.rmtree(dest_meta_dir)
    shutil.copytree(meta_dir, dest_meta_dir)

    print("\n" + "="*80)
    print("UMLS Installation Complete!")
    print(f"The QuickUMLS data has been installed in: {os.path.abspath(args.output_path)}")
    print("You can now start the application with 'docker compose up'")
    print("="*80)

if __name__ == "__main__":
    main() 
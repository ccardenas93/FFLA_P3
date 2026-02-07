import os
import requests
import sys

# Base URL for raw content (handles LFS redirection usually)
BASE_URL = "https://github.com/ccardenas93/FFLA/raw/main"

# Structure to download
# We focus on FMPLPT as it contains the national headers (based on previous inspection P_historical_ecuador.nc)
# derived from the user's listing.
# Renaming for clarity and ensuring we download everything
FILES_FMPLPT = {
    "FMPLPT/historical_ecuador": [
        "pr_historical_ecuador.nc", "tas_historical_ecuador.nc", 
        "tasmin_historical_ecuador.nc", "tasmax_historical_ecuador.nc"
    ],
    "FMPLPT/ssp126_ecuador": [
        "pr_ssp126_ecuador.nc", "tas_ssp126_ecuador.nc", 
        "tasmin_ssp126_ecuador.nc", "tasmax_ssp126_ecuador.nc"
    ],
    "FMPLPT/ssp370_ecuador": [
        "pr_ssp370_ecuador.nc", "tas_ssp370_ecuador.nc", 
        "tasmin_ssp370_ecuador.nc", "tasmax_ssp370_ecuador.nc"
    ],
    "FMPLPT/ssp585_ecuador": [
        "pr_ssp585_ecuador.nc", "tas_ssp585_ecuador.nc", 
        "tasmin_ssp585_ecuador.nc", "tasmax_ssp585_ecuador.nc"
    ],
}
# Note: FMPLPT usually has P_ and T_ prefixes, differing from FODESNA's pr_ / tas_. 
# If the repo actually has standard names for FMPLPT, we should use those.
# But assuming the dictionary above was there for a reason, we keep it. 
# UPDATE: User asked for FMPLPT specifically.

FILES_FODESNA = {
    "FODESNA/historical_ecuador": [
        "pr_historical_ecuador.nc", "tas_historical_ecuador.nc", 
        "tasmin_historical_ecuador.nc", "tasmax_historical_ecuador.nc"
    ],
    "FODESNA/ssp126_ecuador": [
        "pr_ssp126_ecuador.nc", "tas_ssp126_ecuador.nc", 
        "tasmin_ssp126_ecuador.nc", "tasmax_ssp126_ecuador.nc"
    ],
    "FODESNA/ssp370_ecuador": [
        "pr_ssp370_ecuador.nc", "tas_ssp370_ecuador.nc", 
        "tasmin_ssp370_ecuador.nc", "tasmax_ssp370_ecuador.nc"
    ],
    "FODESNA/ssp585_ecuador": [
        "pr_ssp585_ecuador.nc", "tas_ssp585_ecuador.nc", 
        "tasmin_ssp585_ecuador.nc", "tasmax_ssp585_ecuador.nc"
    ]
}

def download_file(url, dest_path):
    print(f"Downloading {url}...")
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"✅ Saved to {dest_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to download {url}: {e}")
        return False

def run(base_dir=None):
    if base_dir is None:
        # Default to 'organized' root
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Target directory is ALWAYS inputs/ inside base_dir
    target_base = os.path.join(base_dir, "inputs")
    
    print(f"🚀 Starting Data Download to {target_base}...")
    
    # Check both sources
    ALL_FILES = {**FILES_FODESNA, **FILES_FMPLPT}

    for folder, files in ALL_FILES.items():
        # folder is "FODESNA/historical_ecuador" or "FDAT/..."
        local_dir = os.path.join(target_base, folder)
        os.makedirs(local_dir, exist_ok=True)
        
        for filename in files:
            file_url = f"{BASE_URL}/{folder}/{filename}"
            dest_path = os.path.join(local_dir, filename)
            
            if os.path.exists(dest_path):
                # Check size? For now just skip if exists
                print(f"⏩ {filename} already exists. Skipping.")
                continue
                
            download_file(file_url, dest_path)

if __name__ == "__main__":
    run()

import os
import requests
import sys

# Base URL for raw content (handles LFS redirection usually)
BASE_URL = "https://github.com/ccardenas93/FFLA/raw/main"

# Structure to download
# We focus on FDAT as it contains the national headers (based on previous inspection P_historical_ecuador.nc)
# derived from the user's listing.
FILES_TO_DOWNLOAD = {
    "FDAT/historical_ecuador": [
        "P_historical_ecuador.nc", 
        "T_historical_ecuador.nc",
        # Add others if needed for water balance: wb? pet? 
        # Usually we need P (pr) and T (tas, tasmin, tasmax) to compute PET and WB.
        # But compute_pet.py needs tasmin/tasmax. 
        # Let's check if they exist in FDAT. 
        # User listed FODESNA contents: tasmax_historical_ecuador.nc exists there.
        # I will try to download from FDAT first, if not found, I might need to check the repo deeper.
        # Ideally we download everything needed for the pipeline.
    ],
    "FDAT/ssp126_ecuador": ["pr_ssp126_ecuador.nc", "tas_ssp126_ecuador.nc", "tasmin_ssp126_ecuador.nc", "tasmax_ssp126_ecuador.nc"],
    "FDAT/ssp370_ecuador": ["pr_ssp370_ecuador.nc", "tas_ssp370_ecuador.nc", "tasmin_ssp370_ecuador.nc", "tasmax_ssp370_ecuador.nc"],
    "FDAT/ssp585_ecuador": ["pr_ssp585_ecuador.nc", "tas_ssp585_ecuador.nc", "tasmin_ssp585_ecuador.nc", "tasmax_ssp585_ecuador.nc"],
}

# The user showed FODESNA has:
# pet_historical_ecuador.nc
# pr_historical_ecuador.nc
# tas_historical_ecuador.nc
# tasmax_historical_ecuador.nc
# tasmin_historical_ecuador.nc
# wb_historical_ecuador.nc ... 
#
# It seems "FODESNA" might be the better source for strictly standard names if FDAT has "P_" and "T_".
# Let's switch to downloading from FODESNA for consistency if they are indeed national files (ending in _ecuador.nc).
# Or download both to be safe? 
# The user explicitly linked both FDAT and FODESNA.
# Let's target FODESNA for the standard variables since the names match our pipeline better.

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
    
    # Target directory is ALWAYS inputs/ inside base_dir for the clipper to find it easily
    # The clipper searches in: source_dir/FODESNA, source_dir/inputs/FODESNA etc.
    # Let's put it in inputs/FODESNA to be clean.
    target_base = os.path.join(base_dir, "inputs")
    
    print(f"🚀 Starting Data Download to {target_base}...")
    
    for folder, files in FILES_FODESNA.items():
        # folder is "FODESNA/historical_ecuador"
        # We want: organized/inputs/FODESNA/historical_ecuador
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

import os
import glob
import xarray as xr
from organized.config import settings

def merge_domain(dom):
    # Source: BASE_DIR/dom (national-level merge). Output: DERIVED_DIR/dom (self-contained).
    src = os.path.join(settings.BASE_DIR, dom)
    out = os.path.join(settings.DERIVED_DIR, dom)
    
    os.makedirs(out, exist_ok=True)
    
    for v in settings.VARS:
        # Pattern from original script: *_{v}_*_ecu.nc
        pattern = os.path.join(src, f"*_{v}_*_ecu.nc")
        files = sorted(glob.glob(pattern))
        
        if not files: 
            print(f'  ⚠️ No {v} files found in {dom}')
            continue
            
        print(f'  Merging {len(files)} files for {v} in {dom}...')
        
        try:
            ds = xr.open_mfdataset(files, combine='by_coords')
            enc = {vn: {'zlib': True, 'complevel': 4} for vn in ds.data_vars}
            fn = os.path.join(out, f'{v}_{dom}.nc')
            ds.to_netcdf(fn, encoding=enc)
            print(f'  ✅ Wrote {fn}')
        except Exception as e:
            print(f'  ❌ Error merging {v} in {dom}: {e}')

def run():
    print("="*60)
    print("STEP 1: MERGING DAILY FILES")
    print("="*60)
    os.makedirs(settings.DERIVED_DIR, exist_ok=True)
    
    for d in settings.DOMAINS:
        print(f"\nProcessing domain: {d}")
        merge_domain(d)

if __name__ == "__main__":
    run()

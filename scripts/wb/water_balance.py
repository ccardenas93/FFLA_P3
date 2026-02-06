import os
import xarray as xr
from organized.config import settings

def pr_to_mmday(da):
    u = str(da.attrs.get('units','')).lower().replace('**','^')
    if any(k in u for k in ['kg','s^-1','s-1']):   # flux in SI
        out = da * 86400.0
        out.attrs['units'] = 'mm/day'
        return out
    # already in mm or mm/day
    out = da.copy()
    out.attrs['units'] = 'mm/day'
    return out

def process_domain(input_dir, output_dir, dom):
    """Read pr from input_dir/dom, pet from output_dir/dom; write wb to output_dir/dom."""
    in_path = os.path.join(input_dir, dom)
    out_path = os.path.join(output_dir, dom)
    os.makedirs(out_path, exist_ok=True)

    p_pr = os.path.join(in_path, f'pr_{dom}.nc')
    p_pet = os.path.join(out_path, f'pet_{dom}.nc')
    if not (os.path.exists(p_pr) and os.path.exists(p_pet)):
        if os.path.exists(os.path.join(in_path, 'pr.nc')) and os.path.exists(os.path.join(out_path, 'pet.nc')):
            p_pr = os.path.join(in_path, 'pr.nc')
            p_pet = os.path.join(out_path, 'pet.nc')
        else:
            print(f'    ⚠️ Missing P or PET for {dom} (skipping)')
            return

    try:
        print(f'    Calculating Water Balance for {dom}...')
        dsP = xr.open_dataset(p_pr)
        dsE = xr.open_dataset(p_pet)
        P = pr_to_mmday(dsP['pr' if 'pr' in dsP else 'precip'])
        PET = dsE['pet']
        WB = (P - PET).rename('wb_mmday')
        WB.attrs['units'] = 'mm/day'

        out = os.path.join(out_path, f'wb_{dom}.nc')
        xr.Dataset({'p_mmday': P, 'pet_mmday': PET, 'wb_mmday': WB}).to_netcdf(
            out, encoding={k: {'zlib': True, 'complevel': 4} for k in ['p_mmday', 'pet_mmday', 'wb_mmday']})
        print(f'    ✅ Wrote {out}')

        out_agg = os.path.join(out_path, f'wb_agg_{dom}.nc')
        xr.Dataset({
            'p_mon': P.resample(time='MS').sum('time'),
            'pet_mon': PET.resample(time='MS').sum('time'),
            'wb_mon': WB.resample(time='MS').sum('time'),
            'p_ann': P.resample(time='YS').sum('time'),
            'pet_ann': PET.resample(time='YS').sum('time'),
            'wb_ann': WB.resample(time='YS').sum('time'),
        }).to_netcdf(out_agg)
        print(f'    ✅ Wrote {out_agg}')
    except Exception as e:
        print(f'    ❌ Error in Water Balance for {dom}: {e}')

def run(region_pairs=None):
    """
    Run WB calculation. region_pairs: list of (input_dir, output_dir). Reads pr from input, pet from output; writes wb to output.
    """
    print("\n" + "="*60)
    print("STEP 3: WATER BALANCE & AGGREGATION")
    print("="*60)
    if region_pairs is None:
        region_pairs = [(settings.DERIVED_DIR, settings.DERIVED_DIR)]
    for input_dir, output_dir in region_pairs:
        print(f"\nProcessing: {input_dir} -> {output_dir}")
        for dom in settings.DOMAINS:
            process_domain(input_dir, output_dir, dom)

if __name__ == "__main__":
    run()

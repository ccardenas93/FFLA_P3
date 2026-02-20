import os
import xarray as xr
import numpy as np
from organized.config import settings

def ra_daily_np(lat_deg, doy):
    phi=np.deg2rad(lat_deg)
    dr=1+0.033*np.cos(2*np.pi*doy/365.0)
    delta=0.409*np.sin(2*np.pi*doy/365.0-1.39)
    ws=np.arccos(np.clip(-np.tan(phi)*np.tan(delta), -1, 1))
    Gsc=0.0820
    return (24*60/np.pi)*Gsc*dr*(ws*np.sin(phi)*np.sin(delta)+np.cos(phi)*np.cos(delta)*np.sin(ws))

def as_celsius(da):
    u=str(da.attrs.get('units','')).lower()
    if 'c' in u: return da
    sample=float(da.isel(time=0, lat=da.lat.size//2, lon=da.lon.size//2))
    return da-273.15 if sample>200 else da

def process_domain(input_dir, output_dir, dom):
    """Read tas* from input_dir/dom, write pet to output_dir/dom."""
    in_path = os.path.join(input_dir, dom)
    out_path = os.path.join(output_dir, dom)
    os.makedirs(out_path, exist_ok=True)

    pmin = os.path.join(in_path, f'tasmin_{dom}.nc')
    pmax = os.path.join(in_path, f'tasmax_{dom}.nc')
    pavg = os.path.join(in_path, f'tas_{dom}.nc')
    if not (os.path.exists(pmin) and os.path.exists(pmax) and os.path.exists(pavg)):
        pmin_alt = os.path.join(in_path, 'tasmin.nc')
        if os.path.exists(pmin_alt):
            pmin = pmin_alt
            pmax = os.path.join(in_path, 'tasmax.nc')
            pavg = os.path.join(in_path, 'tas.nc')
        else:
            print(f'    ⚠️ Missing Temperature files for {dom} in {in_path} (skipping)')
            return

    try:
        print(f'    Calculating PET for {dom}...')
        dsmin = xr.open_dataset(pmin)
        dsmax = xr.open_dataset(pmax)
        dst = xr.open_dataset(pavg)
        tmin = as_celsius(dsmin['tasmin' if 'tasmin' in dsmin else 'tmin'])
        tmax = as_celsius(dsmax['tasmax' if 'tasmax' in dsmax else 'tmax'])
        tmean = as_celsius(dst['tas' if 'tas' in dst else 'tmean'])

        lat = tmin['lat']
        doy = tmin['time'].dt.dayofyear
        LAT, DOY = xr.broadcast(lat, doy)
        Ra = xr.apply_ufunc(ra_daily_np, LAT, DOY, dask='allowed')
        Ra = Ra.transpose('lat', 'time').expand_dims({'lon': tmin['lon']}).transpose('time', 'lat', 'lon')

        PET = 0.0023 * Ra * (tmean + 17.8) * ((tmax - tmin).clip(min=0)) ** 0.5
        PET = PET.rename('pet')
        PET.attrs.update(units='mm/day', long_name='Hargreaves PET')

        out_file = os.path.join(out_path, f'pet_{dom}.nc')
        PET.to_netcdf(out_file, encoding={'pet': {'zlib': True, 'complevel': 4}})
        print(f'    ✅ Wrote {out_file}')
    except Exception as e:
        print(f'    ❌ Error calculating PET for {dom}: {e}')

def run(region_pairs=None):
    """
    Run PET calculation. region_pairs: list of (input_dir, output_dir). Reads from input, writes to output.
    """
    print("\n" + "="*60)
    print("STEP 2: COMPUTING PET (Hargreaves)")
    print("="*60)
    if region_pairs is None:
        region_pairs = [(settings.DERIVED_DIR, settings.DERIVED_DIR)]
    for input_dir, output_dir in region_pairs:
        print(f"\nProcessing: {input_dir} -> {output_dir}")
        for dom in settings.DOMAINS:
            process_domain(input_dir, output_dir, dom)

if __name__ == "__main__":
    run()

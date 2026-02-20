
import os
import sys
import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from organized.config import settings

ROOTS = [info["path"] for info in settings.REGIONS.values()]
DOMAINS = settings.DOMAINS

PERIOD = ("1980-01-01","2100-12-31")

def pr_to_mmday(da):
    u = str(da.attrs.get('units','')).lower().replace('**','^')
    if any(k in u for k in ['kg','s^-1','s-1']):
        out = da * 86400.0
        out.attrs['units'] = 'mm/day'
        return out
    out = da.copy()
    out.attrs['units'] = 'mm/day'
    return out

def wmean(da):
    """Proper area-weighted mean with cos(lat) weighting."""
    w = np.cos(np.deg2rad(da["lat"]))
    num = (da * w).sum("lat")
    den = w.sum("lat")
    return (num / den).mean("lon")

def ra_daily_np(lat_deg, doy):
    phi=np.deg2rad(lat_deg)
    dr  = 1 + 0.033*np.cos(2*np.pi*doy/365.0)
    delta = 0.409*np.sin(2*np.pi*doy/365.0 - 1.39)
    ws  = np.arccos(np.clip(-np.tan(phi)*np.tan(delta), -1, 1))
    Gsc = 0.0820
    return (24*60/np.pi)*Gsc*dr*(ws*np.sin(phi)*np.sin(delta)+np.cos(phi)*np.cos(delta)*np.sin(ws))

def as_celsius(da):
    u=str(da.attrs.get('units','')).lower()
    if 'c' in u: return da
    sample=float(da.isel(time=0, lat=da.lat.size//2, lon=da.lon.size//2))
    return da-273.15 if sample>200 else da

def sanity_recompute_pet(root, dom, npts=3):
    """Recompute PET at npts random grid cells and compare with saved pet."""
    pmin=f'{root}/{dom}/tasmin_{dom}.nc'
    pmax=f'{root}/{dom}/tasmax_{dom}.nc'
    pavg=f'{root}/{dom}/tas_{dom}.nc'
    ppet=f'{root}/{dom}/pet_{dom}.nc'
    if not all(os.path.exists(p) for p in [pmin,pmax,pavg,ppet]): return []

    dsmin=xr.open_dataset(pmin).sel(time=slice(*PERIOD))
    dsmax=xr.open_dataset(pmax).sel(time=slice(*PERIOD))
    dst =xr.open_dataset(pavg).sel(time=slice(*PERIOD))
    dsp =xr.open_dataset(ppet).sel(time=slice(*PERIOD))

    tmin=as_celsius(dsmin['tasmin']); tmax=as_celsius(dsmax['tasmax']); tmean=as_celsius(dst['tas'])
    lat = tmin['lat']; lon = tmin['lon']; time=tmin['time']
    doy = time.dt.dayofyear

    LAT, DOY = xr.broadcast(lat, doy)
    Ra = xr.apply_ufunc(ra_daily_np, LAT, DOY, dask='allowed')
    Ra = Ra.transpose('lat','time').expand_dims({'lon': lon}).transpose('time','lat','lon')

    pet_calc = 0.0023*Ra*(tmean+17.8)*((tmax-tmin).clip(min=0))**0.5
    pet_file = dsp['pet']


    rng=np.random.default_rng(42)
    I = rng.integers(0, lat.size, size=min(npts, lat.size))
    J = rng.integers(0, lon.size, size=min(npts, lon.size))
    rows=[]
    for i,j in zip(I,J):
        a = float(pet_calc.isel(lat=i, lon=j).mean('time'))
        b = float(pet_file.isel(lat=i, lon=j).mean('time'))
        rows.append({'lat': float(lat[i]), 'lon': float(lon[j]), 'PET_recomputed_mmday': a, 'PET_file_mmday': b, 'diff': b-a})
    return rows

def summarize_domain(root, dom):
    paths = {
        'wb':  f'{root}/{dom}/wb_{dom}.nc',
        'agg': f'{root}/{dom}/wb_agg_{dom}.nc',
        'pr':  f'{root}/{dom}/pr_{dom}.nc',
        'pet': f'{root}/{dom}/pet_{dom}.nc',
    }
    if not all(os.path.exists(p) for p in [paths['wb'], paths['agg'], paths['pr'], paths['pet']]):
        print("missing inputs for", root.split('/')[-1], dom); return

    ds_wb  = xr.open_dataset(paths['wb']).sel(time=slice(*PERIOD))
    ds_agg = xr.open_dataset(paths['agg'])
    ds_pr  = xr.open_dataset(paths['pr']).sel(time=slice(*PERIOD))
    ds_pet = xr.open_dataset(paths['pet']).sel(time=slice(*PERIOD))

    P   = pr_to_mmday(ds_wb['p_mmday'] if 'p_mmday' in ds_wb else ds_pr['pr'])
    PET = ds_wb['pet_mmday'] if 'pet_mmday' in ds_wb else ds_pet['pet']
    WB  = P - PET

    p_mean   = float(wmean(P).mean('time'))
    pet_mean = float(wmean(PET).mean('time'))
    wb_mean  = float(wmean(WB).mean('time'))


    mon = pd.DataFrame({
        'P':   wmean(P).resample(time='MS').sum('time').groupby('time.month').mean().to_pandas(),
        'PET': wmean(PET).resample(time='MS').sum('time').groupby('time.month').mean().to_pandas(),
        'WB':  wmean(WB).resample(time='MS').sum('time').groupby('time.month').mean().to_pandas(),
    })
    out_mon = os.path.join(root, dom, f'WB_monthly_clim_{dom}_{PERIOD[0][:4]}_{PERIOD[1][:4]}.csv')
    mon.to_csv(out_mon)

    print(f"\n[{root.split('/')[-1]}] {dom}")
    print(f"  Annual mean P   : {p_mean:6.2f} mm/day")
    print(f"  Annual mean PET : {pet_mean:6.2f} mm/day")
    print(f"  Annual mean WB  : {wb_mean:6.2f} mm/day  (P - PET)")
    if pet_mean>8: print("  ⚠ PET unusually high; check units/temps")
    if p_mean<1:   print("  ⚠ Very low P; clipped area might be dry or units wrong")


    sample_rows = sanity_recompute_pet(root, dom, npts=3)
    if sample_rows:
        df=pd.DataFrame(sample_rows)
        print(df.round(3).to_string(index=False))

for root in ROOTS:
    for dom in DOMAINS:
        summarize_domain(root, dom)

import os
import sys
import numpy as np
import pandas as pd
import xarray as xr

# Self-contained: use repo config from any cwd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from organized.config import settings
DERIVED = settings.DERIVED_DIR
DOMAINS = settings.DOMAINS

FAILS=[]; WARNS=[]
def fail(msg): FAILS.append(msg); print("❌",msg)
def warn(msg): WARNS.append(msg); print("⚠️",msg)
def ok(msg): print("✅",msg)

def check_open(path,var):
    if not os.path.exists(path): fail(f"missing file: {path}"); return None
    try: ds=xr.open_dataset(path); 
    except Exception as e: fail(f"cannot open {path}: {e}"); return None
    if var not in ds: fail(f"{os.path.basename(path)} missing var '{var}'"); return None
    return ds

def check_coords(ds,dom,var):
    cds=set(ds.coords); 
    for c in ['time','lat','lon']:
        if c not in cds: fail(f"{dom}:{var} missing coord '{c}'")
    if 'lat' in ds and not np.all(np.diff(ds['lat'])>0): fail(f"{dom}:{var} lat not strictly increasing")
    if 'lon' in ds and not np.all(np.diff(ds['lon'])>0): fail(f"{dom}:{var} lon not strictly increasing")
    # Ecuador bbox guard (loose)
    if 'lat' in ds and (ds.lat.min()< -6 or ds.lat.max()> 3): warn(f"{dom}:{var} lat extent unexpected: {float(ds.lat.min())}..{float(ds.lat.max())}")
    if 'lon' in ds and (ds.lon.min()< -82 or ds.lon.max()>-74): warn(f"{dom}:{var} lon extent unexpected: {float(ds.lon.min())}..{float(ds.lon.max())}")

def check_time(ds,dom,var):
    t=ds['time'].values
    if pd.Index(t).has_duplicates: fail(f"{dom}:{var} time has duplicates")
    dt=pd.Series(pd.to_datetime(t)).diff().dropna().dt.days
    if not len(dt): return
    if not (dt.mode().iloc[0]==1): warn(f"{dom}:{var} cadence mode={dt.mode().iloc[0]}d (expected 1d)")
    gaps=(dt>1).sum()
    if gaps>0: warn(f"{dom}:{var} has {gaps} gap(s) >1 day")
    if (dt<=0).any(): fail(f"{dom}:{var} non-monotonic time diffs ≤0")

def check_units(ds,dom,var):
    u=str(ds[var].attrs.get('units','')).strip().lower()
    if var=='pr' and u not in ['kg m-2 s-1','kg m**-2 s**-1','kg m-2 s-1.','kg m-2 s^-1']: warn(f"{dom}:{var} units '{u}' (expected kg m-2 s-1)")
    if var in ['tas','tasmin','tasmax'] and u not in ['k','kelvin','kelvins']: warn(f"{dom}:{var} units '{u}' (expected K)")

def nan_rate(ds,dom,var):
    da=ds[var]; frac=float(da.isnull().mean())
    if frac>0.01: warn(f"{dom}:{var} NaN rate {frac:.2%} (>1%)")

def arrays_equal(a,b): return a.size==b.size and np.allclose(a,b,equal_nan=False)

def validate_domain(dom):
    print("\n=== DOMAIN:",dom,"===")
    pdir=f"{DERIVED}/{dom}"
    paths={v:f"{pdir}/{v}_{dom}.nc" for v in ['pr','tas','tasmin','tasmax']}
    dsets={v:check_open(paths[v],v) for v in paths}
    if any(ds is None for ds in dsets.values()): return
    # coords & time & units per var
    for v,ds in dsets.items():
        check_coords(ds,dom,v); check_time(ds,dom,v); check_units(ds,dom,v); nan_rate(ds,dom,v)
    # grid equality
    lats={v: dsets[v]['lat'].values for v in dsets}
    lons={v: dsets[v]['lon'].values for v in dsets}
    for v in ['tas','tasmin','tasmax']:
        if not arrays_equal(lats['pr'],lats[v]): fail(f"{dom}: lat grid pr vs {v} differ")
        if not arrays_equal(lons['pr'],lons[v]): fail(f"{dom}: lon grid pr vs {v} differ")
    # time alignment
    idx={v: pd.Index(pd.to_datetime(dsets[v]['time'].values)) for v in dsets}
    inter=idx['pr'].intersection(idx['tas']).intersection(idx['tasmin']).intersection(idx['tasmax'])
    for v in idx:
        miss=len(idx[v])-len(inter)
        if miss!=0: warn(f"{dom}:{v} has {miss} timestamp(s) not shared by all")
    # physical consistency
    try:
        tmin=dsets['tasmin']['tasmin']; t=dsets['tas']['tas']; tmax=dsets['tasmax']['tasmax']
        bad_min=((t<tmin)-False).sum().item()
        bad_max=((t>tmax)-False).sum().item()
        bad_spread=((tmax<tmin)-False).sum().item()
        if bad_min or bad_max or bad_spread:
            warn(f"{dom}: tas outside [tasmin,tasmax] count: below={bad_min}, above={bad_max}, inverted_spread={bad_spread}")
        else:
            ok(f"{dom}: tas within [tasmin,tasmax]")
    except Exception as e:
        warn(f"{dom}: couldn’t check tas range: {e}")
    ok(f"{dom}: validation completed")

for dom in DOMAINS: validate_domain(dom)
print("\n==== SUMMARY ====")
if FAILS: print("Failures:",len(FAILS)); [print(" -",m) for m in FAILS]
if WARNS: print("Warnings:",len(WARNS)); [print(" -",m) for m in WARNS]
sys.exit(1 if FAILS else 0)
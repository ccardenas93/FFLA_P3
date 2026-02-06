#!/usr/bin/env python3
import os
import sys
import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from organized.config import settings

# Use repo regions (self-contained)
TOP_ROOTS = [info["path"] for info in settings.REGIONS.values()]
DOMAINS = settings.DOMAINS

PERIOD_START, PERIOD_END = 1980, 2100   # set both to None to keep full span

def wlat(lat): return xr.DataArray(np.cos(np.deg2rad(lat)), coords={'lat': lat}, dims=['lat'])
def wmean(da): return da.weighted(wlat(da['lat'])).mean(('lat','lon'))

for ROOT in TOP_ROOTS:
    for dom in DOMAINS:
        p=os.path.join(ROOT, dom, f"wb_agg_{dom}.nc")
        if not os.path.exists(p):
            print("missing", p); continue
        ds=xr.open_dataset(p)

        if PERIOD_START is not None and PERIOD_END is not None:
            ds=ds.sel(time=slice(f"{PERIOD_START}-01-01", f"{PERIOD_END}-12-31"))

        # Monthly table (mm/month)
        tmon = ds["p_mon"]["time"]
        mon_df = pd.DataFrame({
            "Year":  tmon.dt.year.values,
            "Month": tmon.dt.month.values,
            "P_mon_mm":   wmean(ds["p_mon"]).values,
            "PET_mon_mm": wmean(ds["pet_mon"]).values,
            "WB_mon_mm":  wmean(ds["wb_mon"]).values,
        })
        # Annual table (mm/yr)
        tann = ds["p_ann"]["time"]
        ann_df = pd.DataFrame({
            "Year": tann.dt.year.values,
            "P_ann_mm":   wmean(ds["p_ann"]).values,
            "PET_ann_mm": wmean(ds["pet_ann"]).values,
            "WB_ann_mm":  wmean(ds["wb_ann"]).values,
        })

        out_dir=os.path.join(ROOT, dom)
        mon_df.to_csv(os.path.join(out_dir, f"wb_monthly_mean_{dom}.csv"), index=False)
        ann_df.to_csv(os.path.join(out_dir, f"wb_annual_mean_{dom}.csv"), index=False)
        print("wrote CSVs for", os.path.basename(ROOT), dom)
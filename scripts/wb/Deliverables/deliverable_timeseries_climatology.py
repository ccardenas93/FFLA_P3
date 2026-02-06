#!/usr/bin/env python3
import sys
import os
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from organized.config import settings

DOMS = settings.DOMAINS
VENTANAS = {
    "Base 1981–2010":("1981","2010"),
    "Cercano 2021–2050":("2021","2050"),
    "Medio 2041–2070":("2041","2070"),
    "Tardío 2071–2100":("2071","2100"),
}
MESES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
COL = settings.PALETTE

def wlat(lat): return xr.DataArray(np.cos(np.deg2rad(lat)), coords={'lat': lat}, dims=['lat'])
def wmean(da): return da.weighted(wlat(da['lat'])).mean(('lat','lon'))

def mean_series(path, var, t0, t1):  # var in wb_{dom}.nc (p_mmday, pet_mmday, wb_mmday)
    if not os.path.exists(path): return None
    ds = xr.open_dataset(path).sel(time=slice(f"{t0}-01-01", f"{t1}-12-31"))
    if ds.sizes.get("time",0)==0: return None
    if var not in ds: return None
    
    # Correct order: spatial average first (on daily), then monthly sum, then climatology
    daily_mean = wmean(ds[var])  # mm/day, area-averaged
    mon = daily_mean.resample(time="MS").sum("time")  # mm/month
    s = mon.groupby("time.month").mean("time").to_pandas()
    s.index = range(1,13)
    return s

def run():
    print("\n" + "="*60)
    print("GENERATING MONTHLY CLIMATOLOGY TIMESERIES (DELIVERABLE)")
    print("="*60)

    var_cat = {"p_mmday": settings.OUT_CAT_CLIMATOLOGIA_P, "pet_mmday": settings.OUT_CAT_CLIMATOLOGIA_PET, "wb_mmday": settings.OUT_CAT_CLIMATOLOGIA_WB}
    period_name = {("1981", "2010"): "base_1981-2010.png", ("2021", "2050"): "cercano_2021-2050.png", ("2041", "2070"): "medio_2041-2070.png", ("2071", "2100"): "tardio_2071-2100.png"}
    for region_code, region_info in settings.REGIONS.items():
        output_dir = settings.get_region_output_dir(region_code)
        print(f"Processing region: {region_info['name']} ({output_dir})")

        for var, ylab in [("p_mmday", "Precipitación (mm/mes)"),
                          ("pet_mmday", "Evapotranspiración (mm/mes)"),
                          ("wb_mmday", "Balance hídrico (mm/mes)")]:
            for nombre, (t0, t1) in VENTANAS.items():
                plt.figure(figsize=(8, 4))
                for d in DOMS:
                    path = os.path.join(output_dir, d, f"wb_{d}.nc")
                    if not os.path.exists(path):
                        path = os.path.join(output_dir, d, "wb.nc")
                    s = mean_series(path, var, t0, t1)
                    if s is None:
                        continue
                    c = COL.get(d, "tab:blue")
                    plt.plot(range(1, 13), s.values, lw=2, color=c, label=d.replace("_ecuador", ""))
                plt.xticks(range(1, 13), MESES)
                plt.grid(True, alpha=0.3)
                plt.ylabel(ylab)
                plt.title(f"{ylab} | {nombre}")
                plt.legend(ncol=4, fontsize=8)
                fn = period_name.get((t0, t1), f"{t0}-{t1}.png")
                out_path = settings.fig_path(output_dir, var_cat[var], fn)
                plt.tight_layout()
                plt.savefig(out_path, dpi=180)
                plt.close()
                print(f"  Generated: {fn}")

if __name__ == "__main__":
    run()

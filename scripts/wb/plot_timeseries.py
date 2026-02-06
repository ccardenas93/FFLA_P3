#!/usr/bin/env python3
import sys
import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

# Add project root to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from organized.config import settings

PERIOD_START = settings.PERIOD_START
PERIOD_END = settings.PERIOD_END

def wlat(lat):
    return xr.DataArray(np.cos(np.deg2rad(lat)), coords={'lat': lat}, dims=['lat'])

def wmean(da):
    return da.weighted(wlat(da['lat'])).mean(('lat','lon'))

def load_ann(data_dir, dom):
    """data_dir = output dir where wb_agg_*.nc lives."""
    p = os.path.join(data_dir, dom, f"wb_agg_{dom}.nc")
    if not os.path.exists(p): return None, None
    ds=xr.open_dataset(p)
    years = xr.DataArray(ds["p_ann"]["time"]).dt.year.values
    p_ann   = wmean(ds["p_ann"]).values
    pet_ann = wmean(ds["pet_ann"]).values
    wb_ann  = wmean(ds["wb_ann"]).values
    m = (years >= PERIOD_START) & (years <= PERIOD_END)
    if m.sum()==0: return None, None
    return years[m], {"P":p_ann[m], "PET":pet_ann[m], "WB":wb_ann[m]}

def roll_nanmean(y, k, min_frac=0.6):
    y = np.asarray(y, float)
    n = len(y)
    out = np.full(n, np.nan)
    if k <= 1 or n < 2: return y
    half = k // 2
    min_pts = max(1, int(np.ceil(k * min_frac)))
    for i in range(n):
        a = max(0, i-half); b = min(n, i+half+1)
        w = y[a:b]; valid = np.isfinite(w)
        if valid.sum() >= min_pts:
            out[i] = w[valid].mean()
    return out

def run():
    print("\n" + "="*60)
    print("GENERANDO SERIES TEMPORALES (ESPAÑOL)")
    print("="*60)
    
    palette = settings.PALETTE
    
    out_cat = settings.OUT_CAT_SERIES_HIDRO
    file_map = {"P": "precipitacion_anual.png", "PET": "evapotranspiracion_anual.png", "WB": "balance_hidrico_anual.png"}

    for region_code, region_info in settings.REGIONS.items():
        output_dir = settings.get_region_output_dir(region_code)
        print(f"Procesando región: {region_info['name']} ({output_dir})")

        for var, ylabel in [("P", "Precipitación (mm/año)"),
                            ("PET", "Evapotranspiración Potencial (mm/año)"),
                            ("WB", "Balance Hídrico (mm/año)")]:
            fig = plt.figure(figsize=(10, 4))
            drew = False
            for dom in settings.DOMAINS:
                years, dat = load_ann(output_dir, dom)
                if years is None:
                    continue
                y = dat[var]
                span = int(years[-1] - years[0] + 1)
                win = min(11, max(3, (span // 15) * 2 + 1))
                y_smooth = roll_nanmean(y, win, min_frac=0.6)
                c = palette.get(dom, "tab:blue")
                plt.scatter(years, y, s=10, alpha=0.4, color=c)
                dom_label = dom.replace("_ecuador", "")
                if dom_label == "historical":
                    dom_label = "Histórico"
                plt.plot(years, y_smooth, lw=2, color=c, label=dom_label)
                drew = True
            plt.title(f"{region_info['name']}: {ylabel}, {PERIOD_START}–{PERIOD_END}")
            plt.xlabel("Año")
            plt.ylabel(ylabel)
            plt.grid(True, alpha=0.3)
            if drew:
                plt.legend(ncol=4, fontsize=8)
            plt.tight_layout()
            output_file = settings.fig_path(output_dir, out_cat, file_map[var])
            plt.savefig(output_file, dpi=180)
            plt.close(fig)
            print(f"  Generado: {os.path.basename(output_file)}")

if __name__ == "__main__":
    run()

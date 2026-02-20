#!/usr/bin/env python3
import os
import sys
import xarray as xr
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from organized.config import settings


TOP_ROOTS = [info["path"] for info in settings.REGIONS.values()]
DOMAINS_FUT = [d for d in settings.DOMAINS if "historical" not in d]

BASE = (str(settings.BASE_PERIOD[0]), str(settings.BASE_PERIOD[1]))
FUT = ("2081", "2100")

def mean_period(root, domain, var, t0, t1):
    p=f'{root}/{domain}/wb_{domain}.nc'
    if not os.path.exists(p): return None
    ds=xr.open_dataset(p)
    return ds[var].sel(time=slice(f'{t0}-01-01', f'{t1}-12-31')).mean('time')

def plot_field(ax, lat, lon, field, title, cmap='viridis', vmin=None, vmax=None):
    m=ax.pcolormesh(lon, lat, field, shading='auto', cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(title); ax.set_xlabel('Lon'); ax.set_ylabel('Lat'); ax.grid(True, alpha=.2); return m

vars_map=[('p_mmday','P (mm/day)'),('pet_mmday','PET (mm/day)'),('wb_mmday','WB (mm/day)')]

for ROOT in TOP_ROOTS:
    OUT=f"{ROOT}/figs"; os.makedirs(OUT, exist_ok=True)
    for var,label in vars_map:
        base = mean_period(ROOT, 'historical_ecuador', var, *BASE)
        if base is None: continue
        lat,lon = base['lat'].values, base['lon'].values
        fig,axes=plt.subplots(1, 1+len(DOMAINS_FUT), figsize=(14,3.8), sharey=True)
        m0=plot_field(axes[0], lat, lon, base.values, f'Baseline {BASE[0]}–{BASE[1]} {label}')
        fig.colorbar(m0, ax=axes[0], fraction=0.046, pad=0.04)
        for i,dom in enumerate(DOMAINS_FUT, start=1):
            fut = mean_period(ROOT, dom, var, *FUT)
            if fut is None:
                axes[i].set_title(dom+' (missing)'); axes[i].axis('off'); continue
            delta = (fut - base).values
            m=plot_field(axes[i], lat, lon, delta, f'{dom.replace("_ecuador","")} Δ{FUT[0]}–{FUT[1]}', cmap='RdBu_r')
            fig.colorbar(m, ax=axes[i], fraction=0.046, pad=0.04)
        plt.tight_layout()
        plt.savefig(os.path.join(OUT, f'maps_{var.replace("_mmday","")}_{BASE[0]}_{BASE[1]}_{FUT[0]}_{FUT[1]}.png'), dpi=180)
        plt.close()
    print("wrote figures to", OUT)

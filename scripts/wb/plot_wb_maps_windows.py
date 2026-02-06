#!/usr/bin/env python3
import sys
import os
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

# --- PROJ/GDAL setup (portable: env or Python prefix for exe/bundled) ---
_prefix = os.environ.get("CONDA_PREFIX") or getattr(sys, "prefix", "")
if _prefix:
    os.environ.setdefault("PROJ_LIB", os.path.join(_prefix, "share", "proj"))
    os.environ.setdefault("GDAL_DATA", os.path.join(_prefix, "share", "gdal"))
try:
    from pyproj import datadir, CRS
    if os.environ.get("PROJ_LIB"):
        datadir.set_data_dir(os.environ["PROJ_LIB"])
    CRS.from_epsg(4326)
except Exception:
    pass

import geopandas as gpd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from organized.config import settings

SCENS = [d for d in settings.DOMAINS if "historical" not in d]
WIN = {
    "Base (1981–2010)": ("1981","2010"),
    "Cercano (2021–2050)": ("2021","2050"),
    "Medio (2041–2070)": ("2041","2070"),
    "Tardío (2071–2100)": ("2071","2100"),
}

_cache_geo = {}
def cargar_shp(path):
    if path in _cache_geo: return _cache_geo[path]
    if not os.path.exists(path): return None
    g = gpd.read_file(path)
    try:
        if g.crs is None or g.crs.to_epsg() != 4326:
            g = g.to_crs("EPSG:4326")
    except Exception:
        pass
    _cache_geo[path] = g
    return g

def mean_wb(data_dir, domain, t0, t1):
    p = os.path.join(data_dir, domain, f"wb_{domain}.nc")
    if not os.path.exists(p):
        p = os.path.join(data_dir, domain, "wb.nc")
    if not os.path.exists(p): return None
    ds = xr.open_dataset(p).sel(time=slice(f"{t0}-01-01", f"{t1}-12-31"))
    if ds.sizes.get("time", 0) == 0: return None
    # mm/day -> mm/year
    if "wb_mmday" not in ds: return None
    return (ds["wb_mmday"].mean("time")*365.0)

def pmesh(ax, lat, lon, field, title, cmap="RdBu", vmin=None, vmax=None):
    m = ax.pcolormesh(lon, lat, field, shading="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.grid(True, alpha=.2)
    return m

def run():
    print("\n" + "="*60)
    print("GENERANDO MAPAS DE BALANCE HÍDRICO (ESPAÑOL)")
    print("="*60)

    for region_code, region_info in settings.REGIONS.items():
        output_dir = settings.get_region_output_dir(region_code)
        print(f"Procesando región: {region_info['name']} ({output_dir})")

        base = mean_wb(output_dir, "historical_ecuador", *WIN["Base (1981–2010)"])
        if base is None: 
             print(f"  ⚠️ Sin datos de línea base para {region_info['name']}")
             continue
        lat, lon = base["lat"].values, base["lon"].values
        
        shp_path = region_info.get("shapefile")
        geo = cargar_shp(shp_path) if shp_path else None

        base_vals = base.values
        base_max = np.nanmax(np.abs(base_vals))
        base_lim = np.ceil(base_max / 100) * 100  
        
        all_deltas = []
        for scen in SCENS:
            for label, (t0, t1) in WIN.items():
                if label.startswith("Base"): continue
                fut = mean_wb(output_dir, scen, t0, t1)
                if fut is not None:
                    d = (fut - base).values
                    all_deltas.append(d.ravel())
        
        if all_deltas:
            all_deltas = np.concatenate([x[np.isfinite(x)] for x in all_deltas if np.any(np.isfinite(x))])
            delta_min = np.nanmin(all_deltas)
            delta_max = np.nanmax(all_deltas)
            
            if delta_max <= 0:
                vmin_delta = np.floor(delta_min / 100) * 100
                vmax_delta = 0
                cmap_delta = "Reds_r"
            elif delta_min >= 0:
                vmin_delta = 0
                vmax_delta = np.ceil(delta_max / 100) * 100
                cmap_delta = "Blues"
            else:
                abs_max = max(abs(delta_min), abs(delta_max))
                vmax_delta = np.ceil(abs_max / 100) * 100
                vmin_delta = -vmax_delta
                cmap_delta = "RdBu"
        else:
            vmin_delta, vmax_delta = -800, 800
            cmap_delta = "RdBu"
        
        fig, axes = plt.subplots(len(SCENS), len(WIN), figsize=(16, 8), sharex=True, sharey=True)
        if len(SCENS) == 1: axes = axes[np.newaxis, :]

        for j, scen in enumerate(SCENS):
            for i, (label, (t0, t1)) in enumerate(WIN.items()):
                ax = axes[j, i]
                if label.startswith("Base"):
                    m = pmesh(ax, lat, lon, base.values, f"{label}\nBalance Hídrico (mm/año)", cmap="RdBu", vmin=-base_lim, vmax=base_lim)
                    if geo is not None:
                        geo.boundary.plot(ax=ax, edgecolor="k", linewidth=0.9, zorder=5)
                    if i == 0: fig.colorbar(m, ax=ax, fraction=0.046, pad=0.04)
                    continue
                
                fut = mean_wb(output_dir, scen, t0, t1)
                if fut is None:
                    ax.set_title(label + " (sin datos)")
                    ax.axis("off")
                    continue
                
                d = (fut - base).values
                m = pmesh(ax, lat, lon, d, f"{scen.replace('_ecuador','').upper()} Δ{t0}–{t1}", cmap=cmap_delta, vmin=vmin_delta, vmax=vmax_delta)
                if geo is not None:
                    geo.boundary.plot(ax=ax, edgecolor="k", linewidth=0.9, zorder=5)
                fig.colorbar(m, ax=ax, fraction=0.046, pad=0.04)
        
        plt.tight_layout()
        output_file = settings.fig_path(output_dir, settings.OUT_CAT_MATRIZ_VENTANAS, "matriz_WB_escenarios_ventanas.png")
        plt.savefig(output_file, dpi=180)
        plt.close()
        print(f"  Generado: {os.path.basename(output_file)}")

if __name__ == "__main__":
    run()

#!/usr/bin/env python3
import sys
import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt


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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from organized.config import settings

SCENS = [d for d in settings.DOMAINS if "historical" not in d]
BASE = settings.BASE_PERIOD
FUT_WIN = ("2071","2100")
MESES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

def triple_meses_str(start_m):
    idx = [start_m, ((start_m) % 12) + 1, ((start_m + 1) % 12) + 1]
    return "–".join(MESES[i-1] for i in idx), idx

def trimestral(ds):
    mon = ds["wb_mmday"].resample(time="MS").sum("time")
    clim = mon.groupby("time.month").mean("time")
    vals=[]
    for start in range(1,13):
        _, idx = triple_meses_str(start)
        vals.append((start, clim.sel(month=idx).sum("month")))
    mins = min(vals, key=lambda x: np.nanmean(x[1].values))
    maxs = max(vals, key=lambda x: np.nanmean(x[1].values))
    return mins, maxs

def pm(ax, lat, lon, fld, ttl, vmin=None, vmax=None, cmap="bwr_r"):
    im = ax.pcolormesh(lon, lat, fld, shading="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(ttl, fontsize=10); ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud"); ax.grid(True, alpha=.2)
    return im

def run():
    print("\n" + "="*60)
    print("GENERATING SEASONAL EXTREME MAPS")
    print("="*60)

    for region_code, region_info in settings.REGIONS.items():
        output_dir = settings.get_region_output_dir(region_code)
        print(f"Processing region: {region_info['name']} ({output_dir})")

        shp = region_info.get("shapefile")
        geo = None
        if shp and os.path.exists(shp):
            geo = gpd.read_file(shp)
            try:
                if geo.crs is None or geo.crs.to_epsg() != 4326:
                    geo = geo.to_crs("EPSG:4326")
            except Exception: pass

        pbase = os.path.join(output_dir, "historical_ecuador", "wb_historical_ecuador.nc")
        if not os.path.exists(pbase):
            pbase = os.path.join(output_dir, "historical_ecuador", "wb.nc")

        if not os.path.exists(pbase):
            print("  ⚠️ Missing baseline data"); continue

        dsb = xr.open_dataset(pbase).sel(time=slice(f"{BASE[0]}-01-01", f"{BASE[1]}-12-31"))
        (msec, wb_sec), (mhum, wb_hum) = trimestral(dsb)
        lat, lon = wb_sec["lat"].values, wb_sec["lon"].values
        etiqueta_seco, idx_seco = triple_meses_str(msec)
        etiqueta_hum,  idx_hum  = triple_meses_str(mhum)

        both = np.concatenate([wb_sec.values.ravel(), wb_hum.values.ravel()])
        lo, hi = np.nanpercentile(both, [2, 98])
        vm = float(np.ceil(max(abs(lo), abs(hi), 100) / 100) * 100)


        fig, axs = plt.subplots(1, 2, figsize=(12, 4), sharex=True, sharey=True)
        im0 = pm(axs[0], lat, lon, wb_sec.values, f"Trimestre más seco ({etiqueta_seco}) | 1981–2010", -vm, vm, "bwr_r")
        im1 = pm(axs[1], lat, lon, wb_hum.values, f"Trimestre más húmedo ({etiqueta_hum}) | 1981–2010", -vm, vm, "bwr_r")
        if geo is not None:
             for ax in axs: geo.boundary.plot(ax=ax, edgecolor="k", linewidth=.9)
        cax = fig.add_axes([1.02, 0.25, 0.02, 0.5])
        cb = fig.colorbar(im1, cax=cax)
        cb.set_label("Balance hídrico (mm/3 meses)\nAzul = superávit | Rojo = déficit")
        plt.tight_layout(rect=[0, 0, 0.98, 1])
        out_file = settings.fig_path(output_dir, settings.OUT_CAT_TRIMESTRES_BASE, "WB_trimestres_base_1981-2010.png")
        plt.savefig(out_file, dpi=180, bbox_inches="tight")
        plt.close()
        print(f"  Generated: {os.path.basename(out_file)}")

        for scen in SCENS:
            pfut = os.path.join(output_dir, scen, f"wb_{scen}.nc")
            if not os.path.exists(pfut):
                pfut = os.path.join(output_dir, scen, "wb.nc")
            if not os.path.exists(pfut): continue

            dsf = xr.open_dataset(pfut).sel(time=slice(f"{FUT_WIN[0]}-01-01", f"{FUT_WIN[1]}-12-31"))
            mon = dsf["wb_mmday"].resample(time="MS").sum("time").groupby("time.month").mean("time")

            fut_sec = mon.sel(month=idx_seco).sum("month")
            fut_hum = mon.sel(month=idx_hum).sum("month")
            dsec = (fut_sec - wb_sec).values
            dhum = (fut_hum - wb_hum).values
            vm2 = float(np.nanpercentile(np.abs(np.concatenate([dsec.ravel(), dhum.ravel()])), 98))
            vm2 = float(np.ceil(max(vm2, 50) / 50) * 50)

            fig, axs = plt.subplots(1, 2, figsize=(12, 4), sharex=True, sharey=True)
            im0 = pm(axs[0], lat, lon, dsec, f"{scen.replace('_ecuador','')} Δ Trimestre seco ({etiqueta_seco}) 2071–2100", -vm2, vm2, "bwr_r")
            im1 = pm(axs[1], lat, lon, dhum, f"{scen.replace('_ecuador','')} Δ Trimestre húmedo ({etiqueta_hum}) 2071–2100", -vm2, vm2, "bwr_r")
            if geo is not None:
                 for ax in axs: geo.boundary.plot(ax=ax, edgecolor="k", linewidth=.9)
            cax = fig.add_axes([1.02, 0.25, 0.02, 0.5])
            cb = fig.colorbar(im1, cax=cax)
            cb.set_label("Δ Balance hídrico (mm/3 meses)\nAzul = aumento | Rojo = reducción")
            plt.tight_layout(rect=[0, 0, 0.98, 1])
            fn = f"delta_trimestres_{scen.replace('_ecuador','')}.png"
            out_path = settings.fig_path(output_dir, settings.OUT_CAT_TRIMESTRES_CAMBIOS, fn)
            plt.savefig(out_path, dpi=180, bbox_inches="tight")
            plt.close()
            print(f"  Generated: {fn}")

if __name__ == "__main__":
    run()

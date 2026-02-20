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

VENTANAS={
    "Base_1981-2010":("1981","2010"),
    "Cercano_2021-2040":("2021","2040"),
    "Medio_2041-2070":("2041","2070"),
    "Tardío_2071-2100":("2071","2100"),
}

_cache_geo={}
def outline(path):
    if path in _cache_geo: return _cache_geo[path]
    if not os.path.exists(path): return None
    g=gpd.read_file(path)
    try:
        if g.crs is None or g.crs.to_epsg()!=4326: g=g.to_crs("EPSG:4326")
    except Exception: pass
    _cache_geo[path]=g
    return g

def pm(ax, lat, lon, fld, titulo, cmap, vmin=None, vmax=None):
    im=ax.pcolormesh(lon,lat,fld,shading="auto",cmap=cmap,vmin=vmin,vmax=vmax)
    ax.set_title(titulo); ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud"); ax.grid(True,alpha=.2)
    return im

def leer_mean(data_dir, dom, t0, t1, var):
    p = os.path.join(data_dir, dom, f"wb_{dom}.nc")
    if not os.path.exists(p):
        p = os.path.join(data_dir, dom, "wb.nc")
    if not os.path.exists(p):
        return None
    ds = xr.open_dataset(p).sel(time=slice(f"{t0}-01-01", f"{t1}-12-31"))
    if ds.sizes.get("time",0)==0: return None
    return (ds[var].mean("time")*365.0)

def run():
    print("\n" + "="*60)
    print("GENERATING DELIVERABLE MAPS COMPONENTS")
    print("="*60)

    for region_code, region_info in settings.REGIONS.items():
        output_dir = settings.get_region_output_dir(region_code)
        print(f"Processing region: {region_info['name']} ({output_dir})")
        shp = region_info.get("shapefile")
        geo = outline(shp)

        baseWB = leer_mean(output_dir, "historical_ecuador", *VENTANAS["Base_1981-2010"], "wb_mmday")
        baseP = leer_mean(output_dir, "historical_ecuador", *VENTANAS["Base_1981-2010"], "p_mmday")
        baseE = leer_mean(output_dir, "historical_ecuador", *VENTANAS["Base_1981-2010"], "pet_mmday")
        if baseWB is None:
            print("  ⚠️ Missing baseline data"); continue
        lat,lon=baseWB["lat"].values, baseWB["lon"].values


        pmin,pmax = np.nanpercentile(baseP.values,[2,98])
        emin,emax = np.nanpercentile(baseE.values,[2,98])
        wb_span = np.nanpercentile(baseWB.values,[2,98])
        wb_abs = max(abs(wb_span[0]),abs(wb_span[1])); wb_abs=np.ceil(max(wb_abs,100)/100)*100


        fig,axs=plt.subplots(1,3,figsize=(15,4),sharex=True,sharey=True)
        im0=pm(axs[0],lat,lon,baseP.values,"Precipitación (mm/año)","Blues",pmin,pmax)
        im1=pm(axs[1],lat,lon,baseE.values,"Evapotranspiración (mm/año)","Oranges",emin,emax)
        im2=pm(axs[2],lat,lon,baseWB.values,"Balance hídrico (mm/año)","RdBu",-wb_abs,wb_abs)
        if geo is not None:
             for ax in axs: geo.boundary.plot(ax=ax,edgecolor="k",linewidth=.9)
        for im,ax in zip([im0,im1,im2],axs):
            fig.colorbar(im,ax=ax,fraction=0.046,pad=0.04)
        plt.suptitle("Climatología 1981–2010")
        out_base = settings.fig_path(output_dir, settings.OUT_CAT_MAPAS_BASE, "climatologia_base_P_PET_WB.png")
        plt.savefig(out_base, dpi=180, bbox_inches="tight")
        plt.close()
        print(f"  Generated: {os.path.basename(out_base)}")

        period_suffix = {("2021", "2040"): "cercano_2021-2040", ("2041", "2070"): "medio_2041-2070", ("2071", "2100"): "tardio_2071-2100"}
        var_cat = {"wb_mmday": (settings.OUT_CAT_MAPAS_DELTA_WB, "delta_WB"), "p_mmday": (settings.OUT_CAT_MAPAS_DELTA_P, "delta_P"), "pet_mmday": (settings.OUT_CAT_MAPAS_DELTA_PET, "delta_PET")}
        for var, lab, cmap, vm in [
            ("wb_mmday", "Δ Balance hídrico (mm/año)", "RdBu", 800),
            ("p_mmday", "Δ Precipitación (mm/año)", "BrBG", None),
            ("pet_mmday", "Δ Evapotranspiración (mm/año)", "PuOr_r", None),
        ]:
            for key, (t0, t1) in VENTANAS.items():
                if key.startswith("Base"):
                    continue
                fig, axs = plt.subplots(1, 3, figsize=(15, 4), sharex=True, sharey=True)
                ims = []
                for j, scen in enumerate(["ssp126_ecuador", "ssp370_ecuador", "ssp585_ecuador"]):
                    fut = leer_mean(output_dir, scen, t0, t1, var)
                    if fut is None: axs[j].axis("off"); axs[j].set_title(f"{scen} sin datos"); ims.append(None); continue
                    base = baseWB if var=="wb_mmday" else (baseP if var=="p_mmday" else baseE)
                    delta=(fut - base).values
                    if vm is None:
                        lo,hi=np.nanpercentile(delta,[2,98]); vm_dyn=max(abs(lo),abs(hi),50); vm_dyn=np.ceil(vm_dyn/50)*50
                    else:
                        vm_dyn = vm
                    im=pm(axs[j],lat,lon,delta,scen.replace('_ecuador',''),cmap,-vm_dyn,vm_dyn)
                    if geo is not None:
                        geo.boundary.plot(ax=axs[j],edgecolor="k",linewidth=.9)
                    ims.append(im)
                for im, ax in zip(ims, axs):
                    if im is not None:
                        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
                plt.suptitle(f"{lab} | {t0}–{t1} respecto a 1981–2010")
                suf = period_suffix.get((t0, t1), f"{t0}-{t1}")
                cat, prefix = var_cat[var]
                fname = f"{prefix}_{suf}.png"
                out_path = settings.fig_path(output_dir, cat, fname)
                plt.savefig(out_path, dpi=180, bbox_inches="tight")
                plt.close()
                print(f"  Generated: {fname}")

if __name__ == "__main__":
    run()

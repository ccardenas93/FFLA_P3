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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from organized.config import settings

DOMINIOS = settings.DOMAINS
VENTANAS = {
    "Base_1981-2010":   ("1981","2010"),
    "Cercano_2021-2040":("2021","2040"),
    "Medio_2041-2070":  ("2041","2070"),
    "Tardío_2071-2100": ("2071","2100"),
}


MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

_GEO_CACHE={}
def cargar_outline(path):
    if path in _GEO_CACHE: return _GEO_CACHE[path]
    if not os.path.exists(path): return None
    g = gpd.read_file(path)
    try:
        if g.crs is None or g.crs.to_epsg()!=4326:
            g = g.to_crs("EPSG:4326")
    except Exception:
        pass
    _GEO_CACHE[path]=g
    return g

def clim_mensual_wb(data_dir, dominio, t0, t1):
    """Climatología mensual de WB (mm/mes). data_dir = output dir con wb_*.nc."""
    p = os.path.join(data_dir, dominio, f"wb_{dominio}.nc")
    if not os.path.exists(p):
        p = os.path.join(data_dir, dominio, "wb.nc")
    if not os.path.exists(p):
        return None

    ds = xr.open_dataset(p)
    if ("time" not in ds.dims) and ("time" not in ds.coords): return None
    ds = ds.sel(time=slice(f"{t0}-01-01", f"{t1}-12-31"))
    if ds.sizes.get("time",0) == 0: return None

    if "wb_mmday" not in ds: return None


    mon_sum = ds["wb_mmday"].resample(time="MS").sum("time")
    clim = mon_sum.groupby("time.month").mean("time")
    return clim

def limites_comunes(*arrs, default=(-300,300)):
    """Percentiles 2–98, simetrizado a múltiplos de 50."""
    vals=[]
    for a in arrs:
        if a is None: continue
        v=np.asarray(a).ravel()
        v=v[np.isfinite(v)]
        if v.size: vals.append(v)
    if not vals: return default
    v=np.concatenate(vals); lo,hi=np.percentile(v,2),np.percentile(v,98)
    span=max(abs(lo),abs(hi),100.0)
    span=np.ceil(span/50)*50
    return (-span, span)

def dibujar_shp(ax, shp_path):
    if not shp_path: return
    try:
        geo=cargar_outline(shp_path)
        if geo is not None:
            geo.boundary.plot(ax=ax, edgecolor="k", linewidth=0.9, facecolor="none", zorder=5)
    except Exception:
        pass

def panel_3x4(lat, lon, cubo, titulo, out_png, shp_path, vmin=None, vmax=None, cmap="RdBu"):

    fig, axes = plt.subplots(3,4, figsize=(16.5,8.0), sharex=True, sharey=True)
    axes = axes.ravel()
    last_im=None
    for m in range(1,13):
        ax=axes[m-1]
        if cubo is not None and ("month" in cubo.dims) and (m in cubo["month"].values):
            campo = cubo.sel(month=m).values
            last_im = ax.pcolormesh(lon, lat, campo, shading="auto", cmap=cmap, vmin=vmin, vmax=vmax)
            dibujar_shp(ax, shp_path)
        else:
            ax.text(0.5,0.5,"sin datos",ha="center",va="center",transform=ax.transAxes)
        ax.set_title(MESES[m-1], fontsize=10); ax.grid(True, alpha=.2)

    if last_im is not None:
        cax = fig.add_axes([0.985, 0.15, 0.02, 0.7])
        cb  = fig.colorbar(last_im, cax=cax); cb.set_label("Balance Hídrico (mm/mes)")
    fig.suptitle(titulo, fontsize=14)
    for ax in axes[-4:]: ax.set_xlabel("Longitud")
    for i in [0,4,8]: axes[i].set_ylabel("Latitud")
    plt.savefig(out_png, dpi=180, bbox_inches="tight")
    plt.close()

def _monthly_map_output(dom, etiqueta, is_delta):
    """Return (category, filename) for monthly WB maps."""
    if not is_delta and dom == "historical_ecuador":
        return settings.OUT_CAT_MAPAS_MENSUALES_HIST, "WB_mensual_historico_base.png"
    if not is_delta:
        suf = "cercano" if "Cercano" in etiqueta else ("medio" if "Medio" in etiqueta else "tardio")
        if "ssp126" in dom: return settings.OUT_CAT_MAPAS_MENSUALES_SSP126, f"WB_mensual_ssp126_{suf}.png"
        if "ssp370" in dom: return settings.OUT_CAT_MAPAS_MENSUALES_SSP370, f"WB_mensual_ssp370_{suf}.png"
        if "ssp585" in dom: return settings.OUT_CAT_MAPAS_MENSUALES_SSP585, f"WB_mensual_ssp585_{suf}.png"
    else:
        suf = "cercano" if "Cercano" in etiqueta else ("medio" if "Medio" in etiqueta else "tardio")
        if "ssp126" in dom: return settings.OUT_CAT_MAPAS_DELTA_SSP126, f"delta_WB_mensual_ssp126_{suf}.png"
        if "ssp370" in dom: return settings.OUT_CAT_MAPAS_DELTA_SSP370, f"delta_WB_mensual_ssp370_{suf}.png"
        if "ssp585" in dom: return settings.OUT_CAT_MAPAS_DELTA_SSP585, f"delta_WB_mensual_ssp585_{suf}.png"
    return settings.OUT_CAT_MAPAS_MENSUALES_HIST, "out.png"

def run():
    print("\n" + "="*60)
    print("GENERANDO MAPAS MENSUALES DE WB (ESPAÑOL)")
    print("="*60)

    for region_code, region_info in settings.REGIONS.items():
        output_dir = settings.get_region_output_dir(region_code)
        shp_path = region_info.get("shapefile")
        print(f"Procesando región: {region_info['name']} ({output_dir})")

        base = clim_mensual_wb(output_dir, "historical_ecuador", *VENTANAS["Base_1981-2010"])
        ref = base
        if ref is None:
            for d in DOMINIOS:
                for (t0, t1) in VENTANAS.values():
                    tmp = clim_mensual_wb(output_dir, d, t0, t1)
                    if tmp is not None:
                        ref = tmp
                        break
                if ref is not None:
                    break
        if ref is None:
            print("  ⚠️ Sin datos para mapas mensuales")
            continue
        lat, lon = ref["lat"].values, ref["lon"].values

        for dom in DOMINIOS:
            for etiqueta, (t0, t1) in VENTANAS.items():
                clim = clim_mensual_wb(output_dir, dom, t0, t1)
                if clim is None:
                    continue
                vmin, vmax = limites_comunes(clim)
                cat, fname = _monthly_map_output(dom, etiqueta, is_delta=False)
                out_png = settings.fig_path(output_dir, cat, fname)
                titulo = f"{dom.replace('_ecuador','')} | Balance Hídrico Mensual | {etiqueta.replace('_',' ')}"
                panel_3x4(lat, lon, clim, titulo, out_png, shp_path, vmin=vmin, vmax=vmax, cmap="RdBu")
                print(f"  Generado: {os.path.basename(out_png)}")

        if base is None:
            continue
        for dom in [d for d in DOMINIOS if "historical" not in d]:
            for etiqueta, (t0, t1) in VENTANAS.items():
                if etiqueta.startswith("Base"):
                    continue
                fut = clim_mensual_wb(output_dir, dom, t0, t1)
                if fut is None:
                    continue
                delta = fut - base
                vmin, vmax = limites_comunes(delta, default=(-300, 300))
                cat, fname = _monthly_map_output(dom, etiqueta, is_delta=True)
                out_png = settings.fig_path(output_dir, cat, fname)
                titulo = f"{dom.replace('_ecuador','')} | Δ Balance Hídrico Mensual vs Base | {etiqueta.replace('_',' ')}"
                panel_3x4(lat, lon, delta, titulo, out_png, shp_path, vmin=vmin, vmax=vmax, cmap="RdBu")
                print(f"  Generado: {os.path.basename(out_png)}")

if __name__ == "__main__":
    run()

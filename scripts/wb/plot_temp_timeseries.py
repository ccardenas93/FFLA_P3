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
PALETTE = settings.PALETTE
DOMAINS = settings.DOMAINS

# === Utilidades ===
def roll_nanmean(y, k=11, min_frac=0.6):
    """Media móvil robusta con NaNs; ventana impar k."""
    y = np.asarray(y, float)
    n = len(y); out = np.full(n, np.nan)
    if k <= 1 or n < 2: return y
    k = int(k) if int(k)%2==1 else int(k)+1
    half = k//2; min_pts = max(1, int(np.ceil(k*min_frac)))
    for i in range(n):
        a = max(0, i-half); b = min(n, i+half+1)
        w = y[a:b]; m = np.isfinite(w)
        if m.sum() >= min_pts: out[i] = w[m].mean()
    return out

def wlat(lat):
    """Pesos cos(lat) como DataArray (se normaliza al promediar)."""
    return xr.DataArray(np.cos(np.deg2rad(lat)), coords={'lat': lat}, dims=['lat'])

def wmean(da):
    """
    Promedio espacial ponderado por cos(lat) y media en lon.
    xarray.weighted normaliza por suma de pesos automáticamente.
    """
    return da.weighted(wlat(da['lat'])).mean(("lat", "lon"))

def apply_scale_offset(da):
    """Aplica CF scale_factor/add_offset si existen (por si vienen sin decodificar)."""
    sf = da.attrs.get("scale_factor", None)
    ao = da.attrs.get("add_offset",  None)
    if sf is not None or ao is not None:
        sf = 1.0 if sf is None else float(sf)
        ao = 0.0 if ao is None else float(ao)
        da = da.astype("float64") * sf + ao
    return da

def as_celsius(da):
    """
    Devuelve temperatura en °C (robusto a unidades corruptas).
    """
    da = apply_scale_offset(da)
    u = str(da.attrs.get("units", "")).lower()

    # Caso común por metadatos
    if ("k" in u) and ("c" not in u):
        return da - 273.15
    if "c" in u:
        return da

    # Heurística por rango
    finite = da.where(np.isfinite(da), drop=True)
    try:
        vmin = float(finite.min())
        vmax = float(finite.max())
    except Exception:
        # Último recurso: suponer K si falla todo
        return da - 273.15

    if (vmax > 100.0) or (vmin < -50.0):
        return da - 273.15
    return da  # ya parece °C

def run():
    print("\n" + "="*60)
    print("GENERANDO SERIES TEMPORALES DE TEMPERATURA (ESPAÑOL)")
    print("="*60)

    input_cat = settings.OUT_CAT_SERIES_TEMP
    file_map = {"tas": "temperatura_media_anual.png", "tasmax": "temperatura_maxima_anual.png", "tasmin": "temperatura_minima_anual.png"}

    for region_code, region_info in settings.REGIONS.items():
        input_dir = settings.get_region_input_dir(region_code)
        output_dir = settings.get_region_output_dir(region_code)
        print(f"Procesando región: {region_info['name']} ({output_dir})")

        for var, title in [("tas", "Temperatura Media (°C)"),
                           ("tasmax", "Temperatura Máxima (°C)"),
                           ("tasmin", "Temperatura Mínima (°C)")]:
            plt.figure(figsize=(10, 4))
            drew = False

            for dom in DOMAINS:
                p = os.path.join(input_dir, dom, f"{var}_{dom}.nc")
                if not os.path.exists(p):
                    p = os.path.join(input_dir, dom, f"{var}.nc")
                    if not os.path.exists(p):
                        continue

                ds = xr.open_dataset(p)
                if "time" not in ds:
                    continue

                var_in_file = var
                if var not in ds:
                    # Fallback variable names
                    if var == 'tas' and 'tmean' in ds: var_in_file = 'tmean'
                    elif var == 'tasmin' and 'tmin' in ds: var_in_file = 'tmin'
                    elif var == 'tasmax' and 'tmax' in ds: var_in_file = 'tmax'
                
                if var_in_file not in ds:
                    continue

                T = as_celsius(ds[var_in_file])

                # medias anuales (°C)
                ann = T.resample(time="YS").mean()  # (time, lat, lon)
                if ann.sizes.get("time", 0) == 0:
                    continue

                years = ann["time"].dt.year.values
                sel = (years >= PERIOD_START) & (years <= PERIOD_END)
                if sel.sum() == 0:
                    continue

                y = wmean(ann).values[sel]  # serie anual ponderada (°C)
                yrs = years[sel]

                # ventana de suavizado ~ proporcional a la longitud del período
                win = min(11, max(3, ((int(yrs[-1]) - int(yrs[0]) + 1) // 15) * 2 + 1))
                smooth = roll_nanmean(y, k=win)

                c = PALETTE.get(dom, "tab:blue")
                plt.plot(yrs, y, lw=.8, alpha=.5, color=c)
                
                dom_label = dom.replace("_ecuador","")
                if dom_label == "historical": dom_label = "Histórico"
                
                plt.plot(yrs, smooth, lw=2, color=c, label=dom_label)
                drew = True

            plt.title(f"{region_info['name']}: {title} Anual, {PERIOD_START}–{PERIOD_END}")
            plt.xlabel("Año")
            plt.ylabel(title)
            plt.grid(True, alpha=.3)
            if drew:
                plt.legend(ncol=4, fontsize=8)
            plt.tight_layout()
            output_file = settings.fig_path(output_dir, input_cat, file_map[var])
            plt.savefig(output_file, dpi=180)
            plt.close()
            print(f"  Generado: {os.path.basename(output_file)}")

if __name__ == "__main__":
    run()

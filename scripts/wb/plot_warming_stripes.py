#!/usr/bin/env python3
import sys
import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from organized.config import settings

DOMAINS = settings.DOMAINS
BASE = settings.BASE_PERIOD
DOMAINS_TO_PLOT = [d for d in settings.DOMAINS if "historical" not in d]

LABELS = {d: d.replace("_ecuador", "").upper() for d in settings.DOMAINS}

def wlat(lat): return xr.DataArray(np.cos(np.deg2rad(lat)), coords={'lat':lat}, dims=['lat'])
def wmean(da): return da.weighted(wlat(da['lat'])).mean(("lat","lon"))
def as_celsius(da):
    u=str(da.attrs.get("units","")).lower()
    if "c" in u: return da
    sample=float(da.isel(time=0)); return da-273.15 if sample>150 else da

def run():
    print("\n" + "="*60)
    print("GENERANDO WARMING STRIPES (ESPAÑOL)")
    print("="*60)

    for region_code, region_info in settings.REGIONS.items():
        input_dir = settings.get_region_input_dir(region_code)
        output_dir = settings.get_region_output_dir(region_code)
        print(f"Procesando región: {region_info['name']} ({output_dir})")

        hb = os.path.join(input_dir, "historical_ecuador", "tas_historical_ecuador.nc")
        if not os.path.exists(hb):
            hb = os.path.join(input_dir, "historical_ecuador", "tas.nc")
        if not os.path.exists(hb):
            print(f"  ⚠️ Datos históricos no encontrados para línea base")
            continue

        try:
            ds_hist = xr.open_dataset(hb)
            tas_var = 'tas' if 'tas' in ds_hist else 'tmean'
            T = ds_hist[tas_var]
            T = as_celsius(T)


            base_slice = T.sel(time=slice(f"{BASE[0]}-01-01", f"{BASE[1]}-12-31"))
            if base_slice.sizes['time'] == 0:
                 print(f"  ⚠️ No hay datos en período base {BASE} para {region_info['name']}")
                 continue

            base = wmean(base_slice.resample(time="YS").mean()).mean().item()
        except Exception as e:
            print(f"  ❌ Error calculando línea base: {e}")
            continue

        target_domains = DOMAINS_TO_PLOT
        nrows = len(target_domains)
        fig, axes = plt.subplots(nrows, 1, figsize=(12, 1.2*nrows), sharex=True)
        if nrows == 1: axes = [axes]

        for ax, dom in zip(axes, target_domains):
            p = os.path.join(input_dir, dom, f"tas_{dom}.nc")
            if not os.path.exists(p):
                p = os.path.join(input_dir, dom, "tas.nc")

            if not os.path.exists(p):
                ax.axis("off")
                continue

            try:
                ds = xr.open_dataset(p)
                tas_var = 'tas' if 'tas' in ds else 'tmean'
                T = ds[tas_var]
                T = as_celsius(T)

                ann = wmean(T.resample(time="YS").mean())
                years = ann["time"].dt.year.values
                anom = (ann.values - base)

                im = ax.imshow(anom[np.newaxis, :], aspect="auto",
                             extent=[years.min()-0.5, years.max()+0.5, 0, 1],
                             cmap="RdYlBu_r", vmin=-2.5, vmax=+5.0)
                ax.set_yticks([])
                ax.set_ylabel(LABELS.get(dom, dom), rotation=0, labelpad=30, va="center")
            except Exception as e:
                 print(f"  Error graficando {dom}: {e}")
                 ax.axis("off")

        axes[-1].set_xlabel("Año")

        cax = fig.add_axes([0.92, 0.15, 0.015, 0.7])
        fig.colorbar(im, cax=cax, label="Anomalía de Temperatura (°C)")

        plt.tight_layout(rect=[0, 0, 0.9, 1])
        output_file = settings.fig_path(output_dir, settings.OUT_CAT_SERIES_TEMP, "warming_stripes_anomalias.png")
        plt.savefig(output_file, dpi=180)
        plt.close()
        print(f"  Generado: {os.path.basename(output_file)}")

if __name__ == "__main__":
    run()

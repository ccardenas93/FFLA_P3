#!/usr/bin/env python3
import sys
import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from organized.config import settings


SCENS = [d for d in settings.DOMAINS if "historical" not in d]
BASE = settings.BASE_PERIOD
WINS = [("2021","2050"), ("2041","2070"), ("2071","2100")]
LABS = ["Cercano (2021-2050)", "Medio (2041-2070)", "Tardío (2071-2100)"]
PALETTE = settings.PALETTE

def wlat(lat): return xr.DataArray(np.cos(np.deg2rad(lat)), coords={'lat': lat}, dims=['lat'])
def wmean(da): return da.weighted(wlat(da['lat'])).mean(('lat','lon'))

def mean_annual(path, t0, t1):
    if not os.path.exists(path): return None
    try:
        ds = xr.open_dataset(path).sel(time=slice(f"{t0}-01-01", f"{t1}-12-31"))
        if ds.sizes.get("time",0) == 0: return None

        if "wb_mmday" not in ds: return None


        daily_mean = wmean(ds["wb_mmday"])
        y = daily_mean.resample(time="YS").sum("time")
        return float(y.mean("time"))
    except Exception as e:

        return None

def run():
    print("\n" + "="*60)
    print("GENERANDO GRÁFICOS DE BARRAS DELTA (ENTREGABLE - ESPAÑOL)")
    print("="*60)

    out_cat = settings.OUT_CAT_CAMBIOS_WB
    file_map = {"ssp126_ecuador": "delta_WB_ssp126.png", "ssp370_ecuador": "delta_WB_ssp370.png", "ssp585_ecuador": "delta_WB_ssp585.png"}

    for region_code, region_info in settings.REGIONS.items():
        output_dir = settings.get_region_output_dir(region_code)
        print(f"Procesando región: {region_info['name']} ({output_dir})")

        base_path = os.path.join(output_dir, "historical_ecuador", "wb_historical_ecuador.nc")
        if not os.path.exists(base_path):
            base_path = os.path.join(output_dir, "historical_ecuador", "wb.nc")
        base = mean_annual(base_path, *BASE)
        if base is None:
            print(f"  ⚠️ Sin datos de línea base para {region_info['name']}")
            continue

        for scen in SCENS:
            vals = []
            for (t0, t1) in WINS:
                scen_path = os.path.join(output_dir, scen, f"wb_{scen}.nc")
                if not os.path.exists(scen_path):
                    scen_path = os.path.join(output_dir, scen, "wb.nc")
                fut = mean_annual(scen_path, t0, t1)
                vals.append(np.nan if fut is None else fut - base)

            plt.figure(figsize=(6, 4))
            c = PALETTE.get(scen, 'tab:blue')
            plt.bar(LABS, vals, color=c, alpha=0.8)
            plt.axhline(0, color="k", lw=1)
            plt.ylabel("Δ Balance Hídrico (mm/año)")
            plt.title(f"Cambio en WB vs {BASE[0]}–{BASE[1]}\nEscenario: {scen.replace('_ecuador','').upper()}")
            plt.xticks(rotation=15)
            plt.tight_layout()

            output_file = settings.fig_path(output_dir, out_cat, file_map[scen])
            plt.savefig(output_file, dpi=180)
            plt.close()
            print(f"  Generado: {os.path.basename(output_file)}")

    print("✅ Barras delta generadas.")

if __name__ == "__main__":
    run()

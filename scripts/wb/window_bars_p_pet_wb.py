#!/usr/bin/env python3
import sys
import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from organized.config import settings

DOMS = settings.DOMAINS
# Windows for bars
WIN = [("1981","2010"),("2021","2050"),("2041","2070"),("2071","2100")]
LAB = ["1981–2010","2021–2050","2041–2070","2071–2100"]
PALETTE = settings.PALETTE

def wlat(lat): return xr.DataArray(np.cos(np.deg2rad(lat)), coords={'lat':lat}, dims=['lat'])
def wmean(da): return da.weighted(wlat(da['lat'])).mean(("lat","lon"))

def load_series(data_dir, dom):
    p = os.path.join(data_dir, dom, f"wb_{dom}.nc")
    if not os.path.exists(p):
        p = os.path.join(data_dir, dom, "wb.nc")
        if not os.path.exists(p):
            return None
    return xr.open_dataset(p)

def run():
    print("\n" + "="*60)
    print("GENERANDO GRÁFICOS DE BARRAS POR VENTANA (ESPAÑOL)")
    print("="*60)
    out_cat = settings.OUT_CAT_BARRAS_VENTANA
    file_map = {"p_mmday": "precipitacion_por_ventana.png", "pet_mmday": "evapotranspiracion_por_ventana.png", "wb_mmday": "balance_hidrico_por_ventana.png"}

    for region_code, region_info in settings.REGIONS.items():
        output_dir = settings.get_region_output_dir(region_code)
        print(f"Procesando región: {region_info['name']} ({output_dir})")

        ds_map = {d: load_series(output_dir, d) for d in DOMS}
        
        for var,label,fac in [("p_mmday","Precipitación (mm/año)", 365.0),
                              ("pet_mmday","Evapotranspiración Potencial (mm/año)", 365.0),
                              ("wb_mmday","Balance Hídrico (mm/año)", 365.0)]:
            
            vals = np.full((len(DOMS), len(WIN)), np.nan)
            
            for i, dom in enumerate(DOMS):
                ds = ds_map.get(dom)
                if ds is None: continue
                
                var_in_file = var
                if var not in ds:
                    if var == 'p_mmday' and 'pr' in ds: var_in_file = 'pr' 
                
                if var_in_file not in ds: continue

                for j, (t0, t1) in enumerate(WIN):
                    try:
                        daily_mean = wmean(ds[var_in_file])
                        window_mean = daily_mean.sel(time=slice(f"{t0}-01-01", f"{t1}-12-31")).mean("time")
                        vals[i,j] = float(window_mean.item()) * fac
                    except Exception:
                        pass

            # plot
            fig, ax = plt.subplots(figsize=(10, 4))
            width = 0.18
            xs = np.arange(len(WIN))
            
            for i, dom in enumerate(DOMS):
                if np.isnan(vals[i]).all(): continue
                c = PALETTE.get(dom, 'k')
                dom_label = dom.replace("_ecuador","")
                if dom_label == "historical": dom_label = "Histórico"
                ax.bar(xs + i*width - 1.5*width, vals[i], width=width, label=dom_label, color=c, alpha=0.8)
            
            ax.set_xticks(xs)
            ax.set_xticklabels(LAB, rotation=20)
            ax.set_ylabel(label)
            ax.set_title(f"{label} por Ventana Temporal")
            ax.grid(True, axis="y", alpha=.3)
            ax.legend(ncol=4, fontsize=8)
            
            output_file = settings.fig_path(output_dir, out_cat, file_map[var])
            plt.tight_layout()
            plt.savefig(output_file, dpi=180)
            plt.close()
            print(f"  Generado: {os.path.basename(output_file)}")

if __name__ == "__main__":
    run()

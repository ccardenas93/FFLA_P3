#!/usr/bin/env python3
# wb/plot_ai_cdd_timeseries.py
# Series temporales de Índice de Aridez (AI) y Días Secos Consecutivos (CDD)

import sys
import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from organized.config import settings

DOMS = settings.DOMAINS
BASE = settings.BASE_PERIOD
START_YEAR = 1980  # Año inicial para las gráficas
DRY_THRESH_MM = 1.0  # día seco si P < 1 mm/día

PALETTE = settings.PALETTE
LABELS = {d: d.replace("_ecuador", "").upper() for d in DOMS}

def wlat(lat):
    return xr.DataArray(np.cos(np.deg2rad(lat)), coords={'lat': lat}, dims=['lat'])

def wmean(da):
    return da.weighted(wlat(da['lat'])).mean(('lat', 'lon'))

def load_wb_series(data_dir, dom):
    """Carga series diarias promediadas (data_dir = output dir donde está wb_*.nc)."""
    p = os.path.join(data_dir, dom, f"wb_{dom}.nc")
    if not os.path.exists(p):
        p = os.path.join(data_dir, dom, "wb.nc")
        if not os.path.exists(p):
            return None

    ds = xr.open_dataset(p)
    if "time" not in ds:
        return None
    
    # Ensure variables exist
    if "p_mmday" not in ds:
         # Try fallback names from water_balance.py or raw inputs?
         # The file wb_{dom}.nc is created by water_balance.py with p_mmday, pet_mmday, wb_mmday
         return None

    # Promedio espacial primero
    P = wmean(ds["p_mmday"])
    PET = wmean(ds["pet_mmday"])
    WB = wmean(ds["wb_mmday"])
    return xr.Dataset({"P": P, "PET": PET, "WB": WB})

def compute_ai_annual(ds):
    """Calcula AI anual = P_anual / PET_anual."""
    P_ann = ds["P"].resample(time="YS").sum("time")    # mm/año
    PET_ann = ds["PET"].resample(time="YS").sum("time")  # mm/año
    AI = P_ann / PET_ann
    return AI.where(np.isfinite(AI))

def compute_cdd_annual(ds):
    """Calcula CDD (Consecutive Dry Days) anual - racha seca máxima por año."""
    P = ds["P"]
    t = P["time"].to_index()
    years = sorted(set(t.year))
    
    is_dry = (P.values < DRY_THRESH_MM).astype(int)
    
    # Optimization: calculate CDD using numpy
    # We can identify dry spells by finding sequences of 1s
    
    cdd_values = []
    cdd_years = []
    
    # Group by year
    # This can be slow if done year by year in python loop
    # But spatial average is 1D array, so it should be fast enough.
    
    # Pre-calculate year indices
    year_arr = t.year
    
    for y in years:
        mask = (year_arr == y)
        if not np.any(mask): continue
        
        dry_subset = is_dry[mask]
        
        # Find max run of 1s
        padded = np.concatenate(([0], dry_subset, [0]))
        changes = np.diff(padded)
        starts = np.where(changes == 1)[0]
        ends = np.where(changes == -1)[0]
        
        if len(starts) == 0:
            max_run = 0
        else:
            max_run = (ends - starts).max()
            
        cdd_values.append(max_run)
        cdd_years.append(y)
    
    # Crear DataArray con años como coordenada
    return xr.DataArray(
        cdd_values,
        coords={"year": cdd_years},
        dims=["year"]
    )

def rolling_mean(data, window=11):
    """Media móvil simple para suavizar series."""
    if len(data) < window:
        return data
    return np.convolve(data, np.ones(window)/window, mode='valid')

def run():
    print("\n" + "="*60)
    print("GENERATING AI AND CDD TIMESERIES")
    print("="*60)

    out_cat = settings.OUT_CAT_INDICADORES
    for region_code, region_info in settings.REGIONS.items():
        output_dir = settings.get_region_output_dir(region_code)
        print(f"Processing region: {region_info['name']} ({output_dir})")

        data_map = {}
        for dom in DOMS:
            ds = load_wb_series(output_dir, dom)
            if ds is not None:
                data_map[dom] = ds
        
        if not data_map:
            print(f"  ⚠ Sin datos para {region_info['name']}")
            continue
        
        # ========== PLOT 1: ÍNDICE DE ARIDEZ (AI) ==========
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
        
        for dom in DOMS:
            if dom not in data_map:
                continue
            ds = data_map[dom]
            AI = compute_ai_annual(ds)
            
            # Filtrar desde START_YEAR
            AI = AI.sel(time=AI["time"].dt.year >= START_YEAR)
            years = AI["time"].dt.year.values
            
            # Plot serie anual
            ax1.plot(years, AI.values, color=PALETTE.get(dom, 'k'), alpha=0.3, lw=0.8)
            
            # Media móvil de 11 años
            if len(AI) >= 11:
                ai_smooth = rolling_mean(AI.values, window=11)
                years_smooth = years[5:-5]  # centrar la ventana
                ax1.plot(years_smooth, ai_smooth, color=PALETTE.get(dom, 'k'), 
                        lw=2.5, label=LABELS.get(dom, dom))
            else:
                ax1.plot(years, AI.values, color=PALETTE.get(dom, 'k'), 
                        lw=2, label=LABELS.get(dom, dom))
        
        # Sombreado del período base
        ax1.axvspan(int(BASE[0]), int(BASE[1]), alpha=0.15, color='gray', 
                    label=f'Período base ({BASE[0]}–{BASE[1]})')
        ax1.axhline(1.0, color='red', linestyle='--', lw=1.5, alpha=0.7, 
                    label='AI = 1 (P = PET)')
        
        ax1.set_ylabel('Índice de Aridez (AI = P/PET)', fontsize=11)
        ax1.set_title(f'Índice de Aridez — {region_info["name"]}', fontsize=13, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='best', fontsize=9, ncol=2)
        
        # Segundo panel: Anomalías de AI respecto a la base
        # Calcular AI base
        if "historical_ecuador" in data_map:
            ds_base = data_map["historical_ecuador"]
            AI_base_full = compute_ai_annual(ds_base)
            AI_base_period = AI_base_full.sel(time=slice(f"{BASE[0]}-01-01", f"{BASE[1]}-12-31"))
            
            if AI_base_period.sizes['time'] > 0:
                AI_base_mean = float(AI_base_period.mean())
                
                for dom in DOMS:
                    if dom not in data_map:
                        continue
                    ds = data_map[dom]
                    AI = compute_ai_annual(ds)
                    
                    # Filtrar desde START_YEAR
                    AI = AI.sel(time=AI["time"].dt.year >= START_YEAR)
                    years = AI["time"].dt.year.values
                    AI_anom = AI.values - AI_base_mean
                    
                    # Media móvil
                    if len(AI) >= 11:
                        ai_anom_smooth = rolling_mean(AI_anom, window=11)
                        years_smooth = years[5:-5]
                        ax2.plot(years_smooth, ai_anom_smooth, color=PALETTE.get(dom, 'k'), 
                                lw=2.5, label=LABELS.get(dom, dom))
                    else:
                        ax2.plot(years, AI_anom, color=PALETTE.get(dom, 'k'), 
                                lw=2, label=LABELS.get(dom, dom))
                
                ax2.axhline(0, color='k', linestyle='-', lw=1, alpha=0.5)
                ax2.axvspan(int(BASE[0]), int(BASE[1]), alpha=0.15, color='gray')
                ax2.set_ylabel(f'Δ AI (respecto a {BASE[0]}–{BASE[1]})', fontsize=11)
                ax2.set_xlabel('Año', fontsize=11)
                ax2.grid(True, alpha=0.3)
                # ax2.legend(loc='best', fontsize=9, ncol=2)
            else:
                print("  ⚠️ Insufficient base period data for AI anomalies")
        
        plt.tight_layout()
        output_file = settings.fig_path(output_dir, out_cat, "indice_aridez_serie_temporal.png")
        plt.savefig(output_file, dpi=180, bbox_inches='tight')
        plt.close()
        print(f"  Generated: {os.path.basename(output_file)}")
        
        # ========== PLOT 2: DÍAS SECOS CONSECUTIVOS (CDD) ==========
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
        
        for dom in DOMS:
            if dom not in data_map:
                continue
            ds = data_map[dom]
            CDD = compute_cdd_annual(ds)
            
            # Filtrar desde START_YEAR
            CDD = CDD.sel(year=(CDD["year"] >= START_YEAR))
            years = CDD["year"].values
            
            # Plot serie anual
            ax1.plot(years, CDD.values, color=PALETTE.get(dom, 'k'), alpha=0.3, lw=0.8)
            
            # Media móvil de 11 años
            if len(CDD) >= 11:
                cdd_smooth = rolling_mean(CDD.values, window=11)
                years_smooth = years[5:-5]
                ax1.plot(years_smooth, cdd_smooth, color=PALETTE.get(dom, 'k'), 
                        lw=2.5, label=LABELS.get(dom, dom))
            else:
                ax1.plot(years, CDD.values, color=PALETTE.get(dom, 'k'), 
                        lw=2, label=LABELS.get(dom, dom))
        
        # Sombreado del período base
        ax1.axvspan(int(BASE[0]), int(BASE[1]), alpha=0.15, color='gray',
                    label=f'Período base ({BASE[0]}–{BASE[1]})')
        
        ax1.set_ylabel('Racha seca máxima (días)', fontsize=11)
        ax1.set_title(f'Días Secos Consecutivos (CDD) — {region_info["name"]}', fontsize=13, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='best', fontsize=9, ncol=2)
        
        # Segundo panel: Anomalías de CDD respecto a la base
        if "historical_ecuador" in data_map:
            ds_base = data_map["historical_ecuador"]
            CDD_base_full = compute_cdd_annual(ds_base)
            # Filtrar años del período base
            base_years = [y for y in CDD_base_full["year"].values 
                         if int(BASE[0]) <= y <= int(BASE[1])]
            CDD_base_period = CDD_base_full.sel(year=base_years)
            
            if CDD_base_period.sizes['year'] > 0:
                CDD_base_mean = float(CDD_base_period.mean())
                
                for dom in DOMS:
                    if dom not in data_map:
                        continue
                    ds = data_map[dom]
                    CDD = compute_cdd_annual(ds)
                    
                    # Filtrar desde START_YEAR
                    CDD = CDD.sel(year=(CDD["year"] >= START_YEAR))
                    years = CDD["year"].values
                    CDD_anom = CDD.values - CDD_base_mean
                    
                    # Media móvil
                    if len(CDD) >= 11:
                        cdd_anom_smooth = rolling_mean(CDD_anom, window=11)
                        years_smooth = years[5:-5]
                        ax2.plot(years_smooth, cdd_anom_smooth, color=PALETTE.get(dom, 'k'), 
                                lw=2.5, label=LABELS.get(dom, dom))
                    else:
                        ax2.plot(years, CDD_anom, color=PALETTE.get(dom, 'k'), 
                                lw=2, label=LABELS.get(dom, dom))
                
                ax2.axhline(0, color='k', linestyle='-', lw=1, alpha=0.5)
                ax2.axvspan(int(BASE[0]), int(BASE[1]), alpha=0.15, color='gray')
                ax2.set_ylabel(f'Δ CDD (días, respecto a {BASE[0]}–{BASE[1]})', fontsize=11)
                ax2.set_xlabel('Año', fontsize=11)
                ax2.grid(True, alpha=0.3)
                # ax2.legend(loc='best', fontsize=9, ncol=2)
            else:
                print("  ⚠️ Insufficient base period data for CDD anomalies")
        
        plt.tight_layout()
        output_file = settings.fig_path(output_dir, out_cat, "dias_secos_consecutivos_serie_temporal.png")
        plt.savefig(output_file, dpi=180, bbox_inches='tight')
        plt.close()
        print(f"  Generated: {os.path.basename(output_file)}")

if __name__ == "__main__":
    run()

#!/usr/bin/env python3
import os
import sys
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from organized.config import settings

DOMAINS_FUT = [d for d in settings.DOMAINS if 'historical' not in d]

BASE = settings.BASE_PERIOD
# We need 2071-2100 for the "future" plot
FUT = ("2071", "2100") 

def wlat(lat): return xr.DataArray(np.cos(np.deg2rad(lat)), coords={'lat': lat}, dims=['lat'])
def wmean(da): return da.weighted(wlat(da['lat'])).mean(('lat','lon'))

def clim_month(data_dir, domain, t0, t1):
    """data_dir = output dir where wb_*.nc lives."""
    p = os.path.join(data_dir, domain, f'wb_{domain}.nc')
    if not os.path.exists(p): return None
    try:
        ds = xr.open_dataset(p).sel(time=slice(f'{t0}-01-01', f'{t1}-12-31'))
        # Daily series spatially averaged (mm/day), then monthly sum (mm/month)
        mon = xr.Dataset({
            'P'  : wmean(ds['p_mmday']).resample(time='MS').sum(),
            'PET': wmean(ds['pet_mmday']).resample(time='MS').sum(),
            'WB' : wmean(ds['wb_mmday']).resample(time='MS').sum(),
        })
        # Monthly climatology
        clim = mon.groupby('time.month').mean('time')
        return {k:clim[k].values for k in ['P','PET','WB']}
    except Exception as e:
        print(f"Error processing {domain}: {e}")
        return None

def run():
    print("\n" + "="*60)
    print("GENERATING SEASONAL CYCLE PLOTS")
    print("="*60)
    
    palette = settings.PALETTE

    out_cat = settings.OUT_CAT_CLIMATOLOGIA_COMP
    file_map = {"P": "ciclo_anual_precipitacion.png", "PET": "ciclo_anual_evapotranspiracion.png", "WB": "ciclo_anual_balance_hidrico.png"}

    for region_code, region_info in settings.REGIONS.items():
        output_dir = settings.get_region_output_dir(region_code)
        print(f"Processing region: {region_info['name']} ({output_dir})")

        base = clim_month(output_dir, 'historical_ecuador', *BASE)
        futs = {d: clim_month(output_dir, d, *FUT) for d in DOMAINS_FUT}

        for var, label in [('P', 'Precipitación (mm/mes)'),
                           ('PET', 'Evapotranspiración potencial (mm/mes)'),
                           ('WB', 'Balance hídrico (mm/mes)')]:
            fig, ax = plt.subplots(1, 2, figsize=(12, 4), sharey=False)
            m = np.arange(1, 13)
            if base is not None:
                ax[0].plot(m, base[var], 'k', lw=2, label=f'{BASE[0]}–{BASE[1]}')
            for d in DOMAINS_FUT:
                if futs.get(d) is None:
                    continue
                ax[0].plot(m, futs[d][var], color=palette[d], lw=2, label=d.replace('_ecuador', f' {FUT[0]}–{FUT[1]}'))
            ax[0].set_title(label + ' mensual')
            ax[0].set_xlabel('Mes')
            ax[0].grid(True, alpha=0.3)
            ax[0].legend(fontsize=8)
            for d in DOMAINS_FUT:
                if futs.get(d) is None or base is None:
                    continue
                ax[1].plot(m, np.array(futs[d][var]) - np.array(base[var]), color=palette[d], lw=2, label=d.replace('_ecuador', ' Δ'))
            ax[1].axhline(0, color='k', lw=1)
            ax[1].set_title(f'Δ ({FUT[0]}–{FUT[1]} respecto a {BASE[0]}–{BASE[1]})')
            ax[1].set_xlabel('Mes')
            ax[1].grid(True, alpha=0.3)
            ax[1].legend(fontsize=8)
            plt.tight_layout()
            out_file = settings.fig_path(output_dir, out_cat, file_map[var])
            plt.savefig(out_file, dpi=180)
            plt.close()
            print(f"  Generated: {os.path.basename(out_file)}")

if __name__ == "__main__":
    run()

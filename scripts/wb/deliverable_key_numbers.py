import os
import pandas as pd
import numpy as np
import xarray as xr
import json
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from organized.config import settings

np.seterr(all="ignore")

HIST = "historical_ecuador"
SCENS = ["ssp126_ecuador", "ssp370_ecuador", "ssp585_ecuador"]
BASE = settings.BASE_PERIOD
WINS = [
    ("2021", "2050"),
    ("2041", "2070"),
    ("2071", "2100"),
]
WIN_LABEL = {
    ("2021", "2050"): "Cercano (2021–2050)",
    ("2041", "2070"): "Medio (2041–2070)",
    ("2071", "2100"): "Tardío (2071–2100)",
}
DRY_THRESH_MM = 1.0  # dry day if P < 1 mm/day

def area_mean(da):
    w = np.cos(np.deg2rad(da["lat"]))
    if "time" in da.dims:
        num = (da * w).sum("lat")
        den = w.sum("lat")
        return (num / den).mean("lon")
    else:
        num = (da * w).sum("lat")
        den = w.sum("lat")
        return (num / den).mean("lon")

def load_wb_daily(data_dir, dom, t0, t1):
    """data_dir = output dir where wb_*.nc lives."""
    p = os.path.join(data_dir, dom, f"wb_{dom}.nc")
    if not os.path.exists(p):
        return None
    ds = xr.open_dataset(p)
    if "time" not in ds: return None
    ds = ds.sel(time=slice(f"{t0}-01-01", f"{t1}-12-31"))
    if ds.sizes.get("time", 0) == 0: return None
    P = area_mean(ds["p_mmday"])
    PET = area_mean(ds["pet_mmday"])
    WB = area_mean(ds["wb_mmday"])
    return xr.Dataset({"P": P, "PET": PET, "WB": WB})

def load_tas_daily(input_dir, dom, t0, t1):
    """input_dir = inputs region path (read-only)."""
    p = os.path.join(input_dir, dom, f"tas_{dom}.nc")
    if not os.path.exists(p):
        return None
    ds = xr.open_dataset(p)
    if "time" not in ds: return None
    ds = ds.sel(time=slice(f"{t0}-01-01", f"{t1}-12-31"))
    if ds.sizes.get("time", 0) == 0: return None

    tas = ds["tas" if "tas" in ds else "tmean"]
    u = str(tas.attrs.get("units", "")).lower()

    if ("k" in u) and ("c" not in u):
        tasC = tas - 273.15
    elif "c" in u:
        tasC = tas
    else:
        try:
            sample = float(tas.where(np.isfinite(tas), drop=True)
                           .isel(time=0, lat=tas.sizes["lat"] // 2, lon=tas.sizes["lon"] // 2))
        except Exception:
            sample = np.nan

        if np.isfinite(sample) and sample > 200:
            tasC = tas - 273.15
        else:
            vmin = float(tas.min())
            vmax = float(tas.max())
            tasC = tas - 273.15 if (vmax > 100 or vmin < -100) else tas

    tasC = area_mean(tasC)
    return tasC

def ann_stats(series_mmday):
    y = series_mmday.resample(time="YS").sum("time")
    return float(y.mean()), float(y.std())

def ann_mean(series_mmday):
    y = series_mmday.resample(time="YS").sum("time")
    return float(y.mean())

def ai_from_series(P_mmday, PET_mmday):
    Pann = P_mmday.resample(time="YS").sum("time")
    PETann = PET_mmday.resample(time="YS").sum("time")
    AI = (Pann / PETann).where(np.isfinite(Pann / PETann))
    return float(AI.mean())

def dry_day_metrics(P_mmday):
    is_dry = (P_mmday < DRY_THRESH_MM).astype(int)
    dry_days_year = is_dry.resample(time="YS").sum("time")
    mean_dry_days = float(dry_days_year.mean())

    t = P_mmday["time"].to_index()
    years = sorted(set(t.year))
    cdd_list = []
    arr = (P_mmday.values < DRY_THRESH_MM).astype(int)

    year_idx = {}
    for i, tt in enumerate(t):
        year_idx.setdefault(tt.year, []).append(i)

    for y in years:
        idx = year_idx[y]
        if not idx: continue
        run = 0; best = 0
        for k in idx:
            if arr[k] == 1:
                run += 1
                best = max(best, run)
            else:
                run = 0
        cdd_list.append(best)

    mean_cdd = float(np.mean(cdd_list)) if cdd_list else np.nan
    return mean_dry_days, mean_cdd

def seasonal_windows_from_base(data_dir):
    ds = load_wb_daily(data_dir, HIST, *BASE)
    if ds is None: return None
    P = ds["P"]
    mon = P.resample(time="MS").sum("time")
    clim = mon.groupby("time.month").mean("time").to_pandas()
    vals = clim.values
    ext = np.r_[vals, vals[:2]]
    sums = np.convolve(ext, np.ones(3, dtype=int), "valid")[:12]
    wet_start = int(np.argmax(sums)) + 1
    dry_start = int(np.argmin(sums)) + 1

    def tri(start):
        return [(start - 1) % 12 + 1, (start) % 12 + 1, (start + 1) % 12 + 1]

    return {"wet": tri(wet_start), "dry": tri(dry_start)}

def label_trim(months):
    N2M = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}
    return "-".join(N2M[m] for m in months)

def write_line(f, text=""):
    f.write(text + "\n")

def run():
    print("\n" + "="*60)
    print("GENERATING MASTER KEY NUMBERS (JSON & TXT)")
    print("="*60)

    for region_code, region_info in settings.REGIONS.items():
        input_dir = settings.get_region_input_dir(region_code)
        output_dir = settings.get_region_output_dir(region_code)
        out_dir = os.path.join(output_dir, settings.OUT_CAT_RESUMEN)
        os.makedirs(out_dir, exist_ok=True)
        out_txt = os.path.join(out_dir, "key_numbers.txt")
        out_json = os.path.join(out_dir, "key_numbers.json")

        region_name = region_info["name"]
        print(f"Processing region: {region_name} ({output_dir})")

        tri = seasonal_windows_from_base(output_dir)
        
        # Data structure for JSON
        data_export = {
            "region": region_name,
            "base_period": f"{BASE[0]}-{BASE[1]}",
            "baseline": {},
            "projections": {}
        }

        base_ds = load_wb_daily(output_dir, HIST, *BASE)
        if base_ds is None:
            print("  ⚠️ No historical data found.")
            continue

        # --- BASELINE CALCS ---
        Pm, Psd = ann_stats(base_ds["P"])
        Em, Esd = ann_stats(base_ds["PET"])
        WBm, Wbsd = ann_stats(base_ds["WB"])
        AI_base = ai_from_series(base_ds["P"], base_ds["PET"])
        dry_days_base, cdd_base = dry_day_metrics(base_ds["P"])
        tas_base = load_tas_daily(input_dir, HIST, *BASE)
        Tm_base = float(tas_base.resample(time="YS").mean("time").mean()) if tas_base is not None else np.nan
        
        data_export["baseline"] = {
            "P_annual": {"mean": round(Pm), "std": round(Psd)},
            "PET_annual": {"mean": round(Em), "std": round(Esd)},
            "WB_annual": {"mean": round(WBm), "std": round(Wbsd)},
            "AI": round(AI_base, 2),
            "Dry_Days": round(dry_days_base),
            "CDD": round(cdd_base),
            "Temp": round(Tm_base, 1) if not np.isnan(Tm_base) else None
        }

        # Write TXT
        with open(out_txt, "w", encoding="utf-8") as f:
            write_line(f, f"# NÚMEROS CLAVE DE CAMBIO CLIMÁTICO — {region_name}")
            write_line(f, f"Período base: {BASE[0]}–{BASE[1]}")
            write_line(f, "")
            write_line(f, "## Oferta hídrica y balance — Línea base (promedio ± DE)")
            write_line(f, f"• Precipitación anual: {Pm:,.0f} ± {Psd:,.0f} mm/año")
            write_line(f, f"• Evapotranspiración potencial anual: {Em:,.0f} ± {Esd:,.0f} mm/año")
            write_line(f, f"• Balance hídrico anual (P - PET): {WBm:,.0f} ± {Wbsd:,.0f} mm/año")
            write_line(f, f"• Índice de aridez (AI = P/PET): {AI_base:,.2f}")
            write_line(f, f"• Días secos por año (P<{DRY_THRESH_MM} mm/día): {dry_days_base:,.0f} días/año")
            write_line(f, f"• Racha seca máxima media (CDD): {cdd_base:,.0f} días")
            if not np.isnan(Tm_base):
                write_line(f, f"• Temperatura media anual: {Tm_base:,.1f} °C")
            write_line(f, "")

            if tri:
                wet, dry = tri["wet"], tri["dry"]
                wet_lbl, dry_lbl = label_trim(wet), label_trim(dry)
                data_export["baseline"]["seasonality"] = {
                    "wet_quarter": wet_lbl,
                    "dry_quarter": dry_lbl
                }
                
                def tri_sum(da):
                    mon = da.resample(time="MS").sum("time")
                    g = mon.groupby("time.month")
                    return float((g.mean("time").sel(month=list(wet)).sum())), \
                           float((g.mean("time").sel(month=list(dry)).sum()))

                P_wet, P_dry = tri_sum(base_ds["P"])
                PET_wet, PET_dry = tri_sum(base_ds["PET"])
                WB_wet, WB_dry = tri_sum(base_ds["WB"])
                
                write_line(f, "## Estacionalidad — Línea base (trimestres)")
                write_line(f, f"• Trimestre más húmedo (base): {wet_lbl} | P={P_wet:,.0f} mm, PET={PET_wet:,.0f} mm, WB={WB_wet:,.0f} mm")
                write_line(f, f"• Trimestre más seco   (base): {dry_lbl} | P={P_dry:,.0f} mm, PET={PET_dry:,.0f} mm, WB={WB_dry:,.0f} mm")
                write_line(f, "")
            
            write_line(f, "## Cambios proyectados vs 1981–2010")
            
            # --- PROJECTIONS ---
            for scen in SCENS:
                scen_key = scen.replace('_ecuador', '')
                data_export["projections"][scen_key] = {}
                
                write_line(f, f"### {scen_key.upper()}")
                
                for (t0, t1) in WINS:
                    win_key = f"{t0}-{t1}"
                    dsf = load_wb_daily(output_dir, scen, t0, t1)
                    if dsf is None:
                        write_line(f, f"• {WIN_LABEL[(t0, t1)]}: sin datos")
                        continue

                    Pm_f = ann_mean(dsf["P"])
                    Em_f = ann_mean(dsf["PET"])
                    WBm_f = ann_mean(dsf["WB"])
                    
                    dP = Pm_f - Pm
                    dE = Em_f - Em
                    dWB = WBm_f - WBm
                    
                    rP = (dP / Pm * 100.0) if Pm != 0 else np.nan
                    rE = (dE / Em * 100.0) if Em != 0 else np.nan
                    rWB = (dWB / WBm * 100.0) if WBm != 0 else np.nan
                    
                    AI_f = ai_from_series(dsf["P"], dsf["PET"])
                    dAI = AI_f - AI_base

                    dry_days_f, cdd_f = dry_day_metrics(dsf["P"])
                    ddelta = dry_days_f - dry_days_base
                    cddelta = cdd_f - cdd_base

                    Tm_f = np.nan
                    tas_f = load_tas_daily(input_dir, scen, t0, t1)
                    if tas_f is not None:
                        Tm_f = float(tas_f.resample(time="YS").mean("time").mean())
                    dT = (Tm_f - Tm_base) if (not np.isnan(Tm_f) and not np.isnan(Tm_base)) else np.nan

                    # Save to JSON
                    data_export["projections"][scen_key][win_key] = {
                        "delta_P_mm": round(dP),
                        "delta_P_pct": round(rP, 1),
                        "delta_PET_mm": round(dE),
                        "delta_PET_pct": round(rE, 1),
                        "delta_WB_mm": round(dWB),
                        "delta_WB_pct": round(rWB, 1),
                        "delta_AI": round(dAI, 2),
                        "delta_DryDays": round(ddelta),
                        "delta_CDD": round(cddelta),
                        "delta_Temp": round(dT, 1) if not np.isnan(dT) else None
                    }

                    write_line(f, f"• {WIN_LABEL[(t0, t1)]}:")
                    write_line(f, f"   – ΔP = {dP:,.0f} mm/año ({rP:+.1f}%) | ΔPET = {dE:,.0f} mm/año ({rE:+.1f}%) | ΔWB = {dWB:,.0f} mm/año ({rWB:+.1f}%)")
                    write_line(f, f"   – ΔAI (P/PET) = {dAI:+.2f}")
                    write_line(f, f"   – Δ días secos/año = {ddelta:+.0f} | Δ CDD = {cddelta:+.0f} días")
                    if not np.isnan(dT):
                        write_line(f, f"   – ΔT media anual = {dT:+.1f} °C")
                
                write_line(f, "")
        
        # Dump JSON
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(data_export, f, indent=2, ensure_ascii=False)
            
        print(f"  ✔ Summary written to: {out_txt}")
        print(f"  ✔ JSON data written to: {out_json}")

if __name__ == "__main__":
    run()

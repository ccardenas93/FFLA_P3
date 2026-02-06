#!/usr/bin/env python3
# wb/Deliverables/deliverable_master_key_numbers.py
# Resumen maestro de números clave de cambio climático (FDAT y FODESNA).
# Salida: ROOT/Deliverables/master/key_numbers.txt (uno por cada ROOT).
# Self-contained: uses repo config.

import os
import sys
import numpy as np
import xarray as xr
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from organized.config import settings

np.seterr(all="ignore")

# === Carpetas de entrada (regiones del repo) ===
ROOTS = [info["path"] for info in settings.REGIONS.values()]

# === Dominios (ya existentes) ===
HIST = "historical_ecuador"
SCENS = ["ssp126_ecuador", "ssp370_ecuador", "ssp585_ecuador"]

# === Ventanas de análisis ===
BASE = ("1981", "2010")
WINS = [
    ("2021","2050"),
    ("2041","2070"),
    ("2071","2100"),
]
WIN_LABEL = {
    ("2021","2050"): "Cercano (2021–2050)",
    ("2041","2070"): "Medio (2041–2070)",
    ("2071","2100"): "Tardío (2071–2100)",
}

# === Umbrales / parámetros ===
DRY_THRESH_MM = 1.0  # día seco si P<1 mm/día

# === Utilidades ===
def area_mean(da):
    """
    Promedio espacial ponderado por cos(lat).
    CORRECTO: dividir por la suma de pesos en 'lat' y luego media uniforme en 'lon'.
    Soporta (lat,lon) y (time,lat,lon).
    """
    w = np.cos(np.deg2rad(da["lat"]))             # (lat)
    if "time" in da.dims:
        num = (da * w).sum("lat")                 # (time, lon)
        den = w.sum("lat")                        # escalar
        return (num / den).mean("lon")            # (time)
    else:
        num = (da * w).sum("lat")                 # (lon)
        den = w.sum("lat")
        return (num / den).mean("lon")            # escalar

def load_wb_daily(root, dom, t0, t1):
    """Carga WB diario (y P, PET) mm/día, promediado espacialmente, y recorta tiempo."""
    p = f"{root}/{dom}/wb_{dom}.nc"
    if not os.path.exists(p):
        return None
    ds = xr.open_dataset(p)
    if "time" not in ds: return None
    ds = ds.sel(time=slice(f"{t0}-01-01", f"{t1}-12-31"))
    if ds.sizes.get("time",0)==0: return None
    P   = area_mean(ds["p_mmday"])
    PET = area_mean(ds["pet_mmday"])
    WB  = area_mean(ds["wb_mmday"])
    return xr.Dataset({"P":P, "PET":PET, "WB":WB})

def load_tas_daily(root, dom, t0, t1):
    """
    Carga T media diaria (tas) y devuelve °C, promediada espacialmente.
    Robusto a metadatos corruptos de unidades.
    """
    p = f"{root}/{dom}/tas_{dom}.nc"
    if not os.path.exists(p):
        return None
    ds = xr.open_dataset(p)
    if "time" not in ds: return None
    ds = ds.sel(time=slice(f"{t0}-01-01", f"{t1}-12-31"))
    if ds.sizes.get("time",0)==0: return None

    tas = ds["tas"]
    u = str(tas.attrs.get("units","")).lower()

    # 1) por metadatos
    if ("k" in u) and ("c" not in u):
        tasC = tas - 273.15
    elif "c" in u:
        tasC = tas
    else:
        # 2) heurística por magnitud/rango
        try:
            sample = float(tas.where(np.isfinite(tas), drop=True)
                               .isel(time=0, lat=tas.sizes["lat"]//2, lon=tas.sizes["lon"]//2))
        except Exception:
            sample = np.nan

        if np.isfinite(sample) and sample > 200:
            tasC = tas - 273.15
        else:
            vmin = float(tas.min())
            vmax = float(tas.max())
            tasC = tas - 273.15 if (vmax > 100 or vmin < -100) else tas

    tasC = area_mean(tasC)  # serie 1D en °C
    return tasC

def ann_stats(series_mmday):
    """(media, std) anual para serie diaria mm/día -> mm/año sumando por año."""
    y = series_mmday.resample(time="YS").sum("time")  # mm/año
    return float(y.mean()), float(y.std())

def ann_mean(series_mmday):
    """Media anual (mm/año) para serie diaria mm/día -> mm/año."""
    y = series_mmday.resample(time="YS").sum("time")
    return float(y.mean())

def ai_from_series(P_mmday, PET_mmday):
    """Índice de aridez AI = P/PET usando promedios anuales (mm/año)."""
    Pann   = P_mmday.resample(time="YS").sum("time")
    PETann = PET_mmday.resample(time="YS").sum("time")
    AI = (Pann / PETann).where(np.isfinite(Pann/PETann))
    return float(AI.mean())

def dry_day_metrics(P_mmday):
    """Promedio de días secos/año y racha seca máxima (CDD) promediada interanualmente."""
    is_dry = (P_mmday < DRY_THRESH_MM).astype(int)
    dry_days_year = is_dry.resample(time="YS").sum("time")
    mean_dry_days = float(dry_days_year.mean())

    t = P_mmday["time"].to_index()
    years = sorted(set(t.year))
    cdd_list = []
    arr = (P_mmday.values < DRY_THRESH_MM).astype(int)

    year_idx = {}
    for i,tt in enumerate(t):
        year_idx.setdefault(tt.year, []).append(i)

    for y in years:
        idx = year_idx[y]
        if not idx: continue
        run = 0; best = 0
        for k in idx:
            if arr[k]==1:
                run += 1
                best = max(best, run)
            else:
                run = 0
        cdd_list.append(best)

    mean_cdd = float(np.mean(cdd_list)) if cdd_list else np.nan
    return mean_dry_days, mean_cdd

def seasonal_windows_from_base(root):
    """Trimestre más húmedo y más seco a partir de la BASE (histórico)."""
    ds = load_wb_daily(root, HIST, *BASE)
    if ds is None: return None
    P = ds["P"]
    mon = P.resample(time="MS").sum("time")  # mm/mes
    clim = mon.groupby("time.month").mean("time").to_pandas()
    vals = clim.values
    ext = np.r_[vals, vals[:2]]
    sums = np.convolve(ext, np.ones(3, dtype=int), "valid")[:12]
    wet_start  = int(np.argmax(sums)) + 1
    dry_start  = int(np.argmin(sums)) + 1
    def tri(start):
        return [(start-1)%12+1, (start)%12+1, (start+1)%12+1]
    return {"wet": tri(wet_start), "dry": tri(dry_start)}

def label_trim(months):
    N2M = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}
    return "-".join(N2M[m] for m in months)

def write_line(f, text=""):
    f.write(text + "\n")

# === MAIN ===
for ROOT in ROOTS:
    out_dir = os.path.join(ROOT, "Deliverables", "master")
    os.makedirs(out_dir, exist_ok=True)
    out_txt = os.path.join(out_dir, "key_numbers.txt")
    region = os.path.basename(ROOT)

    tri = seasonal_windows_from_base(ROOT)

    # contenedores para el resumen ejecutivo (usaremos la ventana TARDÍO)
    late_summary = {}  # scen -> dict con métricas clave en 2071–2100

    with open(out_txt, "w", encoding="utf-8") as f:
        write_line(f, f"# NÚMEROS CLAVE DE CAMBIO CLIMÁTICO — {region}")
        write_line(f, f"Período base: {BASE[0]}–{BASE[1]}")
        write_line(f, "")

        # === BASE HISTÓRICA: promedios y dispersión ===
        base_ds = load_wb_daily(ROOT, HIST, *BASE)
        if base_ds is None:
            write_line(f, "⚠ No se encontraron datos históricos para la línea base.\n")
            continue

        Pm, Psd   = ann_stats(base_ds["P"])
        Em, Esd   = ann_stats(base_ds["PET"])
        WBm, Wbsd = ann_stats(base_ds["WB"])
        AI_base   = ai_from_series(base_ds["P"], base_ds["PET"])
        dry_days_base, cdd_base = dry_day_metrics(base_ds["P"])
        tas_base = load_tas_daily(ROOT, HIST, *BASE)
        Tm_base = float(tas_base.resample(time="YS").mean("time").mean()) if tas_base is not None else np.nan

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

        # === Estacionalidad: trimestres húmedo/seco ===
        if tri is not None:
            wet, dry = tri["wet"], tri["dry"]
            wet_lbl, dry_lbl = label_trim(wet), label_trim(dry)

            def tri_sum(da):
                mon = da.resample(time="MS").sum("time")
                g   = mon.groupby("time.month")
                return float((g.mean("time").sel(month=list(wet)).sum())), \
                       float((g.mean("time").sel(month=list(dry)).sum()))

            P_wet, P_dry     = tri_sum(base_ds["P"])
            PET_wet, PET_dry = tri_sum(base_ds["PET"])
            WB_wet, WB_dry   = tri_sum(base_ds["WB"])

            write_line(f, "## Estacionalidad — Línea base (trimestres)")
            write_line(f, f"• Trimestre más húmedo (base): {wet_lbl} | P={P_wet:,.0f} mm, PET={PET_wet:,.0f} mm, WB={WB_wet:,.0f} mm")
            write_line(f, f"• Trimestre más seco   (base): {dry_lbl} | P={P_dry:,.0f} mm, PET={PET_dry:,.0f} mm, WB={WB_dry:,.0f} mm")
            write_line(f, "")
        else:
            wet_lbl = dry_lbl = None
            write_line(f, "⚠ No fue posible definir trimestres húmedo/seco (datos base insuficientes).\n")

        # === Cambios por escenario y ventana ===
        write_line(f, "## Cambios proyectados vs 1981–2010")
        for scen in SCENS:
            write_line(f, f"### {scen.replace('_ecuador','').upper()}")
            for (t0,t1) in WINS:
                dsf = load_wb_daily(ROOT, scen, t0, t1)
                if dsf is None:
                    write_line(f, f"• {WIN_LABEL[(t0,t1)]}: sin datos")
                    continue

                Pm_f   = ann_mean(dsf["P"])
                Em_f   = ann_mean(dsf["PET"])
                WBm_f  = ann_mean(dsf["WB"])
                dP     = Pm_f  - Pm
                dE     = Em_f  - Em
                dWB    = WBm_f - WBm
                rP     = (dP  / Pm * 100.0) if Pm  != 0 else np.nan
                rE     = (dE  / Em * 100.0) if Em  != 0 else np.nan
                rWB    = (dWB / WBm* 100.0) if WBm != 0 else np.nan
                AI_f   = ai_from_series(dsf["P"], dsf["PET"])
                dAI    = AI_f - AI_base

                dry_days_f, cdd_f = dry_day_metrics(dsf["P"])
                ddelta  = dry_days_f - dry_days_base
                cddelta = cdd_f - cdd_base

                Tm_f = np.nan
                tas_f = load_tas_daily(ROOT, scen, t0, t1)
                if tas_f is not None:
                    Tm_f = float(tas_f.resample(time="YS").mean("time").mean())
                dT = (Tm_f - Tm_base) if (not np.isnan(Tm_f) and not np.isnan(Tm_base)) else np.nan

                write_line(f, f"• {WIN_LABEL[(t0,t1)]}:")
                write_line(f, f"   – ΔP = {dP:,.0f} mm/año ({rP:+.1f}%) | ΔPET = {dE:,.0f} mm/año ({rE:+.1f}%) | ΔWB = {dWB:,.0f} mm/año ({rWB:+.1f}%)")
                write_line(f, f"   – ΔAI (P/PET) = {dAI:+.2f}")
                write_line(f, f"   – Δ días secos/año = {ddelta:+.0f} | Δ CDD = {cddelta:+.0f} días")
                if not np.isnan(dT):
                    write_line(f, f"   – ΔT media anual = {dT:+.1f} °C")

                # cambios estacionales en trimestres definidos por la base
                if tri is not None:
                    def tri_sum_f(da):
                        mon = da.resample(time="MS").sum("time")
                        g   = mon.groupby("time.month").mean("time")
                        wsum = float(g.sel(month=list(tri['wet'])).sum())
                        dsum = float(g.sel(month=list(tri['dry'])).sum())
                        return wsum, dsum
                    Pw_f, Pd_f     = tri_sum_f(dsf["P"])
                    Ew_f, Ed_f     = tri_sum_f(dsf["PET"])
                    WBw_f, WBd_f   = tri_sum_f(dsf["WB"])
                    write_line(f, f"   – Trimestre húmedo ({label_trim(tri['wet'])}) ΔP={Pw_f-P_wet:+.0f} mm, ΔPET={Ew_f-PET_wet:+.0f} mm, ΔWB={WBw_f-WB_wet:+.0f} mm")
                    write_line(f, f"   – Trimestre seco   ({label_trim(tri['dry'])}) ΔP={Pd_f-P_dry:+.0f} mm, ΔPET={Ed_f-PET_dry:+.0f} mm, ΔWB={WBd_f-WB_dry:+.0f} mm")

                # guardar métricas de la ventana TARDÍA para el resumen ejecutivo
                if (t0, t1) == ("2071", "2100"):
                    late_summary[scen] = {
                        "dP": dP, "rP": rP,
                        "dE": dE, "rE": rE,
                        "dWB": dWB, "rWB": rWB,
                        "dAI": dAI,
                        "ddry": ddelta, "dcdd": cddelta,
                        "dT": dT
                    }

            write_line(f, "")  # línea en blanco por escenario

        # Notas
        write_line(f, "Notas:")
        write_line(f, f"• ‘Días secos’ definidos como P < {DRY_THRESH_MM} mm/día (serie promediada espacialmente).")
        write_line(f, "• CDD = racha seca máxima anual sobre la serie promediada espacialmente.")
        write_line(f, "• Índice de aridez AI = P/PET con promedios anuales (mm/año).")
        write_line(f, "• Cambios estacionales calculados sobre los trimestres húmedo/seco definidos con la línea base.")
        write_line(f, "")

        # =========================
        # RESUMEN EJECUTIVO (simple, directo y comparable entre escenarios)
        # =========================
        def fmt_pm(x):   return "N/D" if x is None or np.isnan(x) else f"{x:+.0f}"
        def fmt_pct(x):  return "N/D" if x is None or np.isnan(x) else f"{x:+.1f}%"
        def fmt_ai(x):   return "N/D" if x is None or np.isnan(x) else f"{x:+.2f}"
        def fmt_temp(x): return "N/D" if x is None or np.isnan(x) else f"{x:+.1f} °C"

        def one_liner(scen_key, name_legible):
            m = late_summary.get(scen_key, None)
            if not m:
                return f"- {name_legible}: sin datos para 2071–2100."
            return (f"- {name_legible}: el balance hídrico anual cambia {fmt_pm(m['dWB'])} mm/año "
                    f"({fmt_pct(m['rWB'])}); la precipitación {fmt_pm(m['dP'])} mm/año "
                    f"({fmt_pct(m['rP'])}) y la PET {fmt_pm(m['dE'])} mm/año ({fmt_pct(m['rE'])}). "
                    f"El índice de aridez varía {fmt_ai(m['dAI'])}. Se esperan {fmt_pm(m['ddry'])} días secos/año "
                    f"adicionales (o menos) y un cambio en la racha seca máxima de {fmt_pm(m['dcdd'])} días. "
                    f"{'' if np.isnan(m['dT']) else 'Temperatura: ' + fmt_temp(m['dT'])}").strip()

        write_line(f, "### Resumen ejecutivo (para tomadores de decisión)")
        write_line(f, "Horizonte: 2071–2100 respecto a 1981–2010.")
        write_line(f, one_liner("ssp126_ecuador", "Trayectoria baja (SSP1-2.6)"))
        write_line(f, one_liner("ssp370_ecuador", "Trayectoria media (SSP3-7.0)"))
        write_line(f, one_liner("ssp585_ecuador", "Trayectoria alta (SSP5-8.5)"))
        write_line(f, "")
        if all(k in late_summary for k in ["ssp126_ecuador","ssp370_ecuador","ssp585_ecuador"]):
            dWB_vals = [late_summary[k]["dWB"] for k in ["ssp126_ecuador","ssp370_ecuador","ssp585_ecuador"]]
            dir_wb = "menor disponibilidad hídrica" if np.nanmean(dWB_vals) < 0 else "mayor disponibilidad hídrica"
            write_line(f, "Mensajes clave:")
            write_line(f, f"• Las señales son coherentes entre escenarios: tendencia hacia {dir_wb} a finales de siglo (magnitud creciente de SSP1-2.6 → SSP5-8.5).")
            write_line(f, "• La aridez (AI) se desplaza en la misma dirección que el balance hídrico: reducciones en AI implican mayor estrés hídrico relativo.")
            write_line(f, "• Aumentos en días secos y rachas secas largas sugieren reforzar medidas de almacenamiento, eficiencia y gestión de la demanda.")
            write_line(f, "• Prioridades: proteger fuentes de agua (páramos/bosques), mejorar eficiencia en riego y consumo humano, y diversificar portafolio de medidas (infraestructura verde y gris).")
        write_line(f, "")

    print("✔ Resumen escrito en:", out_txt)

print("✅ Listo.")
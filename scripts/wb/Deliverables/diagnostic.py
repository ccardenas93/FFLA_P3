

import os
import sys
import numpy as np
import xarray as xr

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from organized.config import settings

ROOTS = [info["path"] for info in settings.REGIONS.values()]
DOMS = settings.DOMAINS
BASE = (str(settings.BASE_PERIOD[0]), str(settings.BASE_PERIOD[1]))
LATE = ("2071", "2100")

def area_mean(da):
    """Proper area-weighted mean with cos(lat) weighting."""
    w = np.cos(np.deg2rad(da["lat"]))
    num = (da * w).sum("lat")
    den = w.sum("lat")
    return (num / den).mean("lon")

def guess_units_and_convert(tas):
    """Devuelve (tas_en_C, etiqueta_conversion). Heurística robusta."""
    u = str(tas.attrs.get("units","")).lower()


    raw_min = float(tas.min().values)
    raw_max = float(tas.max().values)
    raw_med = float(tas.median().values)

    label = "desconocido"
    tasC = tas


    if ("k" in u) and ("c" not in u):
        tasC = tas - 273.15
        label = "K→°C por metadatos"

    elif "c" in u:
        tasC = tas
        label = "°C por metadatos"
    else:

        if raw_med > 200:

            tmp = tas - 273.15
            tmin = float(tmp.min()); tmax = float(tmp.max())
            if -60 <= tmin <= 60 and -60 <= tmax <= 60:
                tasC = tmp; label = "K→°C por heurística"
            else:

                tmp2 = tas/10.0
                tmin2 = float(tmp2.min()); tmax2 = float(tmp2.max())
                if -60 <= tmin2 <= 60 and -60 <= tmax2 <= 60:
                    tasC = tmp2; label = "°C*10→°C por heurística"
                else:
                    label = "¡Rango atípico! (revisar)"
        else:

            if raw_max > 100:
                tmp2 = tas/10.0
                tmin2 = float(tmp2.min()); tmax2 = float(tmp2.max())
                if -60 <= tmin2 <= 60 and -60 <= tmax2 <= 60:
                    tasC = tmp2; label = "°C*10→°C por heurística"
                else:
                    label = "°C (asumido) con rango raro"
            else:
                tasC = tas; label = "°C por heurística (rango plausible)"

    return tasC, label, (raw_min, raw_max, raw_med, u)

def diag_one(root, dom, t0, t1):
    p = f"{root}/{dom}/tas_{dom}.nc"
    if not os.path.exists(p):
        return f"[{root.split('/')[-1]}] {dom}: sin archivo {os.path.basename(p)}"

    try:
        ds  = xr.open_dataset(p)
    except Exception as e:
        return f"[{root.split('/')[-1]}] {dom}: error abriendo {p} -> {e}"

    if "tas" not in ds:
        return f"[{root.split('/')[-1]}] {dom}: variable 'tas' no está en {p}"

    tas = ds["tas"].sel(time=slice(f"{t0}-01-01", f"{t1}-12-31"))
    if tas.sizes.get("time",0)==0:
        return f"[{root.split('/')[-1]}] {dom}: ventana {t0}-{t1} vacía"


    sf = tas.encoding.get("scale_factor", None)
    ao = tas.encoding.get("add_offset", None)


    raw_min, raw_max = float(tas.min()), float(tas.max())


    tasC, how, (rmin, rmax, rmed, units) = guess_units_and_convert(tas)


    tasC_yr = tasC.resample(time="YS").mean("time")
    meanC = float(area_mean(tasC_yr).mean("time"))


    msg = []
    msg.append(f"[{root.split('/')[-1]}] {dom} {t0}-{t1}")
    msg.append(f"  units='{units}', scale_factor={sf}, add_offset={ao}")
    msg.append(f"  rango crudo tas: min={raw_min:.2f}, max={raw_max:.2f}")
    msg.append(f"  conversión inferida: {how}")
    msg.append(f"  media anual (°C): {meanC:.2f}")
    return "\n".join(msg)

print("\n=== DIAGNÓSTICO DE TEMPERATURA ===")
for ROOT in ROOTS:

    print(f"\n-- {ROOT.split('/')[-1]} --")
    for dom in DOMS:
        print(diag_one(ROOT, dom, *BASE))
        if dom != "historical_ecuador":
            print(diag_one(ROOT, dom, *LATE))
print("\n=== FIN DIAGNÓSTICO ===\n")

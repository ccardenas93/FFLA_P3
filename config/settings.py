import os


BASE_DIR_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = BASE_DIR_PATH


INPUTS_DIR = os.path.join(BASE_DIR_PATH, "inputs")
OUTPUTS_DIR = os.path.join(BASE_DIR_PATH, "outputs")
REPORTS_DIR = os.path.join(BASE_DIR_PATH, "reports")
DATA_DIR = os.path.join(BASE_DIR_PATH, "data")
DERIVED_DIR = os.path.join(DATA_DIR, "derived")



REGIONS = {
    "FMPLPT": {
        "name": "FMPLPT (Tungurahua)",
        "path": os.path.join(INPUTS_DIR, "FMPLPT"),
        "shapefile": os.path.join(INPUTS_DIR, "ne_countries", "Tungurahua4326.shp")
    },
    "FODESNA": {
        "name": "Napo",
        "path": os.path.join(INPUTS_DIR, "FODESNA"),
        "shapefile": os.path.join(INPUTS_DIR, "ne_countries", "napo4326.shp")
    }
}

def add_dynamic_region(name, inputs_path, shapefile_path, output_path=None):
    """Dynamically adds a new region to the configuration."""
    region_code = name.upper().replace(" ", "_")
    REGIONS[region_code] = {
        "name": name,
        "path": inputs_path,
        "shapefile": shapefile_path
    }
    if output_path:
        REGIONS[region_code]["output_path"] = output_path
    return region_code


DOMAINS = [
    "historical_ecuador",
    "ssp126_ecuador",
    "ssp370_ecuador",
    "ssp585_ecuador"
]


VARS = ['pr', 'tas', 'tasmax', 'tasmin']


PERIOD_START = 1980
PERIOD_END = 2100
BASE_PERIOD = (1981, 2010)


PALETTE = {
    "historical_ecuador": "k",
    "ssp126_ecuador": "tab:green",
    "ssp370_ecuador": "tab:orange",
    "ssp585_ecuador": "tab:red"
}

def get_region_output_dir(region_code):
    """Returns the output directory for a region (derived data + figures). All writes go here."""

    if "output_path" in REGIONS[region_code]:
         return REGIONS[region_code]["output_path"]
    return os.path.join(OUTPUTS_DIR, REGIONS[region_code]["name"])

def get_region_input_dir(region_code):
    """Returns the input directory for a region (read-only: pr, tas, shapefiles)."""
    return REGIONS[region_code]["path"]


OUT_CAT_SERIES_TEMP = "01_Series_Temporales_Temperatura"
OUT_CAT_SERIES_HIDRO = "02_Series_Temporales_Hidrologicas"
OUT_CAT_INDICADORES = "03_Indicadores_Sequia"
OUT_CAT_CLIMATOLOGIA_COMP = "04_Climatologia_Mensual_Comparativa"
OUT_CAT_CLIMATOLOGIA_P = "05_Climatologia_Mensual_Precipitacion"
OUT_CAT_CLIMATOLOGIA_PET = "06_Climatologia_Mensual_Evapotranspiracion"
OUT_CAT_CLIMATOLOGIA_WB = "07_Climatologia_Mensual_Balance_Hidrico"
OUT_CAT_BARRAS_VENTANA = "08_Barras_por_Ventana_Temporal"
OUT_CAT_CAMBIOS_WB = "09_Cambios_Balance_Hidrico"
OUT_CAT_MAPAS_BASE = "10_Mapas_Componentes_Base"
OUT_CAT_MAPAS_DELTA_P = "11_Mapas_Cambios_Precipitacion"
OUT_CAT_MAPAS_DELTA_PET = "12_Mapas_Cambios_Evapotranspiracion"
OUT_CAT_MAPAS_DELTA_WB = "13_Mapas_Cambios_Balance_Hidrico"
OUT_CAT_MATRIZ_VENTANAS = "14_Matriz_MultiVentana"
OUT_CAT_TRIMESTRES_BASE = "15_Trimestres_Base"
OUT_CAT_TRIMESTRES_CAMBIOS = "16_Trimestres_Cambios"
OUT_CAT_MAPAS_MENSUALES_HIST = "17_Mapas_Mensuales_Historico"
OUT_CAT_MAPAS_MENSUALES_SSP126 = "18_Mapas_Mensuales_SSP126"
OUT_CAT_MAPAS_MENSUALES_SSP370 = "19_Mapas_Mensuales_SSP370"
OUT_CAT_MAPAS_MENSUALES_SSP585 = "20_Mapas_Mensuales_SSP585"
OUT_CAT_MAPAS_DELTA_SSP126 = "21_Mapas_Mensuales_Delta_SSP126"
OUT_CAT_MAPAS_DELTA_SSP370 = "22_Mapas_Mensuales_Delta_SSP370"
OUT_CAT_MAPAS_DELTA_SSP585 = "23_Mapas_Mensuales_Delta_SSP585"
OUT_CAT_RESUMEN = "24_Resumen_Ejecutivo"

def fig_path(output_dir, category, filename):
    """Path for a figure: output_dir/category/filename. Creates parent dir if needed."""
    p = os.path.join(output_dir, category, filename)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p

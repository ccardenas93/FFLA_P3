#!/usr/bin/env python3
"""
Generates the consultory's Product 1 dashboard for water-balance climate analysis.
Features navigation per region, scenario, and adds institutional branding.
"""

import os
import sys
from datetime import datetime
import json
import shutil
import subprocess


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from organized.config import settings


REGION_DISPLAY_NAMES = {
    "FODESNA": "FODESNA",
    "FMPLPT": "FMPLPT",
}

REGION_DISPLAY_ORDER = ["FODESNA", "FMPLPT"]

LOGO_FILES = [
    ("FFLA.png", "FFLA"),
    ("FMPLPT.png", "FMPLPT"),
    ("fodesna.jpg", "FODESNA")
]

LOGO_SOURCE_DIR = os.path.join(settings.INPUTS_DIR, "images")
LOGO_OUTPUT_DIR = os.path.join(settings.OUTPUTS_DIR, "assets", "logos")

STATIC_REPO_NAME = "FFLA_P1"

def load_key_numbers_json(file_path):
    """Reads key numbers JSON file."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return None

def get_ai_category(ai):
    """Returns Aridity Index category and color class based on UNEP."""
    if ai < 0.05: return "Hiperárido", "#b91c1c", 5
    if ai < 0.20: return "Árido", "#ea580c", 20
    if ai < 0.50: return "Semiárido", "#d97706", 50
    if ai < 0.65: return "Subhúmedo Seco", "#65a30d", 65
    return "Húmedo", "#059669", 100

def prepare_logo_assets():
    """Copies logos into outputs/assets/logos and returns relative paths."""
    os.makedirs(LOGO_OUTPUT_DIR, exist_ok=True)
    logo_paths = []
    for filename, alt in LOGO_FILES:
        src = os.path.join(LOGO_SOURCE_DIR, filename)
        dst = os.path.join(LOGO_OUTPUT_DIR, filename)
        try:
            shutil.copy2(src, dst)
            rel_path = os.path.relpath(dst, settings.OUTPUTS_DIR)
            logo_paths.append((rel_path.replace("\\", "/"), alt))
        except FileNotFoundError:
            print(f"⚠️ Logo no encontrado: {src}")
    return logo_paths


def generate_html_content(data_source=None):
    logo_assets = prepare_logo_assets()

    # Filter logos based on data_source
    active_logo_assets = []
    for rel_path, alt in logo_assets:
        filename = os.path.basename(rel_path)
        
        # Always include FFLA
        if "FFLA" in filename:
            active_logo_assets.append((rel_path, alt))
            continue
            
        if data_source == "FODESNA":
            if "fodesna" in filename.lower():
                active_logo_assets.append((rel_path, alt))
        elif data_source == "FMPLPT":
            if "FMPLPT" in filename:
                active_logo_assets.append((rel_path, alt))
        else:
            # If no source specified, include all available logos (legacy behavior)
            active_logo_assets.append((rel_path, alt))
    
    # Sort to ensure FFLA is first or last? User didn't specify order, but FFLA is usually last in lists?
    # Actually list order from prepare_logo_assets depends on LOGO_FILES order.
    # LOGO_FILES has FFLA first. So active_logo_assets will have it first.

    html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel de Cambio Climático</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {
            --primary: #0f172a;
            --secondary: #334155;
            --accent: #2563eb;
            --accent-hover: #1d4ed8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --light: #f8fafc;
            --border: #e2e8f0;
            --sidebar-width: 260px;
        }

        * { box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            line-height: 1.6;
            color: var(--secondary);
            margin: 0;
            background-color: #f1f5f9;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }

        /* --- Header --- */
        header {
            background-color: white;
            border-bottom: 1px solid var(--border);
            padding: 15px 30px;
            position: fixed;
            width: 100%;
            top: 0;
            z-index: 50;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 90px;
            gap: 20px;
        }

        .logo-area h1 { margin: 0; font-size: 1.4rem; color: var(--primary); font-weight: 700; }
        .logo-area span { display:block; font-weight: 500; color: #64748b; font-size: 0.85rem; }

        .logo-strip {
            display: flex;
            gap: 14px;
            align-items: center;
        }
        .logo-strip img {
            max-height: 42px;
            width: auto;
            object-fit: contain;
            filter: drop-shadow(0 1px 3px rgba(0,0,0,0.12));
        }

        /* --- Layout --- */
        .main-wrapper {
            display: flex;
            margin-top: 70px; /* Header height */
            height: calc(100vh - 70px);
            overflow: hidden;
        }

        /* --- Sidebar --- */
        .sidebar {
            width: var(--sidebar-width);
            background-color: white;
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            padding: 20px 0;
            overflow-y: auto;
            flex-shrink: 0;
        }

        .sidebar-label {
            padding: 0 20px;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #94a3b8;
            font-weight: 600;
            margin-bottom: 10px;
            margin-top: 20px;
        }

        .nav-item {
            padding: 12px 20px;
            color: var(--secondary);
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 12px;
            border-left: 3px solid transparent;
            transition: all 0.2s;
            cursor: pointer;
            font-size: 0.95rem;
        }

        .nav-item:hover {
            background-color: var(--light);
            color: var(--primary);
        }

        .nav-item.active {
            background-color: #eff6ff;
            color: var(--accent);
            border-left-color: var(--accent);
            font-weight: 600;
        }

        .nav-item i { width: 20px; text-align: center; }

        /* --- Main Content --- */
        .content-area {
            flex: 1;
            padding: 30px;
            overflow-y: auto;
            scroll-behavior: smooth;
        }

        .section-container {
            max-width: 1400px;
            margin: 0 auto;
            margin-bottom: 60px;
        }

        .section-title {
            font-size: 1.5rem;
            color: var(--primary);
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid var(--border);
            display: flex;
            align-items: center;
            gap: 12px;
        }

        /* --- Region Selector (Top Bar) --- */
        .region-selector {
            display: flex;
            gap: 10px;
            background: #f1f5f9;
            padding: 5px;
            border-radius: 8px;
        }

        .region-btn {
            padding: 8px 16px;
            border: none;
            background: transparent;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            color: #64748b;
            transition: all 0.2s;
        }

        .region-btn.active {
            background: white;
            color: var(--accent);
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        /* --- Cards & Grids --- */
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
        }

        .full-width { grid-column: 1 / -1; }

        .card {
            background: white;
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);
        }

        .card-header {
            padding: 15px 20px;
            border-bottom: 1px solid var(--border);
            background: #f8fafc;
            font-weight: 600;
            color: var(--primary);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .card-body { padding: 0; }
        .card-padding { padding: 20px; }

        .img-wrapper {
            width: 100%;
            height: 250px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f1f5f9;
            cursor: zoom-in;
        }

        .img-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center;
            transition: transform 0.5s ease;
        }
        .img-wrapper.img-contain img {
            object-fit: contain;
        }

        .img-wrapper:hover img { transform: scale(1.05); }

        .img-caption {
            padding: 12px 20px;
            font-size: 0.85rem;
            color: #64748b;
            background: white;
            border-top: 1px solid var(--border);
        }

        /* --- Key Metrics Styles --- */
        .metrics-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }

        .kpi-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid var(--border);
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        .kpi-value { font-size: 1.6rem; font-weight: 800; color: var(--primary); margin: 5px 0; }
        .kpi-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; font-weight: 600; }
        .kpi-sub { font-size: 0.8rem; color: #94a3b8; margin-top: 5px; }

        /* AI Gauge */
        .ai-scale {
            margin-top: 10px;
            height: 6px;
            background: #e2e8f0;
            border-radius: 3px;
            position: relative;
            width: 100%;
        }
        .ai-fill {
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s;
        }
        .ai-category {
            font-size: 0.7rem;
            font-weight: 600;
            margin-top: 4px;
        }

        /* --- Data Table --- */
        .table-container {
            overflow-x: auto;
            border-radius: 8px;
            border: 1px solid var(--border);
        }

        table { width: 100%; border-collapse: collapse; background: white; }
        th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.9rem; }
        th { background: #f8fafc; font-weight: 600; color: var(--secondary); }
        tr:last-child td { border-bottom: none; }

        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        .badge-ssp126 { background: #dcfce7; color: #15803d; }
        .badge-ssp370 { background: #fef3c7; color: #b45309; }
        .badge-ssp585 { background: #fee2e2; color: #b91c1c; }

        .val-pos { color: #10b981; font-weight: 600; }
        .val-neg { color: #ef4444; font-weight: 600; }

        /* --- Scenario Tabs --- */
        .scenario-tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }
        .scen-tab {
            padding: 10px 20px;
            cursor: pointer;
            border: 1px solid transparent;
            border-bottom: none;
            border-radius: 6px 6px 0 0;
            background: transparent;
            font-weight: 500;
            color: #64748b;
        }
        .scen-tab:hover { background: #f1f5f9; }
        .scen-tab.active {
            background: white;
            border-color: var(--border);
            color: var(--primary);
            border-bottom-color: white;
            margin-bottom: -1px;
        }

        /* --- Lightbox --- */
        .lightbox {
            display: none;
            position: fixed;
            z-index: 1000;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background-color: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(5px);
            justify-content: center;
            align-items: center;
            padding: 40px;
        }

        .lightbox img {
            max-width: 100%;
            max-height: 100%;
            border-radius: 4px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
        }

        .lightbox-close {
            position: absolute;
            top: 20px; right: 30px;
            color: white;
            font-size: 2rem;
            cursor: pointer;
            opacity: 0.7;
            transition: opacity 0.2s;
        }
        .lightbox-close:hover { opacity: 1; }

    </style>
    <script>
        // Global variable to track the currently active region
        var activeRegion = '';

        function switchRegion(regionId) {
            activeRegion = regionId;

            // Hide all region contents
            document.querySelectorAll('.region-content').forEach(el => el.style.display = 'none');
            // Show selected region content
            document.getElementById('content-' + regionId).style.display = 'block';

            // Update button states
            document.querySelectorAll('.region-btn').forEach(el => el.classList.remove('active'));
            document.getElementById('btn-' + regionId).classList.add('active');
        }

        function scrollToSection(sectionBaseId) {
            // Scroll to the section within the ACTIVE region
            // IDs are formatted as: sectionBaseId-regionCode
            var targetId = sectionBaseId + '-' + activeRegion;
            const el = document.getElementById(targetId);
            if (el) {
                el.scrollIntoView({behavior: 'smooth'});
            } else {
                console.warn('Target element not found:', targetId);
            }
        }

        function switchScenarioTab(regionCode, scenKey) {
            // Hide all contents for this region
            const container = document.getElementById('scen-container-' + regionCode);
            container.querySelectorAll('.scen-content').forEach(el => el.style.display = 'none');

            // Show selected
            document.getElementById('scen-content-' + regionCode + '-' + scenKey).style.display = 'block';

            // Update tabs
            const tabContainer = document.getElementById('scen-tabs-' + regionCode);
            tabContainer.querySelectorAll('.scen-tab').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + regionCode + '-' + scenKey).classList.add('active');
        }

        function openLightbox(src) {
            const lb = document.getElementById('lightbox');
            const img = document.getElementById('lightbox-img');
            img.src = src;
            lb.style.display = 'flex';
        }

        function closeLightbox() {
            document.getElementById('lightbox').style.display = 'none';
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeLightbox();
        });

        // Initialize activeRegion on load
        window.addEventListener('DOMContentLoaded', () => {
            // Find the button with class 'active' to determine default region
            const activeBtn = document.querySelector('.region-btn.active');
            if (activeBtn) {
                // Extract ID from btn-CODE
                activeRegion = activeBtn.id.replace('btn-', '');
            }
        });
    </script>
</head>
<body>

    <header>
        <div class="logo-area">
            <h1>Análisis Climático · Balance Hídrico</h1>
            <span>Producto 1 · Consultoría de Resiliencia Hídrica</span>
        </div>
        <div class="logo-strip">
"""
    for logo_path, logo_alt in active_logo_assets:
        html += f'            <img src="{logo_path}" alt="{logo_alt}">\n'

    html += """        </div>

        <div class="region-selector">
"""


    region_keys = []
    for code in REGION_DISPLAY_ORDER:
        if code in settings.REGIONS and code not in region_keys:
            region_keys.append(code)
    for code in settings.REGIONS.keys():
        if code not in region_keys:
            region_keys.append(code)


    first = True
    for r_code in region_keys:
        active_cls = " active" if first else ""

        r_display = REGION_DISPLAY_NAMES.get(r_code, settings.REGIONS[r_code]['name'])

        html += f"""            <button id="btn-{r_code}" class="region-btn{active_cls}" onclick="switchRegion('{r_code}')">{r_display}</button>\n"""
        first = False

    html += """        </div>
    </header>

    <div class="main-wrapper">

        <!-- SIDEBAR -->
        <div class="sidebar">
            <div class="sidebar-label">Navegación</div>
            <div class="nav-item active" onclick="scrollToSection('resumen')">
                <i class="fas fa-tachometer-alt"></i> Resumen Ejecutivo
            </div>
            <div class="nav-item" onclick="scrollToSection('escenarios')">
                <i class="fas fa-layer-group"></i> Análisis por Escenario
            </div>
            <div class="nav-item" onclick="scrollToSection('series')">
                <i class="fas fa-chart-line"></i> Series Temporales
            </div>
            <div class="nav-item" onclick="scrollToSection('estacionalidad')">
                <i class="fas fa-calendar-alt"></i> Estacionalidad
            </div>
            <div class="nav-item" onclick="scrollToSection('mapas')">
                <i class="fas fa-map"></i> Análisis Espacial
            </div>

            <div style="flex:1"></div>
            <div style="padding: 20px; font-size: 0.75rem; color: #94a3b8; text-align: center;">
                &copy; 2025 Producto 1 · Balance Hídrico<br>Equipo de Consultoría
            </div>
        </div>

        <!-- CONTENT AREA -->
        <div class="content-area">
"""


    first = True





    for r_code in region_keys:


        pass

        r_info = settings.REGIONS[r_code]
        r_name = r_info['name']
        display_style = "block" if first else "none"
        first = False


        json_path = os.path.join(settings.OUTPUTS_DIR, r_name, "24_Resumen_Ejecutivo", "key_numbers.json")
        data = load_key_numbers_json(json_path)


        def img(category, filename):
            return f"{r_name}/{category}/{filename}"

        html += f"""
            <div id="content-{r_code}" class="region-content" style="display: {display_style};">

                <!-- SECTION: RESUMEN EJECUTIVO -->
                <div id="resumen-{r_code}" class="section-container">
                    <div class="section-title"><i class="fas fa-clipboard-check"></i> Resumen Ejecutivo (Línea Base 1981-2010)</div>

                    <!-- Key Metrics -->
                    <div class="metrics-row">
        """

        if data and "baseline" in data:
            b = data["baseline"]


            ai_val = b['AI']
            cat_name, cat_color, cat_pct = get_ai_category(ai_val)

            html += f"""
                        <div class="kpi-card">
                            <div class="kpi-label">Precipitación</div>
                            <div class="kpi-value">{b['P_annual']['mean']} <span style="font-size:1rem; font-weight:400">mm</span></div>
                            <div class="kpi-sub">σ = {b['P_annual']['std']} mm</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Evapotranspiración</div>
                            <div class="kpi-value">{b['PET_annual']['mean']} <span style="font-size:1rem; font-weight:400">mm</span></div>
                            <div class="kpi-sub">Demanda Potencial</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Balance Hídrico</div>
                            <div class="kpi-value">{b['WB_annual']['mean']} <span style="font-size:1rem; font-weight:400">mm</span></div>
                            <div class="kpi-sub">Oferta Neta</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Temperatura</div>
                            <div class="kpi-value">{b['Temp']}°C</div>
                            <div class="kpi-sub">Media Anual</div>
                        </div>
                         <div class="kpi-card">
                            <div class="kpi-label">Aridez (AI)</div>
                            <div class="kpi-value">{b['AI']}</div>
                            <div class="ai-scale"><div class="ai-fill" style="width: {cat_pct}%; background-color: {cat_color};"></div></div>
                            <div class="ai-category" style="color: {cat_color};">{cat_name}</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Racha Seca (CDD)</div>
                            <div class="kpi-value">{b['CDD']} <span style="font-size:1rem; font-weight:400">días</span></div>
                            <div class="kpi-sub">Máximo consecutivo</div>
                        </div>
            """

        html += """
                    </div>

                    <!-- Warming Stripes -->
                    <div class="card full-width" style="margin-bottom: 30px;">
                        <div class="card-header">
                            <span><i class="fas fa-temperature-high"></i> Evolución Histórica y Proyectada (Warming Stripes)</span>
                        </div>
                        <div class="img-wrapper img-contain" style="height: 220px;" onclick="openLightbox('{}')">
                            <img src="{}" loading="lazy">
                        </div>
                    </div>
                </div>

                <!-- SECTION: ESCENARIOS -->
                <div id="escenarios-{code}" class="section-container">
                    <div class="section-title"><i class="fas fa-layer-group"></i> Análisis por Escenario</div>

                    <div class="scenario-tabs" id="scen-tabs-{code}">
                        <div id="tab-{code}-ssp126" class="scen-tab active" onclick="switchScenarioTab('{code}', 'ssp126')">SSP1-2.6 (Optimista)</div>
                        <div id="tab-{code}-ssp370" class="scen-tab" onclick="switchScenarioTab('{code}', 'ssp370')">SSP3-7.0 (Medio)</div>
                        <div id="tab-{code}-ssp585" class="scen-tab" onclick="switchScenarioTab('{code}', 'ssp585')">SSP5-8.5 (Pesimista)</div>
                    </div>

                    <div id="scen-container-{code}">
        """.format(
            img('01_Series_Temporales_Temperatura', 'warming_stripes_anomalias.png'),
            img('01_Series_Temporales_Temperatura', 'warming_stripes_anomalias.png'),
            code=r_code
        )


        scenarios = [("ssp126", "SSP1-2.6"), ("ssp370", "SSP3-7.0"), ("ssp585", "SSP5-8.5")]
        for i, (scen_key, scen_label) in enumerate(scenarios):
            display = "block" if i == 0 else "none"


            table_rows = ""
            if data and "projections" in data:

                scen_data = data["projections"].get(scen_key, {})

                periods = ["2021-2050", "2041-2070", "2071-2100"]
                period_labels = ["Cercano (2021-2050)", "Medio (2041-2070)", "Tardío (2071-2100)"]

                for pid, plabel in zip(periods, period_labels):
                    p = scen_data.get(pid, {})
                    dWB = p.get('delta_WB_mm', 0)
                    cls_wb = "val-neg" if dWB < 0 else "val-pos"

                    table_rows += f"""
                        <tr>
                            <td><b>{plabel}</b></td>
                            <td>+{p.get('delta_Temp', 'N/A')}°C</td>
                            <td>{p.get('delta_P_mm', 0):+} mm ({p.get('delta_P_pct', 0):+}%)</td>
                            <td class="{cls_wb}">{dWB:+} mm ({p.get('delta_WB_pct', 0):+}%)</td>
                            <td>{p.get('delta_DryDays', 0):+} días</td>
                            <td>{p.get('delta_CDD', 0):+} días</td>
                        </tr>
                    """


            bar_chart = img('09_Cambios_Balance_Hidrico', f'delta_WB_{scen_key}.png')

            map_near = img(f'21_Mapas_Mensuales_Delta_{scen_key.upper()}', f'delta_WB_mensual_{scen_key}_cercano.png')
            map_mid = img(f'21_Mapas_Mensuales_Delta_{scen_key.upper()}', f'delta_WB_mensual_{scen_key}_medio.png')
            map_late = img(f'21_Mapas_Mensuales_Delta_{scen_key.upper()}', f'delta_WB_mensual_{scen_key}_tardio.png')


            if scen_key == 'ssp370':
                map_near = img('22_Mapas_Mensuales_Delta_SSP370', f'delta_WB_mensual_{scen_key}_cercano.png')
                map_mid = img('22_Mapas_Mensuales_Delta_SSP370', f'delta_WB_mensual_{scen_key}_medio.png')
                map_late = img('22_Mapas_Mensuales_Delta_SSP370', f'delta_WB_mensual_{scen_key}_tardio.png')
            elif scen_key == 'ssp585':
                map_near = img('23_Mapas_Mensuales_Delta_SSP585', f'delta_WB_mensual_{scen_key}_cercano.png')
                map_mid = img('23_Mapas_Mensuales_Delta_SSP585', f'delta_WB_mensual_{scen_key}_medio.png')
                map_late = img('23_Mapas_Mensuales_Delta_SSP585', f'delta_WB_mensual_{scen_key}_tardio.png')

            html += f"""
                        <div id="scen-content-{r_code}-{scen_key}" class="scen-content" style="display: {display};">
                            <div class="dashboard-grid">
                                <!-- Evolution Table -->
                                <div class="card full-width">
                                    <div class="card-header">Evolución Temporal de Impactos ({scen_label})</div>
                                    <div class="table-container">
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th>Horizonte</th>
                                                    <th>Δ Temperatura</th>
                                                    <th>Δ Precipitación</th>
                                                    <th>Δ Balance Hídrico</th>
                                                    <th>Δ Días Secos</th>
                                                    <th>Δ Racha Seca (CDD)</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {table_rows}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>

                                <!-- Bar Chart -->
                                <div class="card">
                                    <div class="card-header">Cambio en Balance Hídrico (Anual)</div>
                                    <div class="img-wrapper" onclick="openLightbox('{bar_chart}')">
                                        <img src="{bar_chart}" loading="lazy">
                                    </div>
                                </div>

                                <!-- Monthly Maps -->
                                <div class="card">
                                    <div class="card-header">Mapa Mensual: Cercano (2021-2050)</div>
                                    <div class="img-wrapper" onclick="openLightbox('{map_near}')">
                                        <img src="{map_near}" loading="lazy">
                                    </div>
                                </div>
                                <div class="card">
                                    <div class="card-header">Mapa Mensual: Medio (2041-2070)</div>
                                    <div class="img-wrapper" onclick="openLightbox('{map_mid}')">
                                        <img src="{map_mid}" loading="lazy">
                                    </div>
                                </div>
                                <div class="card">
                                    <div class="card-header">Mapa Mensual: Tardío (2071-2100)</div>
                                    <div class="img-wrapper" onclick="openLightbox('{map_late}')">
                                        <img src="{map_late}" loading="lazy">
                                    </div>
                                </div>
                            </div>
                        </div>
            """

        html += """
                    </div>
                </div>

                <!-- SECTION: SERIES TEMPORALES -->
                <div id="series-{code}" class="section-container">
                    <div class="section-title"><i class="fas fa-chart-line"></i> Series Temporales (1980-2100)</div>

                    <div class="dashboard-grid">
                        <div class="card">
                            <div class="card-header">Temperatura Media</div>
                            <div class="img-wrapper" onclick="openLightbox('{}')"><img src="{}" loading="lazy"></div>
                        </div>
                        <div class="card">
                            <div class="card-header">Temperatura Máxima</div>
                            <div class="img-wrapper" onclick="openLightbox('{}')"><img src="{}" loading="lazy"></div>
                        </div>

                        <div class="card">
                            <div class="card-header">Precipitación Anual</div>
                            <div class="img-wrapper" onclick="openLightbox('{}')"><img src="{}" loading="lazy"></div>
                        </div>
                         <div class="card">
                            <div class="card-header">Balance Hídrico</div>
                            <div class="img-wrapper" onclick="openLightbox('{}')"><img src="{}" loading="lazy"></div>
                        </div>

                        <div class="card">
                            <div class="card-header">Índice de Aridez</div>
                            <div class="img-wrapper" onclick="openLightbox('{}')"><img src="{}" loading="lazy"></div>
                        </div>
                        <div class="card">
                            <div class="card-header">Días Secos Consecutivos (CDD)</div>
                            <div class="img-wrapper" onclick="openLightbox('{}')"><img src="{}" loading="lazy"></div>
                        </div>
                    </div>
                </div>

                <!-- SECTION: ESTACIONALIDAD -->
                <div id="estacionalidad-{code}" class="section-container">
                    <div class="section-title"><i class="fas fa-calendar-alt"></i> Ciclo Estacional y Cambios</div>

                    <div class="dashboard-grid">
                        <div class="card full-width">
                             <div class="card-header">Comparativa Ciclo Anual: Balance Hídrico</div>
                             <div class="img-wrapper" style="height: 300px;" onclick="openLightbox('{}')">
                                <img src="{}" loading="lazy">
                             </div>
                        </div>

                        <div class="card">
                             <div class="card-header">Ciclo Precipitación</div>
                             <div class="img-wrapper" onclick="openLightbox('{}')"><img src="{}" loading="lazy"></div>
                        </div>
                        <div class="card">
                             <div class="card-header">Ciclo Evapotranspiración</div>
                             <div class="img-wrapper" onclick="openLightbox('{}')"><img src="{}" loading="lazy"></div>
                        </div>

                        <div class="card">
                             <div class="card-header">Mapas Trimestrales (Base)</div>
                             <div class="img-wrapper" onclick="openLightbox('{}')"><img src="{}" loading="lazy"></div>
                             <div class="img-caption">Trimestres más húmedo y seco (1981-2010)</div>
                        </div>
                        <div class="card">
                             <div class="card-header">Cambio Trimestral (SSP5-8.5)</div>
                             <div class="img-wrapper" onclick="openLightbox('{}')"><img src="{}" loading="lazy"></div>
                             <div class="img-caption">Alteración en patrones estacionales</div>
                        </div>
                    </div>
                </div>

                <!-- SECTION: MAPAS -->
                <div id="mapas-{code}" class="section-container">
                    <div class="section-title"><i class="fas fa-map-marked-alt"></i> Análisis Espacial de Impactos</div>
                    <div style="margin-bottom: 20px; color: #64748b;">Mostrando horizonte tardío (2071-2100) bajo escenario pesimista (SSP5-8.5) para resaltar riesgos máximos.</div>

                    <div class="dashboard-grid">
                        <div class="card">
                            <div class="card-header">Cambio en Precipitación</div>
                            <div class="img-wrapper" onclick="openLightbox('{}')"><img src="{}" loading="lazy"></div>
                        </div>
                        <div class="card">
                            <div class="card-header">Cambio en Balance Hídrico</div>
                            <div class="img-wrapper" onclick="openLightbox('{}')"><img src="{}" loading="lazy"></div>
                        </div>

                        <div class="card full-width">
                            <div class="card-header">Detalle Mensual de Cambios (Delta WB)</div>
                            <div class="img-wrapper" style="height: 500px;" onclick="openLightbox('{}')">
                                <img src="{}" loading="lazy">
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        """.format(

            img('01_Series_Temporales_Temperatura', 'temperatura_media_anual.png'), img('01_Series_Temporales_Temperatura', 'temperatura_media_anual.png'),
            img('01_Series_Temporales_Temperatura', 'temperatura_maxima_anual.png'), img('01_Series_Temporales_Temperatura', 'temperatura_maxima_anual.png'),
            img('02_Series_Temporales_Hidrologicas', 'precipitacion_anual.png'), img('02_Series_Temporales_Hidrologicas', 'precipitacion_anual.png'),
            img('02_Series_Temporales_Hidrologicas', 'balance_hidrico_anual.png'), img('02_Series_Temporales_Hidrologicas', 'balance_hidrico_anual.png'),
            img('03_Indicadores_Sequia', 'indice_aridez_serie_temporal.png'), img('03_Indicadores_Sequia', 'indice_aridez_serie_temporal.png'),
            img('03_Indicadores_Sequia', 'dias_secos_consecutivos_serie_temporal.png'), img('03_Indicadores_Sequia', 'dias_secos_consecutivos_serie_temporal.png'),


            img('04_Climatologia_Mensual_Comparativa', 'ciclo_anual_balance_hidrico.png'), img('04_Climatologia_Mensual_Comparativa', 'ciclo_anual_balance_hidrico.png'),
            img('04_Climatologia_Mensual_Comparativa', 'ciclo_anual_precipitacion.png'), img('04_Climatologia_Mensual_Comparativa', 'ciclo_anual_precipitacion.png'),
            img('04_Climatologia_Mensual_Comparativa', 'ciclo_anual_evapotranspiracion.png'), img('04_Climatologia_Mensual_Comparativa', 'ciclo_anual_evapotranspiracion.png'),
            img('15_Trimestres_Base', 'WB_trimestres_base_1981-2010.png'), img('15_Trimestres_Base', 'WB_trimestres_base_1981-2010.png'),
            img('16_Trimestres_Cambios', 'delta_trimestres_ssp585.png'), img('16_Trimestres_Cambios', 'delta_trimestres_ssp585.png'),


            img('11_Mapas_Cambios_Precipitacion', 'delta_P_tardio_2071-2100.png'), img('11_Mapas_Cambios_Precipitacion', 'delta_P_tardio_2071-2100.png'),
            img('13_Mapas_Cambios_Balance_Hidrico', 'delta_WB_tardio_2071-2100.png'), img('13_Mapas_Cambios_Balance_Hidrico', 'delta_WB_tardio_2071-2100.png'),
            img('23_Mapas_Mensuales_Delta_SSP585', 'delta_WB_mensual_ssp585_tardio.png'), img('23_Mapas_Mensuales_Delta_SSP585', 'delta_WB_mensual_ssp585_tardio.png'),
            code=r_code
        )

    html += """
        </div> <!-- End Content Area -->
    </div> <!-- End Main Wrapper -->

    <!-- Lightbox -->
    <div id="lightbox" class="lightbox" onclick="closeLightbox()">
        <span class="lightbox-close">&times;</span>
        <img id="lightbox-img">
    </div>

</body>
</html>
"""

    output_path = os.path.join(settings.OUTPUTS_DIR, "index.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Dashboard generado: {output_path}")


def export_static_site():
    """Copies the generated dashboard into the GitHub repository and pushes changes."""
    project_root = os.path.abspath(os.path.join(settings.BASE_DIR_PATH, ".."))
    repo_path = os.path.join(project_root, STATIC_REPO_NAME)

    if not os.path.isdir(repo_path):
        print(f"⚠️ Repositorio estático no encontrado en {repo_path}. Omitiendo despliegue.")
        return

    print(f"🚚 Actualizando sitio estático en {repo_path}")

    for item in os.listdir(repo_path):
        if item == ".git":
            continue
        target = os.path.join(repo_path, item)
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)

    for item in os.listdir(settings.OUTPUTS_DIR):
        src = os.path.join(settings.OUTPUTS_DIR, item)
        dst = os.path.join(repo_path, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    def run_git(cmd):
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            raise RuntimeError(f"Git command failed: {' '.join(cmd)}")
        return result.stdout.strip()

    run_git(["git", "add", "-A"])
    status = run_git(["git", "status", "--porcelain"])
    if not status:
        print("ℹ️ No hay cambios para publicar.")
        return

    commit_msg = f"Actualización del dashboard {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    run_git(["git", "commit", "-m", commit_msg])

    pushed = False
    for branch in ("main", "master"):
        try:
            run_git(["git", "push", "origin", branch])
            pushed = True
            break
        except RuntimeError:
            continue
    if not pushed:
        print("⚠️ Falló el push automático. Revisa el repositorio manualmente.")
        return

    print("🚀 Sitio estático publicado en GitHub.")

def run(deploy_to_github=False, data_source=None):
    """
    Generate dashboard HTML and optionally deploy to GitHub repo.
    Args:
        deploy_to_github: If True, copies outputs to FFLA_P1 repo and runs git commit/push.
                          Set to True only when you want to publish; leave False for local/exe use.
        data_source: 'FODESNA' or 'FMPLPT' to filter logos.
    """
    generate_html_content(data_source)
    if deploy_to_github or os.environ.get("DEPLOY_DASHBOARD", "").lower() in ("1", "true", "yes"):
        export_static_site()
    else:
        print("ℹ️ Dashboard generado localmente. Para publicar en GitHub, ejecuta con deploy_to_github=True o DEPLOY_DASHBOARD=1")

if __name__ == "__main__":
    run()

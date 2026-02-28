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

STATIC_REPO_NAME = "FFLA_P1"

NAV_SECTIONS = [
    ("resumen", "fa-clipboard-check", "Resumen Ejecutivo"),
    ("escenarios", "fa-layer-group", "Análisis por Escenario"),
    ("series", "fa-chart-line", "Series Temporales"),
    ("estacionalidad", "fa-calendar-alt", "Estacionalidad"),
    ("mapas", "fa-map-marked-alt", "Análisis Espacial"),
]

SCENARIOS = [
    ("ssp126", "SSP1-2.6", "Optimista"),
    ("ssp370", "SSP3-7.0", "Intermedio"),
    ("ssp585", "SSP5-8.5", "Alto"),
]

SCENARIO_MONTHLY_DELTA_DIR = {
    "ssp126": "21_Mapas_Mensuales_Delta_SSP126",
    "ssp370": "22_Mapas_Mensuales_Delta_SSP370",
    "ssp585": "23_Mapas_Mensuales_Delta_SSP585",
}

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


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt_number(value, decimals=1, signed=False, suffix=""):
    num = _to_float(value)
    if num is None:
        return "N/A"
    fmt = f"{{:{'+' if signed else ''}.{decimals}f}}"
    if decimals == 0:
        fmt = f"{{:{'+' if signed else ''}.0f}}"
    return f"{fmt.format(num)}{suffix}"

def prepare_logo_assets(output_root):
    """Copies logos into outputs/assets/logos and returns relative paths."""
    logo_output_dir = os.path.join(output_root, "assets", "logos")
    os.makedirs(logo_output_dir, exist_ok=True)
    logo_paths = []
    for filename, alt in LOGO_FILES:
        src = os.path.join(LOGO_SOURCE_DIR, filename)
        dst = os.path.join(logo_output_dir, filename)
        try:
            shutil.copy2(src, dst)
            rel_path = os.path.relpath(dst, output_root)
            logo_paths.append((rel_path.replace("\\", "/"), alt))
        except FileNotFoundError:
            print(f"⚠️ Logo no encontrado: {src}")
    return logo_paths


def generate_html_content(data_source=None, output_root=None, region_codes=None, regions=None):
    output_root = output_root or settings.OUTPUTS_DIR
    os.makedirs(output_root, exist_ok=True)
    active_regions = regions or settings.REGIONS
    if region_codes:
        active_regions = {code: active_regions[code] for code in region_codes if code in active_regions}

    logo_assets = prepare_logo_assets(output_root)

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
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {
            --primary: #0c2a38;
            --secondary: #274457;
            --accent: #007f8f;
            --accent-strong: #005f73;
            --surface: #ffffff;
            --surface-soft: #f4f8fb;
            --bg-1: #e9f3f8;
            --bg-2: #f7fbff;
            --border: #d4e4ee;
            --text-muted: #597083;
            --sidebar-width: 300px;
            --ok: #0f9d73;
            --risk: #dc4d41;
            --header-height: 108px;
        }

        * { box-sizing: border-box; }

        body {
            font-family: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            line-height: 1.55;
            color: var(--secondary);
            margin: 0;
            min-height: 100vh;
            background:
                radial-gradient(circle at 10% 0%, rgba(0, 127, 143, 0.10) 0%, rgba(0, 127, 143, 0) 38%),
                radial-gradient(circle at 100% 15%, rgba(12, 42, 56, 0.09) 0%, rgba(12, 42, 56, 0) 35%),
                linear-gradient(180deg, var(--bg-1), var(--bg-2));
        }

        .app-shell-bg {
            position: fixed;
            inset: 0;
            pointer-events: none;
            background-image: linear-gradient(rgba(39, 68, 87, 0.03) 1px, transparent 1px),
                              linear-gradient(90deg, rgba(39, 68, 87, 0.03) 1px, transparent 1px);
            background-size: 24px 24px;
            opacity: 0.6;
            z-index: 0;
        }

        header {
            background-color: rgba(255, 255, 255, 0.92);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid var(--border);
            padding: 16px 28px;
            position: fixed;
            width: 100%;
            top: 0;
            z-index: 50;
            display: flex;
            justify-content: space-between;
            align-items: center;
            min-height: var(--header-height);
            gap: 20px;
        }

        .logo-area h1 {
            font-family: "IBM Plex Serif", Georgia, serif;
            margin: 0;
            font-size: 1.38rem;
            color: var(--primary);
            font-weight: 600;
            letter-spacing: 0.2px;
        }
        .logo-area span {
            display: block;
            margin-top: 3px;
            font-weight: 500;
            color: var(--text-muted);
            font-size: 0.85rem;
        }

        .logo-strip {
            display: flex;
            gap: 14px;
            align-items: center;
        }
        .logo-strip img {
            max-height: 36px;
            width: auto;
            object-fit: contain;
        }

        .main-wrapper {
            display: flex;
            margin-top: var(--header-height);
            height: calc(100vh - var(--header-height));
            overflow: hidden;
            position: relative;
            z-index: 1;
        }

        .sidebar {
            width: var(--sidebar-width);
            background-color: rgba(255, 255, 255, 0.94);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            padding: 20px 0;
            overflow-y: auto;
            flex-shrink: 0;
        }

        .sidebar-label {
            padding: 0 20px;
            font-size: 0.73rem;
            text-transform: uppercase;
            letter-spacing: 1.1px;
            color: #7f95a5;
            font-weight: 700;
            margin: 12px 0;
        }

        .nav-item {
            width: 100%;
            border: none;
            background: transparent;
            padding: 12px 20px;
            color: var(--secondary);
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 12px;
            border-left: 3px solid transparent;
            transition: all 0.2s ease;
            cursor: pointer;
            font-size: 0.95rem;
            text-align: left;
        }

        .nav-item:hover {
            background-color: #edf5fb;
            color: var(--primary);
        }

        .nav-item.active {
            background: linear-gradient(90deg, rgba(0, 127, 143, 0.16), rgba(0, 127, 143, 0.03));
            color: var(--accent-strong);
            border-left-color: var(--accent);
            font-weight: 700;
        }

        .nav-item i { width: 20px; text-align: center; }

        .sidebar-note {
            margin: 18px 16px 0 16px;
            padding: 12px;
            border: 1px solid var(--border);
            border-radius: 10px;
            background: var(--surface-soft);
            font-size: 0.78rem;
            color: var(--text-muted);
        }

        .sidebar-note b {
            display: block;
            color: var(--secondary);
            margin-bottom: 6px;
        }

        .content-area {
            flex: 1;
            padding: 28px 28px 56px 28px;
            overflow-y: auto;
            scroll-behavior: smooth;
        }

        .section-container {
            max-width: 1440px;
            margin: 0 auto 48px auto;
            scroll-margin-top: 22px;
        }

        .section-title {
            font-size: 1.5rem;
            color: var(--primary);
            margin-bottom: 18px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--border);
            display: flex;
            align-items: center;
            gap: 10px;
            font-family: "IBM Plex Serif", Georgia, serif;
        }

        .section-subtitle {
            margin: -8px 0 20px 0;
            color: var(--text-muted);
            font-size: 0.93rem;
        }

        .region-selector {
            display: flex;
            gap: 8px;
            background: #eaf3f8;
            padding: 6px;
            border-radius: 9px;
            border: 1px solid var(--border);
        }

        .region-btn {
            padding: 8px 14px;
            border: 1px solid transparent;
            background: transparent;
            border-radius: 7px;
            cursor: pointer;
            font-weight: 600;
            color: #466175;
            transition: all 0.2s;
        }

        .region-btn.active {
            background: white;
            color: var(--accent-strong);
            border-color: #c7deea;
            box-shadow: 0 1px 3px rgba(12, 42, 56, 0.08);
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
            gap: 18px;
        }

        .full-width { grid-column: 1 / -1; }

        .card {
            background: var(--surface);
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 2px 6px rgba(12, 42, 56, 0.05);
            overflow: hidden;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 20px rgba(12, 42, 56, 0.08);
        }

        .card-header {
            padding: 13px 16px;
            border-bottom: 1px solid var(--border);
            background: #f2f8fc;
            font-weight: 600;
            color: var(--primary);
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
        }

        .card-padding { padding: 16px; }

        .science-callout {
            background: linear-gradient(135deg, rgba(0, 127, 143, 0.10), rgba(0, 127, 143, 0.02));
            border: 1px solid #b7d7e3;
            border-radius: 12px;
            padding: 14px 16px;
            margin-bottom: 18px;
        }

        .science-callout b {
            color: var(--primary);
            font-size: 0.88rem;
        }

        .science-grid {
            margin-top: 8px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 8px 14px;
            font-size: 0.83rem;
            color: var(--text-muted);
        }

        .img-wrapper {
            width: 100%;
            height: 240px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #eef6fb;
            cursor: zoom-in;
        }

        .img-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center;
            transition: transform 0.45s ease;
        }
        .img-wrapper.img-contain img {
            object-fit: contain;
        }
        .img-wrapper:hover img { transform: scale(1.03); }

        .img-caption {
            padding: 10px 14px;
            font-size: 0.82rem;
            color: #668094;
            background: white;
            border-top: 1px solid var(--border);
        }

        .metrics-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }

        .kpi-card {
            background: linear-gradient(180deg, #ffffff, #f8fcff);
            padding: 16px 12px;
            border-radius: 10px;
            border: 1px solid var(--border);
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        .kpi-value { font-size: 1.45rem; font-weight: 800; color: var(--primary); margin: 4px 0; }
        .kpi-label { font-size: 0.74rem; color: #617b8f; text-transform: uppercase; font-weight: 700; letter-spacing: 0.4px; }
        .kpi-sub { font-size: 0.79rem; color: #8399a8; margin-top: 4px; }

        .ai-scale {
            margin-top: 9px;
            height: 6px;
            background: #dcebf3;
            border-radius: 3px;
            width: 100%;
        }
        .ai-fill { height: 100%; border-radius: 3px; }
        .ai-category {
            font-size: 0.72rem;
            font-weight: 700;
            margin-top: 4px;
        }

        .table-container {
            overflow-x: auto;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: white;
        }

        table { width: 100%; border-collapse: collapse; background: white; }
        th, td { padding: 11px 14px; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.87rem; }
        th { background: #f1f8fc; font-weight: 700; color: var(--secondary); white-space: nowrap; }
        tr:last-child td { border-bottom: none; }

        .val-pos { color: var(--ok); font-weight: 700; }
        .val-neg { color: var(--risk); font-weight: 700; }

        .scenario-tabs {
            display: flex;
            gap: 6px;
            margin-bottom: 12px;
            border-bottom: 1px solid var(--border);
            overflow-x: auto;
            padding-bottom: 2px;
        }
        .scen-tab {
            padding: 9px 14px;
            cursor: pointer;
            border: 1px solid transparent;
            border-bottom: none;
            border-radius: 8px 8px 0 0;
            background: transparent;
            font-weight: 600;
            color: #5f778a;
            white-space: nowrap;
        }
        .scen-tab:hover { background: #eef6fb; }
        .scen-tab.active {
            background: white;
            border-color: var(--border);
            color: var(--primary);
            border-bottom-color: white;
            margin-bottom: -1px;
        }

        .scenario-legend {
            margin-bottom: 14px;
            font-size: 0.82rem;
            color: var(--text-muted);
            display: flex;
            flex-wrap: wrap;
            gap: 14px;
            align-items: center;
        }

        .legend-dot {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .legend-dot::before {
            content: "";
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }
        .legend-dot.pos::before { background: var(--ok); }
        .legend-dot.neg::before { background: var(--risk); }

        .footer-note {
            padding: 18px 20px;
            font-size: 0.76rem;
            color: #7f95a5;
            text-align: center;
            border-top: 1px solid var(--border);
        }

        .lightbox {
            display: none;
            position: fixed;
            z-index: 1000;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(12, 42, 56, 0.94);
            backdrop-filter: blur(6px);
            justify-content: center;
            align-items: center;
            padding: 30px;
        }

        .lightbox img {
            max-width: 100%;
            max-height: 100%;
            border-radius: 6px;
            box-shadow: 0 20px 24px rgba(0, 0, 0, 0.42);
            border: 1px solid rgba(255, 255, 255, 0.22);
        }

        .lightbox-close {
            position: absolute;
            top: 16px;
            right: 24px;
            color: white;
            font-size: 2rem;
            cursor: pointer;
            opacity: 0.78;
            transition: opacity 0.2s;
        }
        .lightbox-close:hover { opacity: 1; }

        @media (max-width: 1100px) {
            header {
                padding: 14px 18px;
                flex-wrap: wrap;
                min-height: 126px;
            }
            .main-wrapper {
                margin-top: 126px;
                height: calc(100vh - 126px);
            }
            .sidebar {
                width: 250px;
            }
        }

        @media (max-width: 920px) {
            .main-wrapper {
                flex-direction: column;
                height: calc(100vh - 126px);
                min-height: calc(100vh - 126px);
                overflow: hidden;
            }
            .sidebar {
                width: 100%;
                border-right: none;
                border-bottom: 1px solid var(--border);
                padding: 10px 0;
            }
            .content-area {
                overflow-y: auto;
                padding: 20px 12px 40px 12px;
            }
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
            .section-container {
                margin-bottom: 32px;
            }
        }
    </style>
    <script>
        let activeRegion = "";
        let observer = null;
        let isScrollTicking = false;
        let suppressObserver = false;

        function getContentArea() {
            return document.getElementById("contentArea");
        }

        function getActiveSections() {
            if (!activeRegion) {
                return [];
            }
            return Array.from(
                document.querySelectorAll('#content-' + activeRegion + ' .section-container[data-section]')
            );
        }

        function setActiveNav(sectionBaseId) {
            document.querySelectorAll('.nav-item').forEach((el) => {
                if (el.dataset.section === sectionBaseId) {
                    el.classList.add('active');
                } else {
                    el.classList.remove('active');
                }
            });
        }

        function updateActiveNavByScroll() {
            if (suppressObserver) {
                return;
            }
            const contentArea = getContentArea();
            const sections = getActiveSections();
            if (!contentArea || sections.length === 0) {
                return;
            }

            const rootTop = contentArea.getBoundingClientRect().top;
            let bestSection = sections[0];
            let bestDistance = Number.POSITIVE_INFINITY;

            sections.forEach((section) => {
                const distance = Math.abs(section.getBoundingClientRect().top - rootTop - 76);
                if (distance < bestDistance) {
                    bestDistance = distance;
                    bestSection = section;
                }
            });

            const sectionBaseId = bestSection.dataset.section;
            if (sectionBaseId) {
                setActiveNav(sectionBaseId);
            }
        }

        function reconnectObserver() {
            if (observer) {
                observer.disconnect();
                observer = null;
            }

            const contentArea = getContentArea();
            const sections = getActiveSections();
            if (!contentArea || sections.length === 0 || !('IntersectionObserver' in window)) {
                updateActiveNavByScroll();
                return;
            }

            observer = new IntersectionObserver((entries) => {
                if (suppressObserver) {
                    return;
                }
                const visible = entries
                    .filter((entry) => entry.isIntersecting)
                    .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
                if (visible.length > 0) {
                    const sectionBaseId = visible[0].target.dataset.section;
                    if (sectionBaseId) {
                        setActiveNav(sectionBaseId);
                    }
                }
            }, {
                root: contentArea,
                threshold: [0.2, 0.35, 0.6],
                rootMargin: "-15% 0px -55% 0px",
            });

            sections.forEach((section) => observer.observe(section));
            updateActiveNavByScroll();
        }

        function switchRegion(regionId) {
            activeRegion = regionId;
            document.querySelectorAll('.region-content').forEach((el) => { el.style.display = 'none'; });
            const regionPanel = document.getElementById('content-' + regionId);
            if (regionPanel) {
                regionPanel.style.display = 'block';
            }

            document.querySelectorAll('.region-btn').forEach((el) => el.classList.remove('active'));
            const regionBtn = document.getElementById('btn-' + regionId);
            if (regionBtn) {
                regionBtn.classList.add('active');
            }

            const contentArea = getContentArea();
            if (contentArea) {
                contentArea.scrollTo({ top: 0, behavior: 'auto' });
            }
            setActiveNav('resumen');
            reconnectObserver();
        }

        function scrollToSection(sectionBaseId) {
            const targetId = sectionBaseId + '-' + activeRegion;
            const el = document.getElementById(targetId);
            if (!el) {
                return;
            }

            suppressObserver = true;
            setActiveNav(sectionBaseId);
            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            window.setTimeout(() => {
                suppressObserver = false;
                updateActiveNavByScroll();
            }, 450);
        }

        function switchScenarioTab(regionCode, scenKey) {
            const container = document.getElementById('scen-container-' + regionCode);
            if (!container) {
                return;
            }
            container.querySelectorAll('.scen-content').forEach((el) => { el.style.display = 'none'; });
            const target = document.getElementById('scen-content-' + regionCode + '-' + scenKey);
            if (target) {
                target.style.display = 'block';
            }

            const tabContainer = document.getElementById('scen-tabs-' + regionCode);
            if (!tabContainer) {
                return;
            }
            tabContainer.querySelectorAll('.scen-tab').forEach((el) => el.classList.remove('active'));
            const tab = document.getElementById('tab-' + regionCode + '-' + scenKey);
            if (tab) {
                tab.classList.add('active');
            }
        }

        function openLightbox(src) {
            const lb = document.getElementById('lightbox');
            const img = document.getElementById('lightbox-img');
            if (!lb || !img) {
                return;
            }
            img.src = src;
            lb.style.display = 'flex';
        }

        function closeLightbox() {
            const lb = document.getElementById('lightbox');
            if (lb) {
                lb.style.display = 'none';
            }
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeLightbox();
            }
        });

        window.addEventListener('DOMContentLoaded', () => {
            const activeBtn = document.querySelector('.region-btn.active');
            if (activeBtn) {
                activeRegion = activeBtn.id.replace('btn-', '');
            } else {
                const firstBtn = document.querySelector('.region-btn');
                if (firstBtn) {
                    activeRegion = firstBtn.id.replace('btn-', '');
                    firstBtn.classList.add('active');
                }
            }

            const contentArea = getContentArea();
            if (contentArea) {
                contentArea.addEventListener('scroll', () => {
                    if (!isScrollTicking) {
                        window.requestAnimationFrame(() => {
                            updateActiveNavByScroll();
                            isScrollTicking = false;
                        });
                        isScrollTicking = true;
                    }
                });
            }

            setActiveNav('resumen');
            reconnectObserver();
            window.addEventListener('resize', updateActiveNavByScroll);
        });
    </script>
</head>
<body>
    <div class="app-shell-bg"></div>

    <header>
        <div class="logo-area">
            <h1>Análisis Climático · Balance Hídrico</h1>
            <span>Producto 1 · Tablero técnico para evaluación hidroclimática</span>
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
        if code in active_regions and code not in region_keys:
            region_keys.append(code)
    for code in active_regions.keys():
        if code not in region_keys:
            region_keys.append(code)


    first = True
    for r_code in region_keys:
        active_cls = " active" if first else ""

        r_display = REGION_DISPLAY_NAMES.get(r_code, active_regions[r_code]['name'])

        html += f"""            <button id="btn-{r_code}" class="region-btn{active_cls}" onclick="switchRegion('{r_code}')">{r_display}</button>\n"""
        first = False

    html += """        </div>
    </header>

    <div class="main-wrapper">

        <!-- SIDEBAR -->
        <aside class="sidebar">
            <div class="sidebar-label">Navegación</div>
"""
    for section_id, icon, label in NAV_SECTIONS:
        html += (
            f'            <button class="nav-item" data-section="{section_id}" '
            f'onclick="scrollToSection(\'{section_id}\')">'
            f'<i class="fas {icon}"></i> {label}</button>\n'
        )

    html += """            <div class="sidebar-note">
                <b>Convención de interpretación</b>
                Δ positivo indica incremento. Para balance hídrico (WB), valores más negativos representan mayor déficit.
            </div>
            <div style="flex:1"></div>
"""
    html += (
        f'            <div class="footer-note">&copy; {datetime.now().year} '
        f'Producto 1 · Balance Hídrico<br>Tablero técnico de evaluación climática</div>\n'
    )
    html += """        </aside>

        <!-- CONTENT AREA -->
        <main id="contentArea" class="content-area">
"""


    first = True





    for r_code in region_keys:


        r_info = active_regions[r_code]
        r_name = r_info['name']
        display_style = "block" if first else "none"
        first = False


        json_path = os.path.join(output_root, r_name, "24_Resumen_Ejecutivo", "key_numbers.json")
        data = load_key_numbers_json(json_path)


        def img(category, filename):
            return f"{r_name}/{category}/{filename}"

        base_period = (data or {}).get("base_period", "1981-2010")
        data_source_label = data_source or r_code

        html += f"""
            <div id="content-{r_code}" class="region-content" style="display: {display_style};">

                <!-- SECTION: RESUMEN EJECUTIVO -->
                <section id="resumen-{r_code}" class="section-container" data-section="resumen">
                    <div class="section-title"><i class="fas fa-clipboard-check"></i> Resumen Ejecutivo (Línea Base {base_period})</div>
                    <div class="section-subtitle">Síntesis de condiciones hidroclimáticas de referencia para <b>{r_name}</b>.</div>

                    <div class="science-callout">
                        <b><i class="fas fa-flask"></i> Marco metodológico</b>
                        <div class="science-grid">
                            <div><b>Región:</b> {r_name}</div>
                            <div><b>Período base:</b> {base_period}</div>
                            <div><b>Fuente climática:</b> {data_source_label}</div>
                            <div><b>Unidades:</b> P/PET/WB en mm/año; Temperatura en °C</div>
                        </div>
                    </div>

                    <!-- Key Metrics -->
                    <div class="metrics-row">
        """

        if data and "baseline" in data:
            b = data["baseline"]
            ai_val = _to_float(b.get("AI"))
            ai_for_scale = ai_val if ai_val is not None else 0.65
            cat_name, cat_color, cat_pct = get_ai_category(ai_for_scale)
            dry_days = b.get("Dry_Days", b.get("dry_days", "N/A"))

            html += f"""
                        <div class="kpi-card">
                            <div class="kpi-label">Precipitación</div>
                            <div class="kpi-value">{fmt_number((b.get('P_annual') or {}).get('mean'), 0)} <span style="font-size:0.92rem; font-weight:500">mm</span></div>
                            <div class="kpi-sub">σ = {fmt_number((b.get('P_annual') or {}).get('std'), 0)} mm</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Evapotranspiración</div>
                            <div class="kpi-value">{fmt_number((b.get('PET_annual') or {}).get('mean'), 0)} <span style="font-size:0.92rem; font-weight:500">mm</span></div>
                            <div class="kpi-sub">Demanda potencial atmosférica</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Balance Hídrico</div>
                            <div class="kpi-value">{fmt_number((b.get('WB_annual') or {}).get('mean'), 0)} <span style="font-size:0.92rem; font-weight:500">mm</span></div>
                            <div class="kpi-sub">Oferta neta (P - PET)</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Temperatura</div>
                            <div class="kpi-value">{fmt_number(b.get('Temp'), 1)}°C</div>
                            <div class="kpi-sub">Promedio anual</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Aridez (AI)</div>
                            <div class="kpi-value">{fmt_number(ai_val, 2)}</div>
                            <div class="ai-scale"><div class="ai-fill" style="width: {cat_pct}%; background-color: {cat_color};"></div></div>
                            <div class="ai-category" style="color: {cat_color};">{cat_name}</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Sequedad</div>
                            <div class="kpi-value">{fmt_number(dry_days, 0)} <span style="font-size:0.92rem; font-weight:500">días</span></div>
                            <div class="kpi-sub">CDD: {fmt_number(b.get('CDD'), 0)} días consecutivos máximos</div>
                        </div>
            """
        else:
            html += """
                        <div class="card full-width">
                            <div class="card-padding" style="color: #7f95a5;">
                                No se encontró <code>key_numbers.json</code> para esta región. Los gráficos se mantienen visibles, pero faltan KPIs resumidos.
                            </div>
                        </div>
            """

        html += f"""
                    </div>

                    <!-- Warming Stripes -->
                    <div class="card full-width" style="margin-bottom: 30px;">
                        <div class="card-header">
                            <span><i class="fas fa-temperature-high"></i> Evolución Histórica y Proyectada (Warming Stripes)</span>
                        </div>
                        <div class="img-wrapper img-contain" style="height: 220px;" onclick="openLightbox('{img('01_Series_Temporales_Temperatura', 'warming_stripes_anomalias.png')}')">
                            <img src="{img('01_Series_Temporales_Temperatura', 'warming_stripes_anomalias.png')}" loading="lazy">
                        </div>
                    </div>
                </section>

                <!-- SECTION: ESCENARIOS -->
                <section id="escenarios-{r_code}" class="section-container" data-section="escenarios">
                    <div class="section-title"><i class="fas fa-layer-group"></i> Análisis por Escenario</div>
                    <div class="section-subtitle">Comparación entre trayectorias de emisiones y su señal hidroclimática proyectada.</div>
                    <div class="scenario-legend">
                        <span class="legend-dot pos">Incremento (Δ positivo)</span>
                        <span class="legend-dot neg">Reducción / déficit (Δ negativo)</span>
                        <span>Horizontes: cercano 2021-2050, medio 2041-2070, tardío 2071-2100.</span>
                    </div>

                    <div class="scenario-tabs" id="scen-tabs-{r_code}">
        """
        for i, (scen_key, scen_label, scen_risk) in enumerate(SCENARIOS):
            active_class = " active" if i == 0 else ""
            html += (
                f'                        <button id="tab-{r_code}-{scen_key}" class="scen-tab{active_class}" '
                f'onclick="switchScenarioTab(\'{r_code}\', \'{scen_key}\')">{scen_label} ({scen_risk})</button>\n'
            )
        html += f"""
                    </div>

                    <div id="scen-container-{r_code}">
        """


        for i, (scen_key, scen_label, scen_risk) in enumerate(SCENARIOS):
            display = "block" if i == 0 else "none"


            table_rows = ""
            if data and "projections" in data:

                scen_data = data["projections"].get(scen_key, {})

                periods = ["2021-2050", "2041-2070", "2071-2100"]
                period_labels = ["Cercano (2021-2050)", "Medio (2041-2070)", "Tardío (2071-2100)"]

                for pid, plabel in zip(periods, period_labels):
                    p = scen_data.get(pid, {})
                    dWB_val = _to_float(p.get('delta_WB_mm'))
                    dWB = dWB_val if dWB_val is not None else 0.0
                    cls_wb = "val-neg" if dWB < 0 else "val-pos"

                    table_rows += f"""
                        <tr>
                            <td><b>{plabel}</b></td>
                            <td>{fmt_number(p.get('delta_Temp'), 1, signed=True, suffix='°C')}</td>
                            <td>{fmt_number(p.get('delta_P_mm'), 0, signed=True, suffix=' mm')} ({fmt_number(p.get('delta_P_pct'), 1, signed=True, suffix='%')})</td>
                            <td class="{cls_wb}">{fmt_number(dWB, 0, signed=True, suffix=' mm')} ({fmt_number(p.get('delta_WB_pct'), 1, signed=True, suffix='%')})</td>
                            <td>{fmt_number(p.get('delta_DryDays'), 0, signed=True, suffix=' días')}</td>
                            <td>{fmt_number(p.get('delta_CDD'), 0, signed=True, suffix=' días')}</td>
                        </tr>
                    """
            if not table_rows:
                table_rows = """
                        <tr>
                            <td colspan="6" style="color:#7f95a5;">No hay datos de proyección resumidos para este escenario.</td>
                        </tr>
                """


            bar_chart = img('09_Cambios_Balance_Hidrico', f'delta_WB_{scen_key}.png')
            monthly_dir = SCENARIO_MONTHLY_DELTA_DIR.get(scen_key, "21_Mapas_Mensuales_Delta_SSP126")
            map_near = img(monthly_dir, f'delta_WB_mensual_{scen_key}_cercano.png')
            map_mid = img(monthly_dir, f'delta_WB_mensual_{scen_key}_medio.png')
            map_late = img(monthly_dir, f'delta_WB_mensual_{scen_key}_tardio.png')

            html += f"""
                        <div id="scen-content-{r_code}-{scen_key}" class="scen-content" style="display: {display};">
                            <div class="dashboard-grid">
                                <!-- Evolution Table -->
                                <div class="card full-width">
                                    <div class="card-header">Evolución Temporal de Impactos ({scen_label} · Riesgo {scen_risk})</div>
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
                </section>

                <!-- SECTION: SERIES TEMPORALES -->
                <section id="series-{code}" class="section-container" data-section="series">
                    <div class="section-title"><i class="fas fa-chart-line"></i> Series Temporales (1980-2100)</div>
                    <div class="section-subtitle">Comportamiento temporal histórico-proyectado de variables clave.</div>

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
                </section>

                <!-- SECTION: ESTACIONALIDAD -->
                <section id="estacionalidad-{code}" class="section-container" data-section="estacionalidad">
                    <div class="section-title"><i class="fas fa-calendar-alt"></i> Ciclo Estacional y Cambios</div>
                    <div class="section-subtitle">Patrones intra-anuales y desplazamientos estacionales esperados.</div>

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
                </section>

                <!-- SECTION: MAPAS -->
                <section id="mapas-{code}" class="section-container" data-section="mapas">
                    <div class="section-title"><i class="fas fa-map-marked-alt"></i> Análisis Espacial de Impactos</div>
                    <div class="section-subtitle">Mapas sintéticos del horizonte tardío (2071-2100) bajo SSP5-8.5 para visualizar presiones máximas.</div>

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
                </section>

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
        </main> <!-- End Content Area -->
    </div> <!-- End Main Wrapper -->

    <!-- Lightbox -->
    <div id="lightbox" class="lightbox" onclick="closeLightbox()">
        <span class="lightbox-close">&times;</span>
        <img id="lightbox-img">
    </div>

</body>
</html>
"""

    output_path = os.path.join(output_root, "index.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Dashboard generado: {output_path}")


def export_static_site(output_root=None):
    """Copies the generated dashboard into the GitHub repository and pushes changes."""
    output_root = output_root or settings.OUTPUTS_DIR
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

    for item in os.listdir(output_root):
        src = os.path.join(output_root, item)
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

def run(deploy_to_github=False, data_source=None, output_root=None, region_codes=None, regions=None):
    """
    Generate dashboard HTML and optionally deploy to GitHub repo.
    Args:
        deploy_to_github: If True, copies outputs to FFLA_P1 repo and runs git commit/push.
                          Set to True only when you want to publish; leave False for local/exe use.
        data_source: 'FODESNA' or 'FMPLPT' to filter logos.
        output_root: Base folder where index.html and assets are written.
        region_codes: Optional region-code filter for dashboard content.
        regions: Optional region dictionary; defaults to settings.REGIONS.
    """
    generate_html_content(
        data_source=data_source,
        output_root=output_root,
        region_codes=region_codes,
        regions=regions,
    )
    if deploy_to_github or os.environ.get("DEPLOY_DASHBOARD", "").lower() in ("1", "true", "yes"):
        export_static_site(output_root=output_root)
    else:
        print("ℹ️ Dashboard generado localmente. Para publicar en GitHub, ejecuta con deploy_to_github=True o DEPLOY_DASHBOARD=1")

if __name__ == "__main__":
    run()

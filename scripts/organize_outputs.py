#!/usr/bin/env python3
"""
Script para organizar copias de las figuras en una estructura de carpetas limpia.
Adaptado para usar la configuración centralizada.
"""

import os
import shutil
from pathlib import Path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from organized.config import settings

# Estructura de carpetas organizadas
# Cada categoría tiene: nombre de carpeta destino, lista de (archivo origen, nombre descriptivo)
FOLDER_STRUCTURE = {
    "01_Series_Temporales_Temperatura": {
        "description": "Series temporales de temperatura (1980-2100)",
        "files": [
            ("figs/ann_ts_tas_1980_2100.png", "temperatura_media_anual.png"),
            ("figs/ann_ts_tasmax_1980_2100.png", "temperatura_maxima_anual.png"),
            ("figs/ann_ts_tasmin_1980_2100.png", "temperatura_minima_anual.png"),
            ("figs/warming_stripes_1981_2010.png", "warming_stripes_anomalias.png"),
        ]
    },
    "02_Series_Temporales_Hidrologicas": {
        "description": "Series temporales de variables hidrológicas (1980-2100)",
        "files": [
            ("figs/ann_timeseries_p_1980_2100.png", "precipitacion_anual.png"),
            ("figs/ann_timeseries_pet_1980_2100.png", "evapotranspiracion_anual.png"),
            ("figs/ann_timeseries_wb_1980_2100.png", "balance_hidrico_anual.png"),
        ]
    },
    "03_Indicadores_Sequia": {
        "description": "Indicadores de sequía y aridez",
        "files": [
            ("figs/timeseries_ai.png", "indice_aridez_serie_temporal.png"),
            ("figs/timeseries_cdd.png", "dias_secos_consecutivos_serie_temporal.png"),
        ]
    },
    "04_Climatologia_Mensual_Comparativa": {
        "description": "Comparación ciclo anual base vs futuro",
        "files": [
            ("figs/seasonal_p_1981_2010_2071_2100.png", "ciclo_anual_precipitacion.png"),
            ("figs/seasonal_pet_1981_2010_2071_2100.png", "ciclo_anual_evapotranspiracion.png"),
            ("figs/seasonal_wb_1981_2010_2071_2100.png", "ciclo_anual_balance_hidrico.png"),
        ]
    },
    "05_Climatologia_Mensual_Precipitacion": {
        "description": "Climatología mensual de precipitación por ventana temporal",
        "files": [
            ("Deliverables/timeseries/clim_mensual_p_1981-2010.png", "base_1981-2010.png"),
            ("Deliverables/timeseries/clim_mensual_p_2021-2050.png", "cercano_2021-2050.png"),
            ("Deliverables/timeseries/clim_mensual_p_2041-2070.png", "medio_2041-2070.png"),
            ("Deliverables/timeseries/clim_mensual_p_2071-2100.png", "tardio_2071-2100.png"),
        ]
    },
    "06_Climatologia_Mensual_Evapotranspiracion": {
        "description": "Climatología mensual de evapotranspiración por ventana temporal",
        "files": [
            ("Deliverables/timeseries/clim_mensual_pet_1981-2010.png", "base_1981-2010.png"),
            ("Deliverables/timeseries/clim_mensual_pet_2021-2050.png", "cercano_2021-2050.png"),
            ("Deliverables/timeseries/clim_mensual_pet_2041-2070.png", "medio_2041-2070.png"),
            ("Deliverables/timeseries/clim_mensual_pet_2071-2100.png", "tardio_2071-2100.png"),
        ]
    },
    "07_Climatologia_Mensual_Balance_Hidrico": {
        "description": "Climatología mensual de balance hídrico por ventana temporal",
        "files": [
            ("Deliverables/timeseries/clim_mensual_wb_1981-2010.png", "base_1981-2010.png"),
            ("Deliverables/timeseries/clim_mensual_wb_2021-2050.png", "cercano_2021-2050.png"),
            ("Deliverables/timeseries/clim_mensual_wb_2041-2070.png", "medio_2041-2070.png"),
            ("Deliverables/timeseries/clim_mensual_wb_2071-2100.png", "tardio_2071-2100.png"),
        ]
    },
    "08_Barras_por_Ventana_Temporal": {
        "description": "Valores anuales por ventana temporal y escenario",
        "files": [
            ("figs/bars_p.png", "precipitacion_por_ventana.png"),
            ("figs/bars_pet.png", "evapotranspiracion_por_ventana.png"),
            ("figs/bars_wb.png", "balance_hidrico_por_ventana.png"),
        ]
    },
    "09_Cambios_Balance_Hidrico": {
        "description": "Cambios en balance hídrico por escenario (delta vs base)",
        "files": [
            ("Deliverables/bars/bars_deltaWB_ssp126_ecuador.png", "delta_WB_ssp126.png"),
            ("Deliverables/bars/bars_deltaWB_ssp370_ecuador.png", "delta_WB_ssp370.png"),
            ("Deliverables/bars/bars_deltaWB_ssp585_ecuador.png", "delta_WB_ssp585.png"),
        ]
    },
    "10_Mapas_Componentes_Base": {
        "description": "Mapas espaciales - Período base (1981-2010)",
        "files": [
            ("Deliverables/maps/componentes_base.png", "climatologia_base_P_PET_WB.png"),
        ]
    },
    "11_Mapas_Cambios_Precipitacion": {
        "description": "Mapas de cambios en precipitación (delta vs base)",
        "files": [
            ("Deliverables/maps/delta_p_2021-2040.png", "delta_P_cercano_2021-2040.png"),
            ("Deliverables/maps/delta_p_2041-2070.png", "delta_P_medio_2041-2070.png"),
            ("Deliverables/maps/delta_p_2071-2100.png", "delta_P_tardio_2071-2100.png"),
        ]
    },
    "12_Mapas_Cambios_Evapotranspiracion": {
        "description": "Mapas de cambios en evapotranspiración (delta vs base)",
        "files": [
            ("Deliverables/maps/delta_pet_2021-2040.png", "delta_PET_cercano_2021-2040.png"),
            ("Deliverables/maps/delta_pet_2041-2070.png", "delta_PET_medio_2041-2070.png"),
            ("Deliverables/maps/delta_pet_2071-2100.png", "delta_PET_tardio_2071-2100.png"),
        ]
    },
    "13_Mapas_Cambios_Balance_Hidrico": {
        "description": "Mapas de cambios en balance hídrico (delta vs base)",
        "files": [
            ("Deliverables/maps/delta_wb_2021-2040.png", "delta_WB_cercano_2021-2040.png"),
            ("Deliverables/maps/delta_wb_2041-2070.png", "delta_WB_medio_2041-2070.png"),
            ("Deliverables/maps/delta_wb_2071-2100.png", "delta_WB_tardio_2071-2100.png"),
        ]
    },
    "14_Matriz_MultiVentana": {
        "description": "Matriz de balance hídrico por escenario y ventana temporal",
        "files": [
            ("figs/wb_maps_windows.png", "matriz_WB_escenarios_ventanas.png"),
        ]
    },
    "15_Trimestres_Base": {
        "description": "Análisis estacional - Trimestres húmedo y seco base",
        "files": [
            ("Deliverables/maps/wb_trimestres_base.png", "WB_trimestres_base_1981-2010.png"),
        ]
    },
    "16_Trimestres_Cambios": {
        "description": "Cambios en trimestres por escenario",
        "files": [
            ("Deliverables/maps/delta_trimestres_ssp126_ecuador.png", "delta_trimestres_ssp126.png"),
            ("Deliverables/maps/delta_trimestres_ssp370_ecuador.png", "delta_trimestres_ssp370.png"),
            ("Deliverables/maps/delta_trimestres_ssp585_ecuador.png", "delta_trimestres_ssp585.png"),
        ]
    },
    "17_Mapas_Mensuales_Historico": {
        "description": "Mapas mensuales de balance hídrico - Período base",
        "files": [
            ("maps/WB_mensual_historical_ecuador_Base_1981-2010.png", "WB_mensual_historico_base.png"),
        ]
    },
    "18_Mapas_Mensuales_SSP126": {
        "description": "Mapas mensuales de balance hídrico - SSP1-2.6",
        "files": [
            ("maps/WB_mensual_ssp126_ecuador_Cercano_2021-2040.png", "WB_mensual_ssp126_cercano.png"),
            ("maps/WB_mensual_ssp126_ecuador_Medio_2041-2070.png", "WB_mensual_ssp126_medio.png"),
            ("maps/WB_mensual_ssp126_ecuador_Tardío_2071-2100.png", "WB_mensual_ssp126_tardio.png"),
        ]
    },
    "19_Mapas_Mensuales_SSP370": {
        "description": "Mapas mensuales de balance hídrico - SSP3-7.0",
        "files": [
            ("maps/WB_mensual_ssp370_ecuador_Cercano_2021-2040.png", "WB_mensual_ssp370_cercano.png"),
            ("maps/WB_mensual_ssp370_ecuador_Medio_2041-2070.png", "WB_mensual_ssp370_medio.png"),
            ("maps/WB_mensual_ssp370_ecuador_Tardío_2071-2100.png", "WB_mensual_ssp370_tardio.png"),
        ]
    },
    "20_Mapas_Mensuales_SSP585": {
        "description": "Mapas mensuales de balance hídrico - SSP5-8.5",
        "files": [
            ("maps/WB_mensual_ssp585_ecuador_Cercano_2021-2040.png", "WB_mensual_ssp585_cercano.png"),
            ("maps/WB_mensual_ssp585_ecuador_Medio_2041-2070.png", "WB_mensual_ssp585_medio.png"),
            ("maps/WB_mensual_ssp585_ecuador_Tardío_2071-2100.png", "WB_mensual_ssp585_tardio.png"),
        ]
    },
    "21_Mapas_Mensuales_Delta_SSP126": {
        "description": "Mapas mensuales de cambios - SSP1-2.6 (delta vs base)",
        "files": [
            ("maps/WB_mensual_delta_ssp126_ecuador_Cercano_2021-2040.png", "delta_WB_mensual_ssp126_cercano.png"),
            ("maps/WB_mensual_delta_ssp126_ecuador_Medio_2041-2070.png", "delta_WB_mensual_ssp126_medio.png"),
            ("maps/WB_mensual_delta_ssp126_ecuador_Tardío_2071-2100.png", "delta_WB_mensual_ssp126_tardio.png"),
        ]
    },
    "22_Mapas_Mensuales_Delta_SSP370": {
        "description": "Mapas mensuales de cambios - SSP3-7.0 (delta vs base)",
        "files": [
            ("maps/WB_mensual_delta_ssp370_ecuador_Cercano_2021-2040.png", "delta_WB_mensual_ssp370_cercano.png"),
            ("maps/WB_mensual_delta_ssp370_ecuador_Medio_2041-2070.png", "delta_WB_mensual_ssp370_medio.png"),
            ("maps/WB_mensual_delta_ssp370_ecuador_Tardío_2071-2100.png", "delta_WB_mensual_ssp370_tardio.png"),
        ]
    },
    "23_Mapas_Mensuales_Delta_SSP585": {
        "description": "Mapas mensuales de cambios - SSP5-8.5 (delta vs base)",
        "files": [
            ("maps/WB_mensual_delta_ssp585_ecuador_Cercano_2021-2040.png", "delta_WB_mensual_ssp585_cercano.png"),
            ("maps/WB_mensual_delta_ssp585_ecuador_Medio_2041-2070.png", "delta_WB_mensual_ssp585_medio.png"),
            ("maps/WB_mensual_delta_ssp585_ecuador_Tardío_2071-2100.png", "delta_WB_mensual_ssp585_tardio.png"),
        ]
    },
    "24_Resumen_Ejecutivo": {
        "description": "Números clave y resumen ejecutivo",
        "files": [
            ("Deliverables/master/key_numbers.txt", "key_numbers.txt"),
            ("Deliverables/master/key_numbers.json", "key_numbers.json"),
        ]
    },
}


def create_readme(folder_path, description):
    """Crea un archivo README en cada carpeta con descripción."""
    readme_path = os.path.join(folder_path, "README.txt")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f"{description}\n")
        f.write(f"\n")
        f.write(f"Carpeta creada automáticamente por el sistema organizado.\n")
        f.write(f"Parte del sistema de organización de figuras de cambio climático\n")


def run():
    """Organiza todas las figuras en carpetas estructuradas."""
    output_dir = settings.OUTPUTS_DIR
    print("="*70)
    print("ORGANIZADOR DE FIGURAS - ANÁLISIS DE CAMBIO CLIMÁTICO")
    print("="*70)
    print(f"\nDirectorio de salida: {output_dir}\n")
    
    # Crear directorio principal de salida
    os.makedirs(output_dir, exist_ok=True)
    
    # Crear README principal
    main_readme = os.path.join(output_dir, "README.txt")
    with open(main_readme, 'w', encoding='utf-8') as f:
        f.write("FIGURAS ORGANIZADAS - ANÁLISIS DE CAMBIO CLIMÁTICO\n")
        f.write("="*60 + "\n\n")
        f.write("Esta carpeta contiene copias organizadas de todas las figuras\n")
        f.write("generadas en el análisis de cambio climático.\n\n")
        f.write("ESTRUCTURA:\n")
        for region_code, region_info in settings.REGIONS.items():
            f.write(f"- {region_info['name']}/: Figuras para {region_info['name']}\n")
        f.write("\nCada región tiene categorías organizadas por tipo de análisis.\n\n")
        f.write("Generado automáticamente.\n")
    
    # Estadísticas
    total_files_copied = 0
    total_files_missing = 0
    
    # Procesar cada región
    for region_code, region_info in settings.REGIONS.items():
        region_name = region_info["name"]
        # The issue was here: source_dir was settings.REGIONS["path"] which is .../organized/inputs/FDAT
        # But figures are generated into .../organized/inputs/FDAT/figs/ or .../organized/inputs/FDAT/Deliverables/
        # The relative paths in FOLDER_STRUCTURE (e.g. "figs/...") expect source_dir to be the region root.
        # We need to make sure source_dir is correct.
        source_dir = region_info["path"] 
        
        region_output = os.path.join(output_dir, region_name)
        
        print(f"\n{'='*70}")
        print(f"🌍 REGIÓN: {region_name}")
        print(f"   Origen: {source_dir}")
        print(f"{'='*70}")
        
        # Crear carpeta de región
        os.makedirs(region_output, exist_ok=True)
        
        region_copied = 0
        region_missing = 0
        
        # Procesar cada categoría
        for folder_name, folder_info in FOLDER_STRUCTURE.items():
            description = folder_info["description"]
            files_list = folder_info["files"]
            
            # Crear carpeta de categoría
            category_path = os.path.join(region_output, folder_name)
            os.makedirs(category_path, exist_ok=True)
            
            # Crear README en la carpeta
            create_readme(category_path, description)
            
            print(f"\n  📂 {folder_name}")
            print(f"     {description}")
            
            # Copiar archivos
            for source_file, dest_name in files_list:
                # The source file is relative to the region root (e.g., "figs/my_plot.png")
                source_path = os.path.join(source_dir, source_file)
                dest_path = os.path.join(category_path, dest_name)
                
                if os.path.exists(source_path):
                    try:
                        shutil.copy2(source_path, dest_path)
                        print(f"     ✅ {dest_name}")
                        region_copied += 1
                        total_files_copied += 1
                    except Exception as e:
                        print(f"     ⚠️  Error copiando {dest_name}: {e}")
                        region_missing += 1
                        total_files_missing += 1
                else:
                    print(f"     ❌ No encontrado: {source_path}")
                    region_missing += 1
                    total_files_missing += 1
        
        # Resumen regional
        print(f"\n  📊 Resumen {region_name}:")
        print(f"     Copiados: {region_copied}")
        print(f"     Faltantes: {region_missing}")
    
    # Resumen final
    print(f"\n{'='*70}")
    print(f"✅ PROCESO COMPLETADO")
    print(f"{'='*70}")
    print(f"\n📊 ESTADÍSTICAS TOTALES:")
    print(f"   Archivos copiados: {total_files_copied}")
    print(f"   Archivos faltantes: {total_files_missing}")
    print(f"   Total esperado: {total_files_copied + total_files_missing}")
    print(f"\n📁 Carpeta de salida: {output_dir}")


def create_index_html():
    """Crea un índice HTML para navegación visual (opcional)."""
    output_dir = settings.OUTPUTS_DIR
    index_path = os.path.join(output_dir, "index.html")
    
    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Índice de Figuras - Cambio Climático</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #003366;
            border-bottom: 3px solid #003366;
            padding-bottom: 10px;
        }
        h2 {
            color: #0066cc;
            margin-top: 30px;
        }
        .region {
            background-color: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .category {
            margin: 15px 0;
            padding: 10px;
            background-color: #f9f9f9;
            border-left: 4px solid #0066cc;
        }
        .category-title {
            font-weight: bold;
            color: #003366;
        }
        .description {
            color: #666;
            font-style: italic;
            margin: 5px 0;
        }
        .folder-link {
            display: inline-block;
            margin: 5px 0;
            padding: 5px 10px;
            background-color: #0066cc;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }
        .folder-link:hover {
            background-color: #004080;
        }
    </style>
</head>
<body>
    <h1>📊 Índice de Figuras - Análisis de Cambio Climático</h1>
    <p><strong>Período de análisis:</strong> 1980-2100 | <strong>Período base:</strong> 1981-2010</p>
"""
    
    for region_code, region_info in settings.REGIONS.items():
        region_name = region_info["name"]
        html_content += f"""
    <div class="region">
        <h2>🌍 {region_name}</h2>
"""
        for folder_name, folder_info in FOLDER_STRUCTURE.items():
            description = folder_info["description"]
            html_content += f"""
        <div class="category">
            <div class="category-title">{folder_name}</div>
            <div class="description">{description}</div>
            <a href="{region_name}/{folder_name}/" class="folder-link">Abrir carpeta →</a>
        </div>
"""
        html_content += "    </div>\n"
    
    html_content += """
    <div style="text-align: center; margin-top: 40px; color: #666;">
        <p>Generado automáticamente.</p>
    </div>
</body>
</html>
"""
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"📄 Índice HTML creado: {index_path}")


if __name__ == "__main__":
    try:
        run()
        create_index_html()
        print("\n🎉 ¡Organización completada exitosamente!\n")
    except Exception as e:
        print(f"\n❌ Error durante la organización:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()

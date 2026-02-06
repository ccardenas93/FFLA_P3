#!/usr/bin/env python3
"""
Script para exportar Water Balance como archivos TIFF para períodos específicos.
Períodos: 2020-2040, 2040-2060, 2060-2080, 2080-2100
"""

import os
import sys
import xarray as xr
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from organized.config import settings

# Try to import rioxarray for GeoTIFF export
try:
    import rioxarray
except ImportError:
    rioxarray = None

# Períodos específicos solicitados
PERIODOS_ESPECIFICOS = {
    "2020-2040": ("2020-01-01", "2040-12-31"),
    "2040-2060": ("2040-01-01", "2060-12-31"),
    "2060-2080": ("2060-01-01", "2080-12-31"),
    "2080-2100": ("2080-01-01", "2100-12-31"),
}

# Solo procesar escenarios futuros (no historical)
SCENARIOS_FUTUROS = [d for d in settings.DOMAINS if "historical" not in d]


def export_wb_tif(root_dir, dominio, periodo_nombre, t0, t1):
    """
    Exporta Water Balance agregado anual como TIFF para un período específico.
    
    Args:
        root_dir: Directorio raíz de la región
        dominio: Nombre del dominio (ej: ssp126_ecuador)
        periodo_nombre: Nombre del período (ej: "2020-2040")
        t0: Fecha inicio (ej: "2020-01-01")
        t1: Fecha fin (ej: "2040-12-31")
    """
    base_path = os.path.join(root_dir, dominio)
    
    # Buscar archivo de water balance
    wb_file = os.path.join(base_path, f'wb_{dominio}.nc')
    if not os.path.exists(wb_file):
        wb_file_alt = os.path.join(base_path, 'wb.nc')
        if os.path.exists(wb_file_alt):
            wb_file = wb_file_alt
        else:
            print(f'    ⚠️ Archivo WB no encontrado para {dominio} en {base_path}')
            return False
    
    try:
        # Abrir dataset
        ds = xr.open_dataset(wb_file)
        
        # Verificar que tiene la variable wb_mmday
        if 'wb_mmday' not in ds:
            print(f'    ⚠️ Variable wb_mmday no encontrada en {wb_file}')
            return False
        
        # Seleccionar período temporal
        wb = ds['wb_mmday'].sel(time=slice(t0, t1))
        
        if wb.sizes.get('time', 0) == 0:
            print(f'    ⚠️ No hay datos en el período {t0} a {t1} para {dominio}')
            return False
        
        # Agregar: suma anual de WB (mm/año)
        # Primero convertir de mm/día a mm/año sumando por año
        wb_anual = wb.resample(time='YS').sum('time')  # Suma por año
        # Promedio de todos los años en el período
        wb_promedio = wb_anual.mean('time')  # mm/año promedio
        
        # Preparar para exportar como GeoTIFF
        # Asegurar que tiene coordenadas lat/lon
        if 'lat' not in wb_promedio.coords or 'lon' not in wb_promedio.coords:
            print(f'    ⚠️ Coordenadas lat/lon no encontradas en {dominio}')
            return False
        
        # Crear carpeta de salida
        output_dir = os.path.join(root_dir, 'tifs_periodos_especificos')
        os.makedirs(output_dir, exist_ok=True)
        
        # Nombre del archivo de salida
        nombre_archivo = f'wb_{dominio}_{periodo_nombre}.tif'
        output_path = os.path.join(output_dir, nombre_archivo)
        
        # Exportar como GeoTIFF usando rioxarray
        if rioxarray is None:
            raise ImportError("rioxarray no está instalado. Ejecute: pip install rioxarray")
        
        # Preparar DataArray para exportación
        # Asegurar que tiene CRS EPSG:4326 (WGS84)
        if not hasattr(wb_promedio, 'rio'):
            wb_promedio = wb_promedio.rio.write_crs("EPSG:4326")
        elif wb_promedio.rio.crs is None:
            wb_promedio = wb_promedio.rio.write_crs("EPSG:4326")
        
        # Renombrar dimensiones para rioxarray (necesita 'y' y 'x' en lugar de 'lat' y 'lon')
        if 'lat' in wb_promedio.dims and 'lon' in wb_promedio.dims:
            wb_promedio = wb_promedio.rename({'lat': 'y', 'lon': 'x'})
        
        # Asegurar orden correcto de dimensiones (y, x)
        if 'y' in wb_promedio.dims and 'x' in wb_promedio.dims:
            # Ordenar por latitud descendente (N a S) para compatibilidad con GeoTIFF
            wb_promedio = wb_promedio.sortby('y', ascending=False)
        
        # Exportar como GeoTIFF
        wb_promedio.rio.to_raster(output_path, driver='GTiff')
        
        print(f'    ✅ Exportado: {nombre_archivo}')
        return True
        
    except ImportError as e:
        print(f'    ⚠️ rioxarray no está instalado.')
        print(f'    Por favor ejecute: pip install rioxarray')
        return False
    except Exception as e:
        print(f'    ❌ Error exportando {dominio} período {periodo_nombre}: {e}')
        import traceback
        traceback.print_exc()
        return False


def process_region(root_dir):
    """
    Procesa una región completa, exportando TIFFs para todos los períodos y escenarios.
    """
    print(f"\nProcesando región: {root_dir}")
    
    total_exportados = 0
    total_fallidos = 0
    
    for dominio in SCENARIOS_FUTUROS:
        print(f"\n  Dominio: {dominio}")
        
        for periodo_nombre, (t0, t1) in PERIODOS_ESPECIFICOS.items():
            if export_wb_tif(root_dir, dominio, periodo_nombre, t0, t1):
                total_exportados += 1
            else:
                total_fallidos += 1
    
    print(f"\n  📊 Resumen:")
    print(f"     Exportados: {total_exportados}")
    print(f"     Fallidos: {total_fallidos}")
    
    return total_exportados, total_fallidos


def run(target_dirs=None):
    """
    Ejecuta la exportación de TIFFs para períodos específicos.
    
    Args:
        target_dirs: Lista de directorios a procesar. Si None, usa las regiones configuradas.
    """
    print("\n" + "="*80)
    print("EXPORTACIÓN DE WATER BALANCE A TIFF - PERÍODOS ESPECÍFICOS")
    print("="*80)
    print("\nPeríodos a procesar:")
    for periodo, (t0, t1) in PERIODOS_ESPECIFICOS.items():
        print(f"  - {periodo}: {t0} a {t1}")
    print()
    
    if target_dirs is None:
        dirs_to_process = [settings.get_region_output_dir(code) for code in settings.REGIONS]
    else:
        dirs_to_process = target_dirs
    
    print(f"Directorios a procesar: {dirs_to_process}\n")
    
    total_exportados = 0
    total_fallidos = 0
    
    for root_dir in dirs_to_process:
        if not os.path.exists(root_dir):
            print(f"⚠️ Directorio no encontrado: {root_dir}")
            continue
        
        exportados, fallidos = process_region(root_dir)
        total_exportados += exportados
        total_fallidos += fallidos
    
    print("\n" + "="*80)
    print("EXPORTACIÓN COMPLETADA")
    print("="*80)
    print(f"\n📊 ESTADÍSTICAS TOTALES:")
    print(f"   Archivos TIFF exportados: {total_exportados}")
    print(f"   Archivos fallidos: {total_fallidos}")
    print(f"\nLos archivos se encuentran en: tifs_periodos_especificos/ dentro de cada región\n")


if __name__ == "__main__":
    run()


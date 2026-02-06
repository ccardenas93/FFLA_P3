import streamlit as st
import os
import sys
import tempfile
import zipfile
import shutil
import geopandas as gpd
import folium
from streamlit_folium import st_folium

# Add PARENT dir to path to import 'organized' package
current_dir = os.path.dirname(os.path.abspath(__file__))

# PATCH: Make "organized" importable even if folder is named "FFLA_P3-master"
import types
if "organized" not in sys.modules:
    # Use current directory (where app.py is) as the "organized" package
    organized_pkg = types.ModuleType("organized")
    organized_pkg.__path__ = [current_dir]
    sys.modules["organized"] = organized_pkg

parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from organized.config import settings
from organized.scripts import clip_inputs, download_data
from organized.scripts.wb import compute_pet, water_balance

st.set_page_config(page_title="Climate Analysis App", layout="wide")

st.title("🌍 Análisis Climático FFLA")

# Sidebar
st.sidebar.header("Configuración")

st.sidebar.subheader("📦 Datos Base")
if st.sidebar.button("Descargar/Actualizar Datos Base"):
    with st.spinner("Descargando datos del repositorio (esto puede tardar)..."):
        try:
            download_data.run(base_dir=parent_dir)
            st.sidebar.success("✅ Datos descargados/verificados.")
        except Exception as e:
            st.sidebar.error(f"Error en descarga: {e}")

mode = st.sidebar.radio("Modo de Operación", ["Seleccionar Región Existente", "Nueva Área de Interés (Subir SHP/GPKG)"])

def save_uploaded_file(uploaded_file):
    """Saves uploaded file to a temp dir and returns the path."""
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path, temp_dir

def handle_zip(zip_path, extract_to):
    """Extracts zip and returns the path to the first .shp found."""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    # Find .shp
    for root, dirs, files in os.walk(extract_to):
        for file in files:
            if file.endswith(".shp"):
                return os.path.join(root, file)
    return None

if mode == "Nueva Área de Interés (Subir SHP/GPKG)":
    st.write("### 📤 Cargar Área de Estudio")
    st.info("Sube un archivo **.gpkg** o un **.zip** que contenga un Shapefile (.shp, .shx, .dbf, etc).")
    
    uploaded_file = st.file_uploader("Seleccionar archivo", type=["zip", "gpkg"])
    
    if uploaded_file:
        with st.spinner("Procesando archivo..."):
            file_path, temp_dir = save_uploaded_file(uploaded_file)
            
            shp_path = None
            if uploaded_file.name.endswith(".zip"):
                shp_path = handle_zip(file_path, temp_dir)
            else:
                shp_path = file_path
                
            if shp_path:
                try:
                    gdf = gpd.read_file(shp_path)
                    
                    # Ensure EPSG:4326
                    if gdf.crs.to_epsg() != 4326:
                        gdf = gdf.to_crs("EPSG:4326")
                        
                    st.success("✅ Geometría cargada correctamente.")
                    
                    # Preview Map
                    # Reproject to projected CRS for centroid to avoid warning
                    gdf_proj = gdf.to_crs(epsg=3857)
                    centroid = gdf_proj.geometry.centroid.to_crs(epsg=4326)
                    m = folium.Map(location=[centroid.y.mean(), centroid.x.mean()], zoom_start=8)
                    folium.GeoJson(gdf).add_to(m)
                    st_folium(m, width=700, height=400)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        region_name = st.text_input("Nombre del Área (para carpeta)", value="Mi_Area")
                    with col2:
                        custom_out = st.text_input("Carpeta de Resultados (Opcional)", placeholder="Dejar vacío para usar default")
                    
                    if st.button("🚀 Ejecutar Análisis", type="primary"):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # 1. Clip Inputs
                        status_text.text("Recortando datos climáticos... (Esto puede tardar unos minutos)")
                        # Pass settings.BASE_DIR explicitly so it searches inside inputs/ correctly
                        # clip_inputs logic searches in source_dir/FODESNA etc.
                        # We want it to look at organized/inputs/FODESNA if we downloaded there.
                        # So let's pass os.path.join(settings.BASE_DIR, 'inputs') as source ??
                        # No, clip_inputs searches `source_dir`, `source_dir/inputs`, `source_dir/FODESNA`...
                        # If we downloaded to `organized/inputs/FODESNA`, then `organized/inputs` is the "root" of that structure?
                        # ACTUALLY: The download script puts it in `organized/inputs/FODESNA`.
                        # Clip inputs search logic:
                        # search_dirs = [source, source/FDAT, source/FODESNA, source/inputs]
                        # If we pass source=settings.BASE_DIR (organized/), it checks:
                        # 1. organized/FODESNA -> NO (it's in inputs)
                        # 2. organized/inputs -> YES (contains FODESNA?) 
                        # Wait, if `organized/inputs/FODESNA/historical_ecuador` exists.
                        # And we look for domain `historical_ecuador`.
                        # It checks `organized/inputs/historical_ecuador` -> No.
                        # It checks `organized/inputs/FODESNA/historical_ecuador`? 
                        # Only if we explicitly add that path to search logic in clip_inputs.
                        
                        # Let's fix searching logic by passing the inputs dir as source, OR updating clip_inputs to search defaults.
                        # It's better to update clip_inputs to search recursively or specifically in inputs/FODESNA.
                        # For now, let's pass the inputs path where we know data is.
                        search_source = os.path.join(settings.BASE_DIR, "inputs")
                        
                        region_inputs_dir = clip_inputs.process_region(region_name, shp_path, source_dir=search_source)
                        progress_bar.progress(30)
                        
                        # 2. Register Region
                        final_out_path = custom_out if custom_out.strip() else None
                        
                        # LOGIC FIX: User wants EVERYTHING in the custom folder.
                        # By default, settings.OUTPUTS_DIR is global. The region output is a subfolder.
                        # If user gives a custom path, we treat that as the "root" for this run?
                        # Or as the region folder?
                        # Usually "Carpeta de Resultados" implies the container.
                        # If user picks "C:/Proyectos/Analisis1", we want:
                        #   C:/Proyectos/Analisis1/Mi_Area/... (Data)
                        #   C:/Proyectos/Analisis1/Reporte.docx
                        #   C:/Proyectos/Analisis1/index.html
                        
                        if final_out_path:
                            # Verify existence or create
                            os.makedirs(final_out_path, exist_ok=True)
                            
                            # Overwrite global settings in memory so reports/dashboard go there
                            settings.OUTPUTS_DIR = final_out_path
                            settings.REPORTS_DIR = final_out_path
                            
                            # Region output will be a subfolder of this custom root
                            region_out_path = os.path.join(final_out_path, region_name)
                        else:
                            # Default behavior
                            region_out_path = None # add_dynamic_region handles default (OUTPUTS_DIR/name)
                        
                        region_code = settings.add_dynamic_region(region_name, region_inputs_dir, shp_path, output_path=region_out_path)
                        output_dir = settings.get_region_output_dir(region_code)
                        
                        region_pair = [(region_inputs_dir, output_dir)]
                        
                        # 3. Calculations
                        status_text.text("Calculando PET...")
                        compute_pet.run(region_pairs=region_pair)
                        progress_bar.progress(50)
                        
                        status_text.text("Calculando Balance Hídrico...")
                        water_balance.run(region_pairs=region_pair)
                        progress_bar.progress(70)
                        
                        # 4. Plotting (Integrated)
                        status_text.text("Generando Gráficos (esto tarda un poco)...")
                        # Importing here to ensure it uses the updated inputs/settings
                        from organized.scripts import generate_plots, generate_dashboard, generate_report
                        try:
                            # generate_plots runs for ALL regions in settings.REGIONS
                            # Since we added our dynamic region to settings.REGIONS, it should run for it.
                            # UPDATE: Pass explicit region code to avoid processing FDAT/FODESNA if they don't exist
                            target_regions = [region_code]
                            
                            # Temporarily backup REGIONS to ensure low-level scripts that don't take args 
                            # only see our region (hacky but effective for legacy scripts)
                            original_regions = settings.REGIONS.copy()
                            # Filter settings.REGIONS to only include our target
                            settings.REGIONS = {k: v for k, v in settings.REGIONS.items() if k in target_regions}
                            
                            try:
                                generate_plots.run(region_codes=target_regions) 
                                progress_bar.progress(85)
                                
                                status_text.text("Generando Reporte y Dashboard...")
                                # Dashboard usually generates for all, but with modified settings it should be fine
                                generate_dashboard.run()
                                doc_path = generate_report.create_document(specific_regions=target_regions)
                            finally:
                                # Restore
                                settings.REGIONS = original_regions
                                
                            progress_bar.progress(100)
                            
                            st.success(f"¡Análisis Completo! Resultados en: `{output_dir}`")
                            st.info(f"Reporte Word generado: `{doc_path}`")
                            
                        except Exception as e:
                            st.error(f"Error generando gráficos/reporte: {e}")
                            st.warning("Los cálculos numéricos (NetCDF) sí se completaron.")
                            import traceback
                            st.code(traceback.format_exc())
                        
                        status_text.text("¡Completado!")
                        
                        # Show some results if available?
                        st.write("---")
                        st.write("#### Resultados Generados")
                        if os.path.exists(output_dir):
                            st.write(f"Carpeta: {output_dir}")
                            # files = os.listdir(output_dir)
                            # st.write(files) (Too many files to list)
                            
                            # Link to dashboard
                            dash_path = os.path.join(settings.OUTPUTS_DIR, "index.html")
                            st.markdown(f"**[Abrir Dashboard HTML]({dash_path})** (Click derecho -> Abrir localmente)")
                        
                except Exception as e:
                    st.error(f"Error leyendo el archivo: {e}")
                    import traceback
                    st.code(traceback.format_exc())
            else:
                st.error("No se encontró un archivo .shp válido dentro del ZIP.")

elif mode == "Seleccionar Región Existente":
    st.write("### 📂 Regiones Disponibles")
    selected_region = st.selectbox("Región", list(settings.REGIONS.keys()))
    
    if st.button("Ver Resultados / Procesar"):
        st.write(f"Mostrando datos para: {settings.REGIONS[selected_region]['name']}")
        # Here we could implement visualization of existing outputs

import streamlit as st
import os
import sys
import tempfile
import zipfile
import shutil
import geopandas as gpd
import folium
from streamlit_folium import st_folium

current_dir = os.path.dirname(os.path.abspath(__file__))

import types
if "organized" not in sys.modules:
    organized_pkg = types.ModuleType("organized")
    organized_pkg.__path__ = [current_dir]
    sys.modules["organized"] = organized_pkg

    sys.modules["organized"] = organized_pkg

from organized.config import settings
from organized.scripts import clip_inputs, download_data
from organized.scripts.wb import compute_pet, water_balance

st.set_page_config(page_title="Climate Analysis App", layout="wide")

st.title("🌍 Análisis Climático FFLA")


st.sidebar.header("Configuración")

st.sidebar.subheader("📦 Datos Base")
if st.sidebar.button("Descargar/Actualizar Datos Base"):
    with st.spinner("Descargando datos del repositorio (esto puede tardar)..."):
        try:

            download_data.run(base_dir=current_dir)
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


                    if gdf.crs.to_epsg() != 4326:
                        gdf = gdf.to_crs("EPSG:4326")

                    st.success("✅ Geometría cargada correctamente.")



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

                    st.write("---")
                    data_source_opt = st.radio(
                        "📡 Fuente de Datos Climáticos",
                        ["FODESNA", "FMPLPT"],
                        help="Seleccione el conjunto de datos a utilizar. FODESNA para la provincia de Napo. FMPLPT para la provincia de Tungurahua."
                    )
                    st.write("---")

                    if st.button("🚀 Ejecutar Análisis", type="primary"):
                        progress_bar = st.progress(0)
                        status_text = st.empty()


                        status_text.text(f"Recortando datos climáticos de {data_source_opt}... (Esto puede tardar unos minutos)")




                        region_inputs_dir = clip_inputs.process_region(
                            region_name,
                            shp_path,
                            source_dir=settings.BASE_DIR,
                            data_source=data_source_opt
                        )
                        progress_bar.progress(30)


                        final_out_path = custom_out if custom_out.strip() else None











                        if final_out_path:

                            os.makedirs(final_out_path, exist_ok=True)


                            settings.OUTPUTS_DIR = final_out_path
                            settings.REPORTS_DIR = final_out_path


                            region_out_path = os.path.join(final_out_path, region_name)
                        else:

                            region_out_path = None

                        region_code = settings.add_dynamic_region(region_name, region_inputs_dir, shp_path, output_path=region_out_path)
                        output_dir = settings.get_region_output_dir(region_code)

                        region_pair = [(region_inputs_dir, output_dir)]


                        status_text.text("Calculando PET...")
                        compute_pet.run(region_pairs=region_pair)
                        progress_bar.progress(50)

                        status_text.text("Calculando Balance Hídrico...")
                        water_balance.run(region_pairs=region_pair)
                        progress_bar.progress(70)


                        status_text.text("Generando Gráficos (esto tarda un poco)...")

                        from organized.scripts import generate_plots, generate_dashboard, generate_report
                        try:



                            target_regions = [region_code]



                            original_regions = settings.REGIONS.copy()

                            settings.REGIONS = {k: v for k, v in settings.REGIONS.items() if k in target_regions}

                            try:
                                generate_plots.run(region_codes=target_regions)
                                progress_bar.progress(85)

                                status_text.text("Generando Reporte y Dashboard...")

                                generate_dashboard.run()
                                doc_path = generate_report.create_document(specific_regions=target_regions)
                            finally:

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


                        st.write("---")
                        st.write("#### Resultados Generados")
                        if os.path.exists(output_dir):
                            st.write(f"Carpeta: {output_dir}")




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


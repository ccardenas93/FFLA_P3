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
                    # Simplified JSON serialization to bypass folium function serialization bug
                    import json
                    geojson_data = json.loads(gdf.to_json())
                    folium.GeoJson(geojson_data).add_to(m)
                    
                    st_folium(m, width=700, height=400, returned_objects=[])

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

                                generate_dashboard.run(data_source=data_source_opt)
                                doc_path = generate_report.create_document(specific_regions=target_regions)
                            finally:

                                settings.REGIONS = original_regions

                            progress_bar.progress(100)

                            st.success(f"¡Análisis Completo! Resultados en: `{output_dir}`")

                        except Exception as e:
                            st.error(f"Error generando gráficos/reporte: {e}")
                            st.warning("Los cálculos numéricos (NetCDF) sí se completaron.")
                            import traceback
                            st.code(traceback.format_exc())

                        status_text.text("¡Completado!")

                        # --- Save results to session_state so they survive reruns ---
                        import io
                        import base64
                        import re

                        if os.path.exists(output_dir):
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                                for root, dirs, files in os.walk(output_dir):
                                    for file in files:
                                        file_path_full = os.path.join(root, file)
                                        arcname = os.path.relpath(file_path_full, output_dir)
                                        zf.write(file_path_full, arcname)

                                # Include a self-contained HTML dashboard with base64 images
                                dash_path = os.path.join(settings.OUTPUTS_DIR, "index.html")
                                if os.path.exists(dash_path):
                                    with open(dash_path, 'r', encoding='utf-8') as df:
                                        dash_html_raw = df.read()

                                    _zip_b64_cache = {}
                                    def _zip_to_uri(rel):
                                        if rel in _zip_b64_cache:
                                            return _zip_b64_cache[rel]
                                        abs_p = os.path.join(settings.OUTPUTS_DIR, rel)
                                        if os.path.exists(abs_p):
                                            ext = os.path.splitext(abs_p)[1].lower()
                                            mimes = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif'}
                                            with open(abs_p, 'rb') as imgf:
                                                b = base64.b64encode(imgf.read()).decode('utf-8')
                                            _zip_b64_cache[rel] = f'data:{mimes.get(ext, "image/png")};base64,{b}'
                                            return _zip_b64_cache[rel]
                                        return None

                                    def _zip_src(m):
                                        uri = _zip_to_uri(m.group(1))
                                        return f'src="{uri}"' if uri else m.group(0)

                                    def _zip_lb(m):
                                        uri = _zip_to_uri(m.group(1))
                                        return f"openLightbox('{uri}')" if uri else m.group(0)

                                    dash_self_contained = re.sub(r'src="([^"]+\.(?:png|jpg|jpeg|gif|svg))"', _zip_src, dash_html_raw)
                                    dash_self_contained = re.sub(r"openLightbox\('([^']+\.(?:png|jpg|jpeg|gif|svg))'\)", _zip_lb, dash_self_contained)
                                    zf.writestr("dashboard.html", dash_self_contained)

                            zip_buffer.seek(0)
                            st.session_state["results_zip"] = zip_buffer.getvalue()
                            st.session_state["results_zip_name"] = f"resultados_{region_name}.zip"

                        if 'doc_path' in dir() and doc_path and os.path.exists(doc_path):
                            with open(doc_path, "rb") as doc_file:
                                st.session_state["results_docx"] = doc_file.read()
                                st.session_state["results_docx_name"] = os.path.basename(doc_path)

                        dash_path = os.path.join(settings.OUTPUTS_DIR, "index.html")
                        if os.path.exists(dash_path):
                            with open(dash_path, 'r', encoding='utf-8') as f:
                                dashboard_html = f.read()

                            # Build a cache of path -> base64 data URI
                            _b64_cache = {}
                            def _to_data_uri(rel_path):
                                if rel_path in _b64_cache:
                                    return _b64_cache[rel_path]
                                abs_p = os.path.join(settings.OUTPUTS_DIR, rel_path)
                                if os.path.exists(abs_p):
                                    ext = os.path.splitext(abs_p)[1].lower()
                                    mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.svg': 'image/svg+xml'}
                                    mime_type = mime_map.get(ext, 'image/png')
                                    with open(abs_p, 'rb') as img_file:
                                        b64 = base64.b64encode(img_file.read()).decode('utf-8')
                                    _b64_cache[rel_path] = f'data:{mime_type};base64,{b64}'
                                    return _b64_cache[rel_path]
                                return None

                            # Replace src="path.png"
                            def _replace_src(match):
                                uri = _to_data_uri(match.group(1))
                                return f'src="{uri}"' if uri else match.group(0)

                            # Replace openLightbox('path.png')
                            def _replace_lightbox(match):
                                uri = _to_data_uri(match.group(1))
                                return f"openLightbox('{uri}')" if uri else match.group(0)

                            dashboard_html = re.sub(r'src="([^"]+\.(?:png|jpg|jpeg|gif|svg))"', _replace_src, dashboard_html)
                            dashboard_html = re.sub(r"openLightbox\('([^']+\.(?:png|jpg|jpeg|gif|svg))'\)", _replace_lightbox, dashboard_html)

                            st.session_state["results_dashboard_html"] = dashboard_html

                except Exception as e:
                    st.error(f"Error leyendo el archivo: {e}")
                    import traceback
                    st.code(traceback.format_exc())
            else:
                st.error("No se encontró un archivo .shp válido dentro del ZIP.")

    # --- Display results from session_state (persists across reruns) ---
    if "results_zip" in st.session_state:
        st.write("---")
        st.write("#### 📥 Descargar Resultados")

        col_dl1, col_dl2, col_dl3 = st.columns([2, 2, 1])
        with col_dl1:
            st.download_button(
                label="📦 Descargar todos los resultados (.zip)",
                data=st.session_state["results_zip"],
                file_name=st.session_state.get("results_zip_name", "resultados.zip"),
                mime="application/zip"
            )
        with col_dl2:
            if "results_docx" in st.session_state:
                st.download_button(
                    label="📄 Descargar Reporte Word (.docx)",
                    data=st.session_state["results_docx"],
                    file_name=st.session_state.get("results_docx_name", "reporte.docx"),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        with col_dl3:
            if st.button("🔄 Reiniciar", type="secondary"):
                for key in ["results_zip", "results_zip_name", "results_docx", "results_docx_name", "results_dashboard_html"]:
                    st.session_state.pop(key, None)
                st.rerun()

    if "results_dashboard_html" in st.session_state:
        st.write("---")
        st.write("#### 🖥️ Dashboard Interactivo")
        import streamlit.components.v1 as components
        components.html(st.session_state["results_dashboard_html"], height=900, scrolling=True)

elif mode == "Seleccionar Región Existente":
    st.write("### 📂 Regiones Disponibles")
    selected_region = st.selectbox("Región", list(settings.REGIONS.keys()))

    if st.button("Ver Resultados / Procesar"):
        st.write(f"Mostrando datos para: {settings.REGIONS[selected_region]['name']}")


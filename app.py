import base64
import os
import re
import stat
import sys
import tempfile
import traceback
import types
import unicodedata
import zipfile
from pathlib import Path

import folium
import geopandas as gpd
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

current_dir = os.path.dirname(os.path.abspath(__file__))

if "organized" not in sys.modules:
    organized_pkg = types.ModuleType("organized")
    organized_pkg.__path__ = [current_dir]
    sys.modules["organized"] = organized_pkg

from organized.config import settings
from organized.scripts import clip_inputs, download_data
from organized.scripts.wb import compute_pet, water_balance

IMAGE_EXT_RE = r"(?:png|jpg|jpeg|gif|svg)"
TEMP_RESULT_KEYS = ("results_zip_path", "results_dashboard_path")
SESSION_KEYS = (
    "results_zip_path",
    "results_zip_name",
    "results_docx_path",
    "results_docx_name",
    "results_dashboard_path",
)


def sanitize_folder_name(name, default="mi_area"):
    normalized = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode("ascii")
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", normalized).strip("._-")
    return safe or default


def write_uploaded_file(uploaded_file, temp_dir):
    filename = os.path.basename(uploaded_file.name)
    path = os.path.join(temp_dir, filename)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


def safe_extract_zip(zip_path, extract_to):
    extract_root = Path(extract_to).resolve()
    first_shp = None
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError("ZIP contiene rutas inseguras")

            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError("ZIP contiene enlaces simbólicos no permitidos")

            target = (extract_root / member.filename).resolve()
            try:
                target.relative_to(extract_root)
            except ValueError:
                raise ValueError("ZIP intenta escribir fuera de la carpeta temporal")

            zip_ref.extract(member, extract_root)
            if target.suffix.lower() == ".shp" and first_shp is None:
                first_shp = str(target)
    return first_shp


def load_uploaded_geometry(path):
    gdf = gpd.read_file(path)
    if gdf.empty:
        raise ValueError("El archivo no contiene geometrías")
    if gdf.crs is None:
        raise ValueError("El archivo no tiene CRS definido")
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
    if gdf.empty:
        raise ValueError("Todas las geometrías están vacías")
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
    return gdf


def render_geometry_map(gdf):
    gdf_proj = gdf.to_crs(epsg=3857)
    centroid = gdf_proj.geometry.centroid.to_crs(epsg=4326)
    m = folium.Map(location=[centroid.y.mean(), centroid.x.mean()], zoom_start=8)
    folium.GeoJson(gdf.__geo_interface__).add_to(m)
    st_folium(m, width=700, height=400, returned_objects=[])


def resolve_output_root(custom_out):
    if custom_out and custom_out.strip():
        output_root = os.path.abspath(os.path.expanduser(custom_out.strip()))
    else:
        output_root = settings.OUTPUTS_DIR
    os.makedirs(output_root, exist_ok=True)
    return output_root


def _make_data_uri(path):
    ext = os.path.splitext(path)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
    }
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_map.get(ext, 'image/png')};base64,{b64}"


def make_self_contained_dashboard(index_html_path, output_root):
    output_root_resolved = Path(output_root).resolve()
    with open(index_html_path, "r", encoding="utf-8") as f:
        dashboard_html = f.read()

    cache = {}

    def to_uri(rel_path):
        rel_clean = rel_path.split("?", 1)[0].strip().replace("\\", "/")
        if rel_clean in cache:
            return cache[rel_clean]
        candidate = (output_root_resolved / rel_clean).resolve()
        try:
            candidate.relative_to(output_root_resolved)
        except ValueError:
            return None
        if not candidate.exists():
            return None
        cache[rel_clean] = _make_data_uri(str(candidate))
        return cache[rel_clean]

    def replace_src(match):
        uri = to_uri(match.group(1))
        return f'src="{uri}"' if uri else match.group(0)

    def replace_lightbox(match):
        uri = to_uri(match.group(1))
        return f"openLightbox('{uri}')" if uri else match.group(0)

    dashboard_html = re.sub(rf'src="([^"]+\.{IMAGE_EXT_RE})"', replace_src, dashboard_html)
    dashboard_html = re.sub(
        rf"openLightbox\('([^']+\.{IMAGE_EXT_RE})'\)",
        replace_lightbox,
        dashboard_html,
    )
    return dashboard_html


def create_results_zip(region_output_dir, dashboard_html):
    tmp = tempfile.NamedTemporaryFile(prefix="climate_results_", suffix=".zip", delete=False)
    tmp.close()
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(region_output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, region_output_dir)
                zf.write(file_path, arcname)
        if dashboard_html:
            zf.writestr("dashboard.html", dashboard_html)
    return tmp.name


def set_temp_result_path(key, path):
    old = st.session_state.get(key)
    if old and old != path and os.path.exists(old):
        os.remove(old)
    st.session_state[key] = path


def cleanup_session_artifacts():
    for key in TEMP_RESULT_KEYS:
        path = st.session_state.get(key)
        if path and os.path.exists(path):
            os.remove(path)
    for key in SESSION_KEYS:
        st.session_state.pop(key, None)


st.set_page_config(page_title="Climate Analysis App", layout="wide")
st.title("🌍 Análisis Climático FFLA")

st.sidebar.header("Configuración")
st.sidebar.subheader("📦 Datos Base")
if st.sidebar.button("Descargar/Actualizar Datos Base"):
    with st.spinner("Descargando datos del repositorio (esto puede tardar)..."):
        try:
            download_data.run(base_dir=current_dir)
            st.sidebar.success("✅ Datos descargados/verificados.")
        except Exception as exc:
            st.sidebar.error(f"Error en descarga: {exc}")

mode = st.sidebar.radio(
    "Modo de Operación",
    ["Seleccionar Región Existente", "Nueva Área de Interés (Subir SHP/GPKG)"],
)

if mode == "Nueva Área de Interés (Subir SHP/GPKG)":
    st.write("### 📤 Cargar Área de Estudio")
    st.info("Sube un archivo **.gpkg** o un **.zip** que contenga un Shapefile (.shp, .shx, .dbf, etc).")

    uploaded_file = st.file_uploader("Seleccionar archivo", type=["zip", "gpkg"])

    if uploaded_file:
        with tempfile.TemporaryDirectory(prefix="climate_upload_") as temp_dir:
            uploaded_path = write_uploaded_file(uploaded_file, temp_dir)
            shp_path = None

            try:
                if uploaded_file.name.lower().endswith(".zip"):
                    shp_path = safe_extract_zip(uploaded_path, temp_dir)
                else:
                    shp_path = uploaded_path
            except Exception as exc:
                st.error(f"Error procesando el archivo ZIP: {exc}")
                st.code(traceback.format_exc())

            if not shp_path:
                st.error("No se encontró un archivo .shp válido dentro del ZIP.")
            else:
                try:
                    gdf = load_uploaded_geometry(shp_path)
                except Exception as exc:
                    st.error(f"Error cargando geometría: {exc}")
                    st.code(traceback.format_exc())
                else:
                    st.success("✅ Geometría cargada correctamente.")
                    render_geometry_map(gdf)

                    col1, col2 = st.columns(2)
                    with col1:
                        region_name_display = st.text_input(
                            "Nombre del Área (para carpeta)",
                            value="Mi_Area",
                        )
                    with col2:
                        custom_out = st.text_input(
                            "Carpeta de Resultados (Opcional)",
                            placeholder="Dejar vacío para usar default",
                        )

                    region_folder = sanitize_folder_name(region_name_display, default="mi_area")
                    if (region_name_display or "").strip() != region_folder:
                        st.caption(f"Se usará la carpeta segura: `{region_folder}`")

                    st.write("---")
                    data_source_opt = st.radio(
                        "📡 Fuente de Datos Climáticos",
                        ["FODESNA", "FMPLPT"],
                        help="Seleccione el conjunto de datos a utilizar. FODESNA para la provincia de Napo. FMPLPT para la provincia de Tungurahua.",
                    )
                    st.write("---")

                    if st.button("🚀 Ejecutar Análisis", type="primary"):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        region_code = None
                        existing_region_codes = set(settings.REGIONS.keys())

                        try:
                            cleanup_session_artifacts()
                            region_label = (region_name_display or "").strip() or region_folder
                            output_root = resolve_output_root(custom_out)
                            region_output_dir = os.path.join(output_root, region_folder)
                            os.makedirs(region_output_dir, exist_ok=True)

                            status_text.text(
                                f"Recortando datos climáticos de {data_source_opt}... (Esto puede tardar unos minutos)"
                            )
                            region_inputs_dir = clip_inputs.process_region(
                                region_folder,
                                shp_path,
                                source_dir=settings.BASE_DIR,
                                data_source=data_source_opt,
                            )
                            progress_bar.progress(30)

                            region_code = settings.add_dynamic_region(
                                region_label,
                                region_inputs_dir,
                                shp_path,
                                output_path=region_output_dir,
                            )
                            region_pair = [(region_inputs_dir, region_output_dir)]

                            status_text.text("Calculando PET...")
                            compute_pet.run(region_pairs=region_pair)
                            progress_bar.progress(50)

                            status_text.text("Calculando Balance Hídrico...")
                            water_balance.run(region_pairs=region_pair)
                            progress_bar.progress(70)

                            status_text.text("Generando gráficos...")
                            from organized.scripts import generate_dashboard, generate_plots, generate_report

                            generate_plots.run(region_codes=[region_code])
                            progress_bar.progress(85)

                            status_text.text("Generando reporte y dashboard...")
                            generate_dashboard.run(
                                data_source=data_source_opt,
                                output_root=output_root,
                                region_codes=[region_code],
                            )
                            doc_path = generate_report.create_document(
                                specific_regions=[region_code],
                                report_dir=output_root,
                            )
                            progress_bar.progress(95)

                            dashboard_html = None
                            index_html_path = os.path.join(output_root, "index.html")
                            if os.path.exists(index_html_path):
                                dashboard_html = make_self_contained_dashboard(index_html_path, output_root)
                                dashboard_tmp = tempfile.NamedTemporaryFile(
                                    prefix="climate_dashboard_",
                                    suffix=".html",
                                    delete=False,
                                    mode="w",
                                    encoding="utf-8",
                                )
                                with dashboard_tmp:
                                    dashboard_tmp.write(dashboard_html)
                                set_temp_result_path("results_dashboard_path", dashboard_tmp.name)

                            zip_path = create_results_zip(region_output_dir, dashboard_html)
                            set_temp_result_path("results_zip_path", zip_path)
                            st.session_state["results_zip_name"] = f"resultados_{region_folder}.zip"

                            if doc_path and os.path.exists(doc_path):
                                st.session_state["results_docx_path"] = doc_path
                                st.session_state["results_docx_name"] = os.path.basename(doc_path)

                            progress_bar.progress(100)
                            status_text.text("¡Completado!")
                            st.success(f"¡Análisis Completo! Resultados en: `{region_output_dir}`")
                        except Exception as exc:
                            status_text.text("Falló")
                            st.error(f"Error durante el análisis: {exc}")
                            st.warning("Los cálculos parciales podrían haberse generado antes del error.")
                            st.code(traceback.format_exc())
                        finally:
                            if region_code and region_code not in existing_region_codes:
                                settings.REGIONS.pop(region_code, None)

    if "results_zip_path" in st.session_state:
        st.write("---")
        st.write("#### 📥 Descargar Resultados")
        col_dl1, col_dl2, col_dl3 = st.columns([2, 2, 1])

        with col_dl1:
            zip_path = st.session_state.get("results_zip_path")
            if zip_path and os.path.exists(zip_path):
                with open(zip_path, "rb") as f:
                    st.download_button(
                        label="📦 Descargar todos los resultados (.zip)",
                        data=f.read(),
                        file_name=st.session_state.get("results_zip_name", "resultados.zip"),
                        mime="application/zip",
                    )
            else:
                st.warning("No se encontró el archivo ZIP de resultados.")

        with col_dl2:
            doc_path = st.session_state.get("results_docx_path")
            if doc_path and os.path.exists(doc_path):
                with open(doc_path, "rb") as f:
                    st.download_button(
                        label="📄 Descargar Reporte Word (.docx)",
                        data=f.read(),
                        file_name=st.session_state.get("results_docx_name", "reporte.docx"),
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )

        with col_dl3:
            if st.button("🔄 Reiniciar", type="secondary"):
                cleanup_session_artifacts()
                st.rerun()

    dashboard_path = st.session_state.get("results_dashboard_path")
    if dashboard_path and os.path.exists(dashboard_path):
        st.write("---")
        st.write("#### 🖥️ Dashboard Interactivo")
        with open(dashboard_path, "r", encoding="utf-8") as f:
            components.html(f.read(), height=900, scrolling=True)

elif mode == "Seleccionar Región Existente":
    st.write("### 📂 Regiones Disponibles")
    selected_region = st.selectbox("Región", list(settings.REGIONS.keys()))
    if st.button("Ver Resultados / Procesar"):
        st.write(f"Mostrando datos para: {settings.REGIONS[selected_region]['name']}")

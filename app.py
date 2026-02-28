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
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from netCDF4 import Dataset
from shapely import wkb as shapely_wkb
from shapely.geometry import box
from shapely.prepared import prep
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


def geometry_union(geoseries):
    if hasattr(geoseries, "union_all"):
        return geoseries.union_all()
    return geoseries.unary_union


def render_geometry_map(gdf):
    return render_geometry_map_with_grid(gdf, grid_preview=None)


def render_geometry_map_with_grid(gdf, grid_preview=None):
    gdf_proj = gdf.to_crs(epsg=3857)
    centroid = gdf_proj.geometry.centroid.to_crs(epsg=4326)
    m = folium.Map(location=[centroid.y.mean(), centroid.x.mean()], zoom_start=8)
    folium.GeoJson(gdf.__geo_interface__, name="Área de estudio").add_to(m)

    if grid_preview and grid_preview.get("preview_cells"):
        grid_layer = folium.FeatureGroup(name="Pixeles NC (preview)", show=True)
        for y0, x0, y1, x1 in grid_preview["preview_cells"]:
            folium.Rectangle(
                bounds=[[y0, x0], [y1, x1]],
                color="#2563eb",
                weight=1,
                fill=False,
                opacity=0.45,
            ).add_to(grid_layer)
        grid_layer.add_to(m)
        folium.LayerControl(collapsed=True).add_to(m)

    minx, miny, maxx, maxy = gdf.total_bounds
    if minx == maxx:
        minx -= 0.01
        maxx += 0.01
    if miny == maxy:
        miny -= 0.01
        maxy += 0.01
    m.fit_bounds([[miny, minx], [maxy, maxx]])

    st_folium(m, width=700, height=400, returned_objects=[])


def resolve_grid_nc_path(data_source):
    candidates = [
        os.path.join(settings.INPUTS_DIR, data_source, "historical_ecuador", "pr_historical_ecuador.nc"),
        os.path.join(settings.INPUTS_DIR, data_source, "historical_ecuador", "pr.nc"),
    ]
    if data_source == "FMPLPT":
        candidates.extend(
            [
                os.path.join(settings.INPUTS_DIR, "FDAT", "historical_ecuador", "pr_historical_ecuador.nc"),
                os.path.join(settings.INPUTS_DIR, "FDAT", "historical_ecuador", "pr.nc"),
            ]
        )
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


@st.cache_data(show_spinner=False)
def load_grid_axes(nc_path):
    with Dataset(nc_path, "r") as ds:
        if "lat" not in ds.variables or "lon" not in ds.variables:
            raise ValueError(f"Grid file sin ejes lat/lon: {nc_path}")
        lat = np.asarray(ds.variables["lat"][:], dtype=float).ravel()
        lon = np.asarray(ds.variables["lon"][:], dtype=float).ravel()

    lat = np.unique(lat)
    lon = np.unique(lon)
    lat.sort()
    lon.sort()
    if lat.size == 0 or lon.size == 0:
        raise ValueError("Grid vacío en NetCDF")
    return lat, lon


def centers_to_edges(axis):
    axis = np.asarray(axis, dtype=float)
    if axis.size == 1:
        step = 0.1
        return np.array([axis[0] - step / 2, axis[0] + step / 2], dtype=float)

    edges = np.empty(axis.size + 1, dtype=float)
    edges[1:-1] = (axis[:-1] + axis[1:]) / 2.0
    edges[0] = axis[0] - (axis[1] - axis[0]) / 2.0
    edges[-1] = axis[-1] + (axis[-1] - axis[-2]) / 2.0
    return edges


@st.cache_data(show_spinner=False)
def compute_grid_preview(geometry_wkb, data_source, max_preview_cells=900):
    nc_path = resolve_grid_nc_path(data_source)
    if not nc_path:
        return {"error": f"No se encontró NetCDF de grilla para {data_source}."}

    lat, lon = load_grid_axes(nc_path)
    lat_edges = centers_to_edges(lat)
    lon_edges = centers_to_edges(lon)
    dlat = float(np.median(np.abs(np.diff(lat)))) if lat.size > 1 else 0.0
    dlon = float(np.median(np.abs(np.diff(lon)))) if lon.size > 1 else 0.0

    geom = shapely_wkb.loads(geometry_wkb)
    prepared = prep(geom)
    minx, miny, maxx, maxy = geom.bounds

    lat_mask = (lat_edges[:-1] <= maxy) & (lat_edges[1:] >= miny)
    lon_mask = (lon_edges[:-1] <= maxx) & (lon_edges[1:] >= minx)
    lat_idx = np.where(lat_mask)[0]
    lon_idx = np.where(lon_mask)[0]

    bbox_cells = int(lat_idx.size * lon_idx.size)
    touched_cells = 0
    preview_cells = []

    for i in lat_idx:
        y0a, y1a = lat_edges[i], lat_edges[i + 1]
        y0, y1 = (y0a, y1a) if y0a <= y1a else (y1a, y0a)
        for j in lon_idx:
            x0a, x1a = lon_edges[j], lon_edges[j + 1]
            x0, x1 = (x0a, x1a) if x0a <= x1a else (x1a, x0a)
            cell = box(x0, y0, x1, y1)
            if prepared.intersects(cell):
                touched_cells += 1
                if len(preview_cells) < max_preview_cells:
                    preview_cells.append((y0, x0, y1, x1))

    return {
        "source_nc": nc_path,
        "grid_shape": (int(lat.size), int(lon.size)),
        "grid_total_cells": int(lat.size * lon.size),
        "resolution_deg": (dlat, dlon),
        "bbox_cells": bbox_cells,
        "touched_cells": touched_cells,
        "preview_cells": preview_cells,
        "preview_is_sampled": touched_cells > len(preview_cells),
    }


def infer_data_source(gdf):
    """Infer best source by AOI overlap with known reference regions."""
    source_options = ["FODESNA", "FMPLPT"]
    target = geometry_union(gdf.geometry)
    if target.is_empty:
        return source_options[0], {}, "default"
    if not target.is_valid:
        target = target.buffer(0)
    target_proj = gpd.GeoSeries([target], crs="EPSG:4326").to_crs(epsg=3857).iloc[0]
    target_area = float(target_proj.area) if target_proj.area > 0 else 0.0

    overlap_ratios = {}
    overlap_areas = {}
    method = "overlap"
    for code in source_options:
        ref_proj = None
        try:
            shp_path = settings.REGIONS.get(code, {}).get("shapefile")
            if shp_path and os.path.exists(shp_path):
                ref = gpd.read_file(shp_path)
                if not ref.empty and ref.crs is not None:
                    if ref.crs.to_epsg() != 4326:
                        ref = ref.to_crs("EPSG:4326")
                    ref_geom = geometry_union(ref.geometry)
                    if not ref_geom.is_empty:
                        if not ref_geom.is_valid:
                            ref_geom = ref_geom.buffer(0)
                        ref_proj = gpd.GeoSeries([ref_geom], crs="EPSG:4326").to_crs(epsg=3857).iloc[0]
        except Exception:
            ref_proj = None

        if ref_proj is None:
            nc_path = resolve_grid_nc_path(code)
            if not nc_path:
                continue
            try:
                lat, lon = load_grid_axes(nc_path)
                lat_edges = centers_to_edges(lat)
                lon_edges = centers_to_edges(lon)
                extent_geom = box(
                    float(np.min(lon_edges)),
                    float(np.min(lat_edges)),
                    float(np.max(lon_edges)),
                    float(np.max(lat_edges)),
                )
                ref_proj = gpd.GeoSeries([extent_geom], crs="EPSG:4326").to_crs(epsg=3857).iloc[0]
                method = "nc_extent"
            except Exception:
                continue

        inter_area = float(target_proj.intersection(ref_proj).area)
        overlap_areas[code] = inter_area
        overlap_ratios[code] = (inter_area / target_area) if target_area > 0 else 0.0

    if overlap_areas:
        inferred = max(overlap_areas, key=overlap_areas.get)
        if overlap_areas.get(inferred, 0.0) > 0:
            return inferred, overlap_ratios, method

    # Fallback: choose source whose reference extent centroid is closest to AOI centroid.
    target_centroid = target_proj.centroid
    distances = {}
    for code in source_options:
        nc_path = resolve_grid_nc_path(code)
        if not nc_path:
            continue
        try:
            lat, lon = load_grid_axes(nc_path)
            lat_edges = centers_to_edges(lat)
            lon_edges = centers_to_edges(lon)
            extent_geom = box(
                float(np.min(lon_edges)),
                float(np.min(lat_edges)),
                float(np.max(lon_edges)),
                float(np.max(lat_edges)),
            )
            extent_proj = gpd.GeoSeries([extent_geom], crs="EPSG:4326").to_crs(epsg=3857).iloc[0]
            distances[code] = float(target_centroid.distance(extent_proj.centroid))
        except Exception:
            continue
    if distances:
        inferred = min(distances, key=distances.get)
        return inferred, overlap_ratios, "distance"

    return source_options[0], overlap_ratios, "default"


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

                    st.write("### 🧩 Vista previa de píxeles NetCDF")
                    auto_source, overlap_ratios, infer_method = infer_data_source(gdf)
                    source_options = ["FODESNA", "FMPLPT"]
                    default_source_index = source_options.index(auto_source) if auto_source in source_options else 0
                    data_source_opt = st.radio(
                        "📡 Fuente de Datos Climáticos",
                        source_options,
                        index=default_source_index,
                        help="Seleccione el conjunto de datos a utilizar. FODESNA para la provincia de Napo. FMPLPT para la provincia de Tungurahua.",
                    )
                    if overlap_ratios:
                        ratio_text = ", ".join(
                            f"{k}: {overlap_ratios.get(k, 0.0):.1%}" for k in source_options
                        )
                        method_txt = {
                            "overlap": "solape con polígonos de referencia",
                            "nc_extent": "solape con extensión de grillas NC",
                            "distance": "distancia a extensión de grillas NC",
                            "default": "valor por defecto",
                        }.get(infer_method, infer_method)
                        st.caption(
                            f"Selección automática sugerida: `{auto_source}` "
                            f"({method_txt}; solape AOI: {ratio_text}). Puede cambiarla manualmente."
                        )
                    else:
                        st.caption(
                            f"Selección automática sugerida: `{auto_source}`. "
                            "No se pudo calcular solape, puede cambiarla manualmente."
                        )
                    geom_wkb = geometry_union(gdf.geometry).wkb
                    grid_preview = compute_grid_preview(geom_wkb, data_source_opt)
                    if grid_preview.get("error"):
                        st.warning(grid_preview["error"])
                        render_geometry_map_with_grid(gdf, grid_preview=None)
                    else:
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.metric("Resolución lat/lon", f"{grid_preview['resolution_deg'][0]:.4f}° / {grid_preview['resolution_deg'][1]:.4f}°")
                        with c2:
                            st.metric("Pixeles (grid completo)", f"{grid_preview['grid_total_cells']:,}")
                        with c3:
                            st.metric("Pixeles en bbox AOI", f"{grid_preview['bbox_cells']:,}")
                        with c4:
                            st.metric("Pixeles que tocarían AOI", f"{grid_preview['touched_cells']:,}")

                        st.caption(
                            f"Fuente de grilla: `{grid_preview['source_nc']}`"
                            + (" | El overlay muestra una muestra de celdas." if grid_preview["preview_is_sampled"] else "")
                        )
                        render_geometry_map_with_grid(gdf, grid_preview=grid_preview)
                    st.write("---")

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

import os
import glob
import xarray as xr
import geopandas as gpd
import rioxarray
from shapely.geometry import mapping
from organized.config import settings

def _load_region_gdf(shapefile_path):
    gdf = gpd.read_file(shapefile_path)
    if gdf.empty:
        raise ValueError("Shapefile sin geometrías")
    if gdf.crs is None:
        raise ValueError("Shapefile sin CRS definido")
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
    if gdf.empty:
        raise ValueError("Shapefile sin geometrías válidas")
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
    return gdf


def clip_nc_file(nc_path, out_path_base, gdf, var_name=None):
    """
    Clips a NetCDF file to the geometry of a shapefile.
    out_path_base: directory to save to. Filename is inferred/standardized.
    """
    try:
        fname = os.path.basename(nc_path)
        standard_name = fname


        if fname.startswith("P_"):
            standard_name = "pr_" + fname[2:]
        elif fname.startswith("T_"):

            standard_name = "tas_" + fname[2:]
        elif fname.startswith("pr_") or fname.startswith("tas") or fname.startswith("pet") or fname.startswith("wb"):
            standard_name = fname


        out_path = os.path.join(out_path_base, standard_name)
        with xr.open_dataset(nc_path) as ds:
            if "lat" in ds.coords and "lon" in ds.coords:
                ds = ds.rio.write_crs("EPSG:4326")
                ds.rio.set_spatial_dims("lon", "lat", inplace=True)
            elif "lat" in ds.data_vars and "lon" in ds.data_vars:
                ds = ds.set_coords(["lat", "lon"])
                ds = ds.rio.write_crs("EPSG:4326")
                ds.rio.set_spatial_dims("lon", "lat", inplace=True)
            else:
                print(f"⚠️  Skipping {nc_path}: missing lat/lon coords")
                return False

            clipped = ds.rio.clip(
                gdf.geometry.apply(mapping), gdf.crs, drop=True, all_touched=True
            )
            os.makedirs(out_path_base, exist_ok=True)
            encoding = {var: {"zlib": True, "complevel": 4} for var in clipped.data_vars}
            clipped.to_netcdf(out_path, encoding=encoding)

        print(f"  ✅ Clipped: {os.path.basename(nc_path)} -> {os.path.basename(out_path)}")
        return True

    except Exception as e:
        print(f"  ❌ Error clipping {os.path.basename(nc_path)}: {e}")
        return False

def process_region(region_name, shapefile_path, source_dir=None, data_source=None):
    """
    Creates input files for a new region by clipping national data.
    data_source: 'FODESNA', 'FMPLPT', or None (search everything)
    """
    if source_dir is None:
        source_dir = settings.BASE_DIR

    safe_region_name = os.path.basename(os.path.normpath(region_name))
    if safe_region_name in ("", ".", "..") or safe_region_name != region_name:
        raise ValueError(f"Invalid region name for filesystem: {region_name}")

    output_base = os.path.join(settings.INPUTS_DIR, safe_region_name)

    source_msg = f" (Fuente: {data_source})" if data_source else " (Buscando en todo)"
    print(f"✂️  Clipping inputs for region '{region_name}' using {shapefile_path}{source_msg}...")

    count = 0
    gdf = _load_region_gdf(shapefile_path)


    if "GDAL_DATA" not in os.environ:
        try:
            import fiona
            os.environ["GDAL_DATA"] = fiona.datadir
        except Exception:
            pass


    if data_source == "FODESNA":
        search_dirs = [
            os.path.join(source_dir, "inputs", "FODESNA"),
            os.path.join(source_dir, "FODESNA"),
            os.path.join(source_dir, "inputs"),
        ]
    elif data_source == "FMPLPT":
        search_dirs = [
            os.path.join(source_dir, "inputs", "FMPLPT"),
            os.path.join(source_dir, "FMPLPT"),
            os.path.join(source_dir, "inputs", "FDAT"),
            os.path.join(source_dir, "FDAT"),
        ]
    else:

        search_dirs = [
            source_dir,
            os.path.join(source_dir, "inputs"),
            os.path.join(source_dir, "inputs", "FODESNA"),
            os.path.join(source_dir, "inputs", "FMPLPT"),
            os.path.join(source_dir, "inputs", "FDAT"),
            os.path.join(source_dir, "FODESNA"),
            os.path.join(source_dir, "FMPLPT"),
            os.path.join(source_dir, "FDAT"),
        ]

    for dom in settings.DOMAINS:
        found_domain = False


        dom_src = None
        for base in search_dirs:
            p = os.path.join(base, dom)
            if os.path.exists(p):
                dom_src = p
                break

        if not dom_src:
            print(f"  ⚠️  Source domain dir not found for '{dom}' (checked FDAT/FODESNA/root)")
            continue

        print(f"  Found source for {dom}: {dom_src}")
        dom_out = os.path.join(output_base, dom)

        files = glob.glob(os.path.join(dom_src, "*.nc"))
        if not files:
            print(f"  ⚠️  No .nc files found in {dom_src}")
            continue

        for f in files:
            if clip_nc_file(f, dom_out, gdf):
                count += 1

    print(f"✨ Finished. {count} files clipped for {region_name}.\n")
    return output_base

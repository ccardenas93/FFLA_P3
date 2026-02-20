import os
import glob
import xarray as xr
import geopandas as gpd
import rioxarray
from shapely.geometry import mapping
from organized.config import settings

def clip_nc_file(nc_path, shapefile_path, out_path_base, var_name=None):
    """
    Clips a NetCDF file to the geometry of a shapefile.
    out_path_base: directory to save to. Filename is inferred/standardized.
    """
    try:

        gdf = gpd.read_file(shapefile_path)
        if gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")


        ds = xr.open_dataset(nc_path)



        fname = os.path.basename(nc_path)
        standard_name = fname


        if fname.startswith("P_"):
            standard_name = "pr_" + fname[2:]
        elif fname.startswith("T_"):

            standard_name = "tas_" + fname[2:]
        elif fname.startswith("pr_") or fname.startswith("tas") or fname.startswith("pet") or fname.startswith("wb"):
            standard_name = fname






        out_path = os.path.join(out_path_base, standard_name)


        if 'lat' in ds.coords and 'lon' in ds.coords:
            ds = ds.rio.write_crs("EPSG:4326")
            ds.rio.set_spatial_dims("lon", "lat", inplace=True)
        else:

            if 'lat' in ds.data_vars:
                ds = ds.set_coords(['lat', 'lon'])
                ds = ds.rio.write_crs("EPSG:4326")
                ds.rio.set_spatial_dims("lon", "lat", inplace=True)
            else:
                print(f"⚠️  Skipping {nc_path}: missing lat/lon coords")
                return False


        clipped = ds.rio.clip(gdf.geometry.apply(mapping), gdf.crs, drop=True)


        os.makedirs(out_path_base, exist_ok=True)

        encoding = {var: {'zlib': True, 'complevel': 4} for var in clipped.data_vars}
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

    output_base = os.path.join(settings.INPUTS_DIR, region_name)

    source_msg = f" (Fuente: {data_source})" if data_source else " (Buscando en todo)"
    print(f"✂️  Clipping inputs for region '{region_name}' using {shapefile_path}{source_msg}...")

    count = 0


    if "GDAL_DATA" not in os.environ:
        try:
            import fiona
            os.environ["GDAL_DATA"] = fiona.datadir
        except:
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
        ]
    else:

        search_dirs = [
            source_dir,
            os.path.join(source_dir, "inputs"),
            os.path.join(source_dir, "inputs", "FODESNA"),
            os.path.join(source_dir, "inputs", "FMPLPT"),
            os.path.join(source_dir, "FODESNA"),
            os.path.join(source_dir, "FMPLPT"),
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
            if clip_nc_file(f, shapefile_path, dom_out):
                count += 1

    print(f"✨ Finished. {count} files clipped for {region_name}.\n")
    return output_base

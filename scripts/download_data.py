import os
import tempfile

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://github.com/ccardenas93/FFLA/raw/main"
TIMEOUT = (10, 180)

FILES_FMPLPT = {
    "FMPLPT/historical_ecuador": [
        "pr_historical_ecuador.nc",
        "tas_historical_ecuador.nc",
        "tasmin_historical_ecuador.nc",
        "tasmax_historical_ecuador.nc",
    ],
    "FMPLPT/ssp126_ecuador": [
        "pr_ssp126_ecuador.nc",
        "tas_ssp126_ecuador.nc",
        "tasmin_ssp126_ecuador.nc",
        "tasmax_ssp126_ecuador.nc",
    ],
    "FMPLPT/ssp370_ecuador": [
        "pr_ssp370_ecuador.nc",
        "tas_ssp370_ecuador.nc",
        "tasmin_ssp370_ecuador.nc",
        "tasmax_ssp370_ecuador.nc",
    ],
    "FMPLPT/ssp585_ecuador": [
        "pr_ssp585_ecuador.nc",
        "tas_ssp585_ecuador.nc",
        "tasmin_ssp585_ecuador.nc",
        "tasmax_ssp585_ecuador.nc",
    ],
}

FILES_FODESNA = {
    "FODESNA/historical_ecuador": [
        "pr_historical_ecuador.nc",
        "tas_historical_ecuador.nc",
        "tasmin_historical_ecuador.nc",
        "tasmax_historical_ecuador.nc",
    ],
    "FODESNA/ssp126_ecuador": [
        "pr_ssp126_ecuador.nc",
        "tas_ssp126_ecuador.nc",
        "tasmin_ssp126_ecuador.nc",
        "tasmax_ssp126_ecuador.nc",
    ],
    "FODESNA/ssp370_ecuador": [
        "pr_ssp370_ecuador.nc",
        "tas_ssp370_ecuador.nc",
        "tasmin_ssp370_ecuador.nc",
        "tasmax_ssp370_ecuador.nc",
    ],
    "FODESNA/ssp585_ecuador": [
        "pr_ssp585_ecuador.nc",
        "tas_ssp585_ecuador.nc",
        "tasmin_ssp585_ecuador.nc",
        "tasmax_ssp585_ecuador.nc",
    ],
}


def _build_session():
    session = requests.Session()
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def download_file(url, dest_path, session):
    print(f"Downloading {url}...")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        prefix=".download_",
        suffix=".part",
        dir=os.path.dirname(dest_path),
    )
    os.close(fd)

    try:
        with session.get(url, stream=True, timeout=TIMEOUT) as response:
            response.raise_for_status()
            expected_size = int(response.headers.get("Content-Length") or 0)
            bytes_written = 0
            with open(tmp_path, "wb") as out:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    out.write(chunk)
                    bytes_written += len(chunk)

        if bytes_written <= 0:
            raise RuntimeError("Downloaded file is empty")
        if expected_size and bytes_written != expected_size:
            raise RuntimeError(
                f"Size mismatch (expected {expected_size}, got {bytes_written})"
            )

        os.replace(tmp_path, dest_path)
        print(f"✅ Saved to {dest_path}")
        return True
    except Exception as exc:
        print(f"❌ Failed to download {url}: {exc}")
        return False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def run(base_dir=None):
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    target_base = os.path.join(base_dir, "inputs")
    print(f"🚀 Starting Data Download to {target_base}...")

    all_files = {**FILES_FODESNA, **FILES_FMPLPT}
    failures = []
    downloaded = 0
    skipped = 0

    session = _build_session()
    try:
        for folder, files in all_files.items():
            local_dir = os.path.join(target_base, folder)
            os.makedirs(local_dir, exist_ok=True)

            remote_folder = folder.replace("FMPLPT", "FDAT")
            for filename in files:
                file_url = f"{BASE_URL}/{remote_folder}/{filename}"
                dest_path = os.path.join(local_dir, filename)

                if os.path.exists(dest_path):
                    if os.path.getsize(dest_path) > 0:
                        print(f"⏩ {filename} already exists. Skipping.")
                        skipped += 1
                        continue
                    os.remove(dest_path)

                ok = download_file(file_url, dest_path, session=session)
                if ok:
                    downloaded += 1
                else:
                    failures.append(file_url)
    finally:
        session.close()

    print(
        f"📦 Download summary: downloaded={downloaded}, skipped={skipped}, failed={len(failures)}"
    )
    if failures:
        raise RuntimeError(
            "Failed to download required files:\n" + "\n".join(failures[:8])
        )


if __name__ == "__main__":
    run()

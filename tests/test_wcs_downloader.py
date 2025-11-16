from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import box

from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from orthophotos_downloader.data_scraping.file_downloader import FileServiceDownloader
from orthophotos_downloader.wms_catalog.catalog_manager import WMSService


def _make_wcs_service() -> WMSService:
    return WMSService(
        id="SH_RGBI_DOP20_wcs_test",
        state_code="SH",
        state_name="Schleswig-Holstein",
        type="RGBI",
        resolution=0.2,
        crs="EPSG:25832",
        files={
            "index_type": "wcs",
            "wcs_url": "https://dienste.gdi-sh.de/WCS_SH_DOP20col_OpenGBD",
            "wcs_coverage": "2",
            "wcs_format": "image/GeoTIFF",
            "grid_size": 1000,
            "default_extension": "tif",
            "wcs_max_pixels": 4000,
        },
    )


def test_wcs_download_respects_pixel_limit(tmp_path: Path, monkeypatch):
    service = _make_wcs_service()
    downloader = FileServiceDownloader(service=service, grid_spacing=1000, extract_metadata=False)

    with MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff",
            width=10,
            height=10,
            count=1,
            dtype="uint8",
            transform=from_origin(0, 10, 1, 1),
            crs="EPSG:25832",
        ) as dataset:
            dataset.write(np.zeros((1, 10, 10), dtype=np.uint8))
        geotiff_bytes = memfile.read()

    requested_urls = []

    class DummyResponse:
        def __init__(self, data: bytes):
            self._data = data

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=8192):
            yield self._data

    def fake_get(url, stream=True, timeout=180):
        requested_urls.append(url)
        return DummyResponse(geotiff_bytes)

    monkeypatch.setattr("orthophotos_downloader.data_scraping.file_downloader.requests.get", fake_get)

    area = box(568000, 5965000, 569000, 5966000)
    result = downloader.download_images_from_polygon(
        area_name="test",
        area_polygon=area,
        out_path=tmp_path,
    )

    assert result.images is not None
    assert len(result.images) > 0
    assert len(requested_urls) == 16
    assert all("WIDTH=2500" in url for url in requested_urls)
    assert all("HEIGHT=2500" in url for url in requested_urls)
    assert all("RESX=" not in url for url in requested_urls)
    assert any(path.exists() for path in tmp_path.glob("*.tif"))

from pathlib import Path

import pytest
from shapely.geometry import box

from orthophotos_downloader.wms_catalog.catalog_manager import WMSService
from orthophotos_downloader.wms_catalog.service_discovery import ServiceDiscovery


def _make_atom_service(year="2024"):
    return WMSService(
        id=f"SH_RGBI_DOP20_{year}",
        state_code="SH",
        state_name="Schleswig-Holstein",
        type="RGBI",
        resolution=0.2,
        year=year,
        files={
            "index_type": "atom",
            "atom_feed_url": "https://example.com/feed.xml",
            "product_code": "dop20rgbi",
            "grid_size": 1000,
            "default_extension": "tif",
        },
    )


@pytest.fixture
def service_discovery(tmp_path: Path) -> ServiceDiscovery:
    return ServiceDiscovery(use_cache=False)


def test_file_service_verification_success(monkeypatch, service_discovery):
    service = _make_atom_service("2024")
    area = box(455000, 6083000, 456000, 6084000)
    observed_years = []

    from orthophotos_downloader.data_scraping import file_downloader

    def fake_get_tiles(self, area_polygon, target_year=None):
        observed_years.append(target_year)
        return [{"dummy": "tile"}]

    monkeypatch.setattr(
        file_downloader.FileServiceDownloader,
        "get_tiles_from_atom_feed",
        fake_get_tiles,
    )

    result = service_discovery._verify_service_coverage(service, area)

    assert result["has_coverage"] is True
    assert result["coverage_category"] == "full"
    assert observed_years == ["2024"]


def test_file_service_verification_failure(monkeypatch, service_discovery):
    service = _make_atom_service("2023")
    area = box(455000, 6083000, 456000, 6084000)

    from orthophotos_downloader.data_scraping import file_downloader

    def fake_no_tiles(self, area_polygon, target_year=None):
        return []

    monkeypatch.setattr(
        file_downloader.FileServiceDownloader,
        "get_tiles_from_atom_feed",
        fake_no_tiles,
    )

    result = service_discovery._verify_service_coverage(service, area)

    assert result["has_coverage"] is False
    assert result["coverage_category"] == "minimal"

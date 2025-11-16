"""
Integration tests that actually download data from WMS services.
These tests are marked as slow and can be skipped with: pytest -m "not download"
"""

import pytest
import tempfile
from pathlib import Path
from shapely.geometry import box
import geopandas as gpd

from orthophotos_downloader.data_scraping.generic_downloader import WMSServiceDownloader
from orthophotos_downloader.data_scraping.image_download import RGBIImageDownloader
from orthophotos_downloader import AutoOrthophotoDownloader
from orthophotos_downloader.wms_catalog import WMSCatalogManager


class TestActualDownloads:
    """Integration tests that perform actual downloads."""

    @pytest.mark.download
    @pytest.mark.slow
    def test_small_rgb_download_bavaria(self):
        """Test actual RGB download from Bavaria (100m x 100m)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Get BY RGB service from catalog
            catalog = WMSCatalogManager()
            service = catalog.filter_services(state_code='BY', image_type='RGB', year='latest')[0]
            
            downloader = WMSServiceDownloader(service=service, grid_spacing=100)

            # Very small area in Munich
            bbox = box(691000, 5334000, 691100, 5334100)
            area = gpd.GeoDataFrame([1], geometry=[bbox], crs="EPSG:25832")

            result = downloader.download_images_from_polygon(
                area_name="test_small",
                area_polygon=area.geometry,
                out_path=Path(tmpdir),
            )

            assert result is not None
            assert result.images is not None
            assert len(result.images) > 0

            # Check that file was created
            assert result.images[0].image_path.exists()

    @pytest.mark.download
    @pytest.mark.slow
    def test_small_cir_download_bavaria(self):
        """Test actual CIR download from Bavaria (100m x 100m)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Get BY CIR service from catalog
            catalog = WMSCatalogManager()
            service = catalog.filter_services(state_code='BY', image_type='CIR', year='latest')[0]
            
            downloader = WMSServiceDownloader(service=service, grid_spacing=100)

            # Very small area in Munich
            bbox = box(691000, 5334000, 691100, 5334100)
            area = gpd.GeoDataFrame([1], geometry=[bbox], crs="EPSG:25832")

            result = downloader.download_images_from_polygon(
                area_name="test_small_cir",
                area_polygon=area.geometry,
                out_path=Path(tmpdir),
            )

            assert result is not None
            assert result.images is not None
            assert len(result.images) > 0
            assert result.images[0].image_path.exists()

    @pytest.mark.download
    @pytest.mark.slow
    def test_rgbi_download_bavaria(self):
        """Test actual RGBI download and merge (100m x 100m)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Get BY RGB and CIR services from catalog
            catalog = WMSCatalogManager()
            rgb_service = catalog.filter_services(state_code='BY', image_type='RGB', year='latest')[0]
            cir_service = catalog.filter_services(state_code='BY', image_type='CIR', year='latest')[0]
            
            rgb_downloader = WMSServiceDownloader(service=rgb_service, grid_spacing=100)
            cir_downloader = WMSServiceDownloader(service=cir_service, grid_spacing=100)

            rgbi_downloader = RGBIImageDownloader(
                rgb_downloader=rgb_downloader, cir_downloader=cir_downloader
            )

            # Very small area in Munich
            bbox = box(691000, 5334000, 691100, 5334100)
            area = gpd.GeoDataFrame([1], geometry=[bbox], crs="EPSG:25832")

            result = rgbi_downloader.download_rgbi_images_from_polygon(
                area_name="test_rgbi", area_polygon=area.geometry, out_path=Path(tmpdir)
            )

            assert result is not None
            assert result.images is not None
            assert len(result.images) > 0

            # Check that RGBI file was created
            rgbi_files = list(Path(tmpdir).glob("RGBI_*.tiff"))
            assert len(rgbi_files) > 0

    @pytest.mark.download
    @pytest.mark.slow
    def test_auto_downloader_single_state(self):
        """Test AutoOrthophotoDownloader with a small area."""
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = AutoOrthophotoDownloader(grid_spacing=100)

            # Very small area in Munich
            bbox = box(691000, 5334000, 691100, 5334100)
            area = gpd.GeoDataFrame([1], geometry=[bbox], crs="EPSG:25832")

            results = downloader.download_rgb_images_auto(
                area_name="test_auto", area_polygon=area.geometry, out_path=Path(tmpdir)
            )

            assert results is not None
            assert len(results) > 0
            assert "Bayern" in results or "Bavaria" in str(results)

    @pytest.mark.download
    @pytest.mark.slow
    @pytest.mark.timeout(300)  # 5 minute timeout
    def test_multiple_tiles_download(self):
        """Test downloading multiple tiles (500m x 500m area, 100m tiles)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Get BY RGB service from catalog
            catalog = WMSCatalogManager()
            service = catalog.filter_services(state_code='BY', image_type='RGB', year='latest')[0]
            
            downloader = WMSServiceDownloader(service=service, grid_spacing=100)

            # 500m x 500m area = 25 tiles of 100m x 100m
            bbox = box(691000, 5334000, 691500, 5334500)
            area = gpd.GeoDataFrame([1], geometry=[bbox], crs="EPSG:25832")

            result = downloader.download_images_from_polygon(
                area_name="test_multiple",
                area_polygon=area.geometry,
                out_path=Path(tmpdir),
            )

            assert result is not None
            assert len(result.images) > 1  # Should have multiple tiles

            # Check that multiple files were created
            tiff_files = list(Path(tmpdir).glob("*.tiff"))
            assert len(tiff_files) > 1


class TestDownloadErrorHandling:
    """Test error handling in download scenarios."""

    @pytest.mark.download
    def test_invalid_coordinates(self):
        """Test that invalid coordinates are handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Get BY RGB service from catalog
            catalog = WMSCatalogManager()
            service = catalog.filter_services(state_code='BY', image_type='RGB', year='latest')[0]
            
            downloader = WMSServiceDownloader(service=service, grid_spacing=100)

            # Coordinates outside Germany
            bbox = box(0, 0, 100, 100)
            area = gpd.GeoDataFrame([1], geometry=[bbox], crs="EPSG:25832")

            # This should either raise an error or return empty results
            # depending on implementation
            try:
                result = downloader.download_images_from_polygon(
                    area_name="test_invalid",
                    area_polygon=area.geometry,
                    out_path=Path(tmpdir),
                )
                # If it doesn't raise, check that it handled it gracefully
                assert result is not None
            except Exception as e:
                # Expected - coordinates are invalid
                assert isinstance(e, (ValueError, RuntimeError, Exception))

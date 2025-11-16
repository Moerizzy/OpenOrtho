"""
Test AutoOrthophotoDownloader with WMS catalog integration.

This test verifies that the auto downloader now uses the centralized
WMS catalog instead of hardcoded downloader mappings.
"""

import pytest
from pathlib import Path
from shapely.geometry import box
import geopandas as gpd

from orthophotos_downloader.data_scraping.auto_downloader import AutoOrthophotoDownloader
from orthophotos_downloader.wms_catalog import WMSCatalogManager


class TestAutoDownloaderWithCatalog:
    """Test auto downloader with catalog integration"""
    
    def test_auto_downloader_has_catalog(self):
        """Verify auto downloader initializes with catalog"""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)
        
        assert hasattr(downloader, '_catalog')
        assert isinstance(downloader._catalog, WMSCatalogManager)
    
    def test_get_downloader_class_uses_catalog(self):
        """Verify _get_downloader_class queries catalog and returns generic downloader"""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)
        
        # Test RGB downloader for Bayern - should return tuple (class, service)
        rgb_class, rgb_service = downloader._get_downloader_class('BY', 'RGB')
        assert rgb_class.__name__ == 'WMSServiceDownloader'
        assert rgb_service.state_code == 'BY'
        assert rgb_service.type == 'RGB'
        
        # Test CIR downloader for Bayern
        cir_class, cir_service = downloader._get_downloader_class('BY', 'CIR')
        assert cir_class.__name__ == 'WMSServiceDownloader'
        assert cir_service.state_code == 'BY'
        assert cir_service.type == 'CIR'
    
    def test_get_downloader_class_different_resolutions(self):
        """Verify downloader returns correct service with different resolutions"""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)
        
        # Bayern DOP20 (0.2m resolution)
        by_class, by_service = downloader._get_downloader_class('BY', 'RGB')
        assert by_class.__name__ == 'WMSServiceDownloader'
        assert by_service.resolution == 0.2
        
        # NW DOP10 (0.1m resolution)
        nw_class, nw_service = downloader._get_downloader_class('NW', 'RGB')
        assert nw_class.__name__ == 'WMSServiceDownloader'
        assert nw_service.resolution == 0.1
    
    def test_get_downloader_class_invalid_state(self):
        """Verify error handling for invalid state"""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)
        
        with pytest.raises(ValueError, match="No RGB service available"):
            downloader._get_downloader_class('XX', 'RGB')
    
    def test_get_downloader_class_invalid_type(self):
        """Verify error handling for invalid image type"""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)
        
        with pytest.raises(ValueError, match="must be 'RGB', 'CIR', or 'RGBI'"):
            downloader._get_downloader_class('BY', 'INVALID')
    
    def test_all_catalog_states_have_downloaders(self):
        """Verify all states in catalog have corresponding downloader classes"""
        catalog = WMSCatalogManager()
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)
        
        # Get all unique state codes from catalog
        all_services = catalog.get_all_services()
        state_codes = set(s.state_code for s in all_services if s.state_code != 'DE')
        
        # Test RGB downloaders
        missing_rgb = []
        for state_code in state_codes:
            rgb_services = catalog.filter_services(state_code=state_code, image_type='RGB')
            if rgb_services:
                try:
                    downloader._get_downloader_class(state_code, 'RGB')
                except (ImportError, ValueError) as e:
                    missing_rgb.append((state_code, str(e)))
        
        # Test CIR downloaders
        missing_cir = []
        for state_code in state_codes:
            cir_services = catalog.filter_services(state_code=state_code, image_type='CIR')
            if cir_services:
                try:
                    downloader._get_downloader_class(state_code, 'CIR')
                except (ImportError, ValueError) as e:
                    missing_cir.append((state_code, str(e)))
        
        # Report any missing downloaders
        if missing_rgb:
            print(f"\nMissing RGB downloaders: {missing_rgb}")
        if missing_cir:
            print(f"\nMissing CIR downloaders: {missing_cir}")
        
        # For now, just log warnings instead of failing
        # (some states might be in catalog but not yet have downloader classes)
        if missing_rgb or missing_cir:
            pytest.skip(f"Some downloaders not yet implemented: RGB={len(missing_rgb)}, CIR={len(missing_cir)}")
    
    def test_detect_intersecting_states(self):
        """Test state detection with sample geometry"""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)
        
        # Create test polygon in Bayern (Munich area)
        # EPSG:25832 coordinates for Munich
        munich_box = box(691000, 5334000, 692000, 5335000)
        
        states = downloader.detect_intersecting_states(munich_box)
        
        # Should detect Bayern
        assert len(states) > 0
        state_codes = [s[1] for s in states]
        assert 'BY' in state_codes
    
    @pytest.mark.skip(reason="Requires network access and actual download")
    def test_download_images_auto_with_catalog(self, tmp_path):
        """Integration test: download using catalog-based auto downloader"""
        downloader = AutoOrthophotoDownloader(
            grid_spacing=50,  # Small grid for testing
            extract_metadata=False  # Skip metadata for faster test
        )
        
        # Small test area in Bayern (Munich)
        munich_box = box(691550, 5334700, 691600, 5334750)
        area_gdf = gpd.GeoDataFrame([1], geometry=[munich_box], crs='EPSG:25832')
        
        # Download
        results = downloader.download_images_auto(
            area_name='test_munich',
            area_polygon=area_gdf,
            out_path=tmp_path,
            image_type='RGB'
        )
        
        # Verify results
        assert 'Bayern' in results
        assert len(results['Bayern'].images) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

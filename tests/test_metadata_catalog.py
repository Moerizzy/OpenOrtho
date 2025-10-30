"""
Test metadata extraction using WMS catalog configuration.

This test verifies that metadata extraction now reads configuration
from the centralized WMS catalog instead of hardcoded dictionaries.
"""

import pytest
from pathlib import Path
from orthophotos_downloader.wms_catalog import WMSCatalogManager
from orthophotos_downloader.metadata.metadata_extractor import TileMetadataExtractor


class TestMetadataWithCatalog:
    """Test metadata extraction with catalog integration"""
    
    def test_catalog_loads_metadata_config(self):
        """Verify catalog contains metadata configuration"""
        catalog = WMSCatalogManager()
        
        # Bayern should have metadata configuration
        bayern_services = catalog.filter_services(state_code='BY')
        assert len(bayern_services) > 0
        
        bayern_service = bayern_services[0]
        assert hasattr(bayern_service, 'metadata')
        assert isinstance(bayern_service.metadata, dict)
        
        # Check metadata fields
        metadata = bayern_service.metadata
        assert 'metadata_layer' in metadata
        assert metadata['metadata_layer'] == 'by_dop20_info'
    
    def test_extractor_loads_from_catalog(self):
        """Verify metadata extractor loads config from catalog"""
        catalog = WMSCatalogManager()
        services = catalog.filter_services(state_code='BY')
        assert len(services) > 0
        
        service = services[0]
        
        # Initialize extractor with WMSService object
        extractor = TileMetadataExtractor(
            wms_url=service.url,
            state_code='BY',
            wms_service=service
        )
        
        # Verify metadata config is loaded
        assert extractor.metadata_config is not None
        assert isinstance(extractor.metadata_config, dict)
        assert 'metadata_layer' in extractor.metadata_config
        assert extractor.metadata_config['metadata_layer'] == 'by_dop20_info'
    
    def test_extractor_fallback_to_catalog(self):
        """Verify extractor can load from catalog by state code"""
        # Initialize without WMSService object
        extractor = TileMetadataExtractor(
            wms_url='https://geoservices.bayern.de/wms/v2/ogc_dop20_oa.cgi?',
            state_code='BY'
        )
        
        # Should still load metadata config from catalog
        assert extractor.metadata_config is not None
        assert 'metadata_layer' in extractor.metadata_config
    
    def test_states_with_metadata_services(self):
        """Verify all states with metadata configuration"""
        catalog = WMSCatalogManager()
        
        # States that should have metadata configs
        states_with_metadata = [
            'BE', 'BB', 'BW', 'BY', 'HE', 'MV', 
            'NI', 'NW', 'RP', 'SH', 'SL', 'SN', 'ST', 'TH'
        ]
        
        for state_code in states_with_metadata:
            services = catalog.filter_services(state_code=state_code)
            if services:
                service = services[0]
                assert hasattr(service, 'metadata'), f"{state_code} missing metadata"
                assert service.metadata, f"{state_code} has empty metadata"
                assert 'metadata_layer' in service.metadata, \
                    f"{state_code} missing metadata_layer"
    
    def test_metadata_service_urls(self):
        """Verify dedicated metadata service URLs are in catalog"""
        catalog = WMSCatalogManager()
        
        # States with dedicated metadata services (different from image service)
        dedicated_metadata_states = {
            'BE': 'isk.geobasis-bb.de',
            'BB': 'isk.geobasis-bb.de',
            'BW': 'owsproxy.lgl-bw.de',
            'SH': 'service.gdi-sh.de',
        }
        
        for state_code, expected_domain in dedicated_metadata_states.items():
            services = catalog.filter_services(state_code=state_code)
            if services:
                service = services[0]
                metadata_url = service.metadata.get('metadata_service_url')
                assert metadata_url is not None, \
                    f"{state_code} missing metadata_service_url"
                assert expected_domain in metadata_url, \
                    f"{state_code} metadata URL doesn't contain {expected_domain}"
    
    def test_metadata_wms_versions(self):
        """Verify WMS versions are configured for metadata services"""
        catalog = WMSCatalogManager()
        
        # Check a few states for WMS version configuration
        test_cases = [
            ('BY', '1.1.1'),  # Bayern uses 1.1.1 for metadata
            ('NI', '1.3.0'),  # Niedersachsen uses 1.3.0
            ('SH', '1.1.1'),  # Schleswig-Holstein uses 1.1.1
        ]
        
        for state_code, expected_version in test_cases:
            services = catalog.filter_services(state_code=state_code)
            if services:
                service = services[0]
                wms_version = service.metadata.get('metadata_wms_version')
                assert wms_version == expected_version, \
                    f"{state_code} expected WMS {expected_version}, got {wms_version}"
    
    def test_metadata_info_formats(self):
        """Verify INFO_FORMAT is configured correctly"""
        catalog = WMSCatalogManager()
        
        # States that return HTML instead of text/plain
        html_states = ['NI', 'SL', 'ST']
        
        for state_code in html_states:
            services = catalog.filter_services(state_code=state_code)
            if services:
                service = services[0]
                info_format = service.metadata.get('metadata_info_format')
                assert info_format == 'text/html', \
                    f"{state_code} should use text/html, got {info_format}"
    
    @pytest.mark.skip(reason="Requires network access and may be slow")
    def test_actual_metadata_query_bayern(self):
        """Integration test: actually query Bayern metadata service"""
        catalog = WMSCatalogManager()
        services = catalog.filter_services(state_code='BY', image_type='RGB')
        assert len(services) > 0
        
        service = services[0]
        extractor = TileMetadataExtractor(
            wms_url=service.url,
            state_code='BY',
            wms_service=service
        )
        
        # Query metadata for Munich Marienplatz
        # EPSG:25832 coordinates
        metadata = extractor._query_wms_metadata(
            center_x=691603,
            center_y=5334780,
            crs='EPSG:25832'
        )
        
        # Should get some response (might be error or actual data)
        assert isinstance(metadata, dict)
        # If successful, should have some metadata fields
        # (exact fields depend on WMS response)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

"""
Example: Extract metadata for downloaded orthophoto tiles using WMS catalog.

This example demonstrates how metadata extraction now works with the
centralized WMS catalog configuration instead of hardcoded values.
"""

from pathlib import Path
from orthophotos_downloader.wms_catalog import WMSCatalogManager, WMSDiscovery
from orthophotos_downloader.metadata.metadata_extractor import TileMetadataExtractor


def example_metadata_extraction_with_catalog():
    """
    Example showing metadata extraction using catalog configuration.
    """
    print("=" * 70)
    print("Metadata Extraction with WMS Catalog")
    print("=" * 70)
    
    # 1. Discover WMS service using catalog
    print("\n1. Finding WMS service for Munich (Bayern)...")
    catalog = WMSCatalogManager()
    
    # Get Bayern RGB service
    services = catalog.filter_services(
        state_code='BY',
        image_type='RGB'
    )
    
    if not services:
        print("❌ No services found for Bayern")
        return
    
    # Use first Bayern service
    service = services[0]
    print(f"✅ Found service: {service.state_name} ({service.id})")
    print(f"   Resolution: {service.resolution}")
    print(f"   URL: {service.url}")
    
    # 2. Check metadata configuration in catalog
    print("\n2. Checking metadata configuration...")
    if hasattr(service, 'metadata') and service.metadata:
        print("✅ Metadata configuration found in catalog:")
        for key, value in service.metadata.items():
            if isinstance(value, dict):
                print(f"   {key}:")
                for k, v in value.items():
                    print(f"      {k}: {v}")
            else:
                print(f"   {key}: {value}")
    else:
        print("❌ No metadata configuration available")
        return
    
    # 3. Create metadata extractor using service from catalog
    print("\n3. Creating metadata extractor...")
    extractor = TileMetadataExtractor(
        wms_url=service.url,
        state_code=service.state_code,
        wms_service=service  # Pass WMSService object
    )
    print(f"✅ Extractor initialized for {service.state_code}")
    print(f"   Using metadata layer: {extractor.metadata_config.get('metadata_layer')}")
    print(f"   WMS version: {extractor.metadata_config.get('metadata_wms_version')}")
    
    # 4. Check if we have downloaded tiles
    print("\n4. Looking for downloaded tiles...")
    test_download_dir = Path(__file__).parent.parent / 'data' / 'test_downloads_bayern'
    
    if test_download_dir.exists():
        tile_files = list(test_download_dir.glob('*.tiff'))
        if tile_files:
            print(f"✅ Found {len(tile_files)} tiles in {test_download_dir}")
            
            # Extract metadata from first tile
            tile_path = tile_files[0]
            print(f"\n5. Extracting metadata from: {tile_path.name}")
            
            # Parse coordinates from filename (e.g., bayern_32_691550_5334700.tiff)
            parts = tile_path.stem.split('_')
            if len(parts) >= 4:
                center_x = int(parts[2]) + 25  # Center of 50m tile
                center_y = int(parts[3]) + 25
                
                print(f"   Tile center: ({center_x}, {center_y}) EPSG:25832")
                
                # Extract metadata
                try:
                    metadata = extractor.extract_tile_metadata(
                        tile_path=tile_path,
                        center_x=center_x,
                        center_y=center_y,
                        crs='EPSG:25832'
                    )
                    
                    print("\n✅ Metadata extracted:")
                    for key, value in metadata.items():
                        print(f"   {key}: {value}")
                        
                except Exception as e:
                    print(f"⚠️  Metadata extraction failed: {e}")
        else:
            print(f"ℹ️  No tiles found in {test_download_dir}")
    else:
        print(f"ℹ️  Download directory not found: {test_download_dir}")
        print("   Run download examples first to create test tiles")


def list_all_metadata_configs():
    """
    List all states with metadata configuration in the catalog.
    """
    print("\n" + "=" * 70)
    print("States with Metadata Configuration")
    print("=" * 70)
    
    catalog = WMSCatalogManager()
    all_services = catalog.get_all_services()
    
    # Group by state
    states_with_metadata = {}
    for service in all_services:
        if hasattr(service, 'metadata') and service.metadata:
            if service.state_code not in states_with_metadata:
                states_with_metadata[service.state_code] = service
    
    print(f"\nFound {len(states_with_metadata)} states with metadata services:\n")
    
    for state_code in sorted(states_with_metadata.keys()):
        service = states_with_metadata[state_code]
        metadata = service.metadata
        
        print(f"{state_code} - {service.state_name}")
        print(f"  Layer: {metadata.get('metadata_layer')}")
        print(f"  WMS Version: {metadata.get('metadata_wms_version')}")
        print(f"  Format: {metadata.get('metadata_info_format', 'text/plain')}")
        
        # Check if dedicated metadata service
        metadata_url = metadata.get('metadata_service_url')
        if metadata_url:
            print(f"  Dedicated metadata service: {metadata_url[:60]}...")
        else:
            print(f"  Uses same URL as image service")
        print()


def compare_old_vs_new_approach():
    """
    Show the difference between old (hardcoded) and new (catalog) approach.
    """
    print("\n" + "=" * 70)
    print("Old vs New Approach")
    print("=" * 70)
    
    print("\n❌ OLD APPROACH (Hardcoded):")
    print("""
    # Hardcoded dictionaries in metadata_extractor.py
    METADATA_LAYERS = {
        'BY': 'by_dop20_info',
        'BW': None,
        # ... etc
    }
    
    METADATA_SERVICES = {
        'BE': {
            'url': 'https://isk.geobasis-bb.de/...',
            'layer': 'bb_dop_info',
            # ... etc
        }
    }
    
    # Problems:
    # - Duplicated configuration
    # - Hard to maintain
    # - Not linked to WMS service catalog
    """)
    
    print("\n✅ NEW APPROACH (Catalog-based):")
    print("""
    # All configuration in wms_services.yaml
    - id: bayern_dop20_rgb
      state_code: BY
      metadata:
        metadata_layer: by_dop20_info
        metadata_wms_version: '1.1.1'
        # ... etc
    
    # Code usage:
    catalog = WMSCatalogManager()
    service = catalog.filter_services(state_code='BY')[0]
    
    extractor = TileMetadataExtractor(
        wms_url=service.url,
        state_code='BY',
        wms_service=service  # Metadata config automatically loaded!
    )
    
    # Benefits:
    # - Single source of truth
    # - Easy to maintain and update
    # - Linked to WMS service configuration
    # - No code changes needed for new states
    """)


if __name__ == '__main__':
    # Run examples
    example_metadata_extraction_with_catalog()
    list_all_metadata_configs()
    compare_old_vs_new_approach()
    
    print("\n" + "=" * 70)
    print("✅ Metadata extraction now uses centralized WMS catalog!")
    print("=" * 70)

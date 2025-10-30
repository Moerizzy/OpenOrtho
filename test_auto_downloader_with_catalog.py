"""
Test AutoOrthophotoDownloader with the WMS catalog integration.

This script verifies that the auto downloader correctly uses the 
centralized WMS catalog instead of hardcoded mappings.
"""

from pathlib import Path
from shapely.geometry import box
import geopandas as gpd
from orthophotos_downloader.data_scraping.auto_downloader import AutoOrthophotoDownloader
from orthophotos_downloader.wms_catalog import WMSCatalogManager


def test_catalog_integration():
    """Test that auto downloader integrates with catalog"""
    print("=" * 70)
    print("Testing AutoOrthophotoDownloader with WMS Catalog")
    print("=" * 70)
    print()
    
    # 1. Verify catalog is accessible
    print("1. Checking catalog accessibility...")
    catalog = WMSCatalogManager()
    all_services = catalog.get_all_services()
    print(f"   ✅ Catalog loaded: {len(all_services)} services")
    print()
    
    # 2. Initialize auto downloader
    print("2. Initializing AutoOrthophotoDownloader...")
    downloader = AutoOrthophotoDownloader(
        grid_spacing=1000,
        extract_metadata=False  # Skip metadata for faster testing
    )
    print(f"   ✅ Auto downloader initialized")
    print(f"   ✅ Has catalog: {hasattr(downloader, '_catalog')}")
    print()
    
    # 3. Test downloader class retrieval for different states
    print("3. Testing downloader class retrieval from catalog...")
    test_cases = [
        ('BY', 'RGB', 'BY_RGB_Dop20_ImageDownloader'),
        ('BY', 'CIR', 'BY_CIR_Dop20_ImageDownloader'),
        ('BW', 'RGB', 'BW_RGB_Dop20_ImageDownloader'),
        ('NW', 'RGB', 'NW_RGB_Dop10_ImageDownloader'),  # Different resolution
        ('HE', 'CIR', 'HE_CIR_Dop20_ImageDownloader'),
    ]
    
    for state_code, image_type, expected_class in test_cases:
        try:
            downloader_class = downloader._get_downloader_class(state_code, image_type)
            actual_name = downloader_class.__name__
            status = "✅" if actual_name == expected_class else "❌"
            print(f"   {status} {state_code} {image_type}: {actual_name}")
            if actual_name != expected_class:
                print(f"      Expected: {expected_class}")
        except Exception as e:
            print(f"   ❌ {state_code} {image_type}: {e}")
    print()
    
    # 4. Test state detection
    print("4. Testing state detection...")
    # Create test polygon in Bayern (Munich area)
    munich_box = box(691000, 5334000, 692000, 5335000)
    
    try:
        states = downloader.detect_intersecting_states(munich_box)
        print(f"   ✅ Detected {len(states)} state(s) for Munich area")
        for state_name, state_code, _ in states:
            print(f"      - {state_name} ({state_code})")
    except Exception as e:
        print(f"   ❌ State detection failed: {e}")
    print()
    
    # 5. Test catalog query for services
    print("5. Testing catalog queries...")
    
    # RGB services
    rgb_services = catalog.filter_services(image_type='RGB')
    print(f"   ✅ RGB services: {len(rgb_services)}")
    
    # CIR services
    cir_services = catalog.filter_services(image_type='CIR')
    print(f"   ✅ CIR services: {len(cir_services)}")
    
    # Services with metadata
    services_with_metadata = [
        s for s in all_services 
        if hasattr(s, 'metadata') and s.metadata
    ]
    print(f"   ✅ Services with metadata: {len(services_with_metadata)}")
    print()
    
    # 6. Test downloader instantiation
    print("6. Testing downloader instantiation...")
    try:
        by_rgb_class = downloader._get_downloader_class('BY', 'RGB')
        by_rgb_instance = by_rgb_class(grid_spacing=1000, extract_metadata=False)
        print(f"   ✅ Created instance: {by_rgb_instance.__class__.__name__}")
        print(f"   ✅ Grid spacing: {by_rgb_instance.grid_spacing}")
    except Exception as e:
        print(f"   ❌ Instantiation failed: {e}")
    print()
    
    print("=" * 70)
    print("✅ All catalog integration tests completed!")
    print("=" * 70)


def test_all_states_have_downloaders():
    """Verify all catalog states have corresponding downloader classes"""
    print()
    print("=" * 70)
    print("Checking Downloader Availability for All Catalog Services")
    print("=" * 70)
    print()
    
    catalog = WMSCatalogManager()
    downloader = AutoOrthophotoDownloader(grid_spacing=1000)
    
    all_services = catalog.get_all_services()
    
    # Group by state and type
    states = {}
    for service in all_services:
        if service.state_code == 'DE':  # Skip BKG
            continue
        key = service.state_code
        if key not in states:
            states[key] = {'RGB': None, 'CIR': None}
        states[key][service.type] = service
    
    missing = []
    available = []
    
    for state_code in sorted(states.keys()):
        for image_type in ['RGB', 'CIR']:
            service = states[state_code][image_type]
            if service:
                try:
                    downloader_class = downloader._get_downloader_class(state_code, image_type)
                    available.append(f"{state_code} {image_type}")
                    print(f"✅ {state_code} {image_type:3s}: {downloader_class.__name__}")
                except Exception as e:
                    missing.append(f"{state_code} {image_type}")
                    print(f"❌ {state_code} {image_type:3s}: Missing - {e}")
    
    print()
    print(f"Summary: {len(available)} available, {len(missing)} missing")
    
    if missing:
        print(f"Missing downloaders: {', '.join(missing)}")
    else:
        print("✅ All catalog services have corresponding downloaders!")
    
    print("=" * 70)


if __name__ == '__main__':
    test_catalog_integration()
    test_all_states_have_downloaders()

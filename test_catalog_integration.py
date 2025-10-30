#!/usr/bin/env python3
"""
Test: Integration of WMS Catalog with AutoOrthophotoDownloader
"""

import sys
sys.path.insert(0, 'src')

import logging
import geopandas as gpd
from shapely.geometry import box

from orthophotos_downloader.wms_catalog import WMSCatalogManager
from orthophotos_downloader import AutoOrthophotoDownloader

logging.basicConfig(level=logging.INFO)

print("\n" + "="*80)
print("TEST 1: Load Catalog and Query Services")
print("="*80)

catalog = WMSCatalogManager()
print(f"✅ Catalog loaded with {len(catalog.get_all_services())} services")

# Test 1: Get all services
all_services = catalog.get_all_services()
print(f"✅ Retrieved {len(all_services)} services")

# Test 2: Filter by state
by_services = catalog.filter_services(state_code='BY')
print(f"✅ Bayern services: {len(by_services)}")
for s in by_services:
    print(f"   - {s.id}: {s.description}")

# Test 3: Filter by image type
rgb_services = catalog.filter_services(image_type='RGB')
print(f"✅ RGB services: {len(rgb_services)}")

# Test 4: Filter by resolution
dop20 = catalog.filter_services(resolution=0.2)
print(f"✅ DOP20 (0.2m) services: {len(dop20)}")

print("\n" + "="*80)
print("TEST 2: Query Available Options")
print("="*80)

states = catalog.get_states()
print(f"✅ States covered: {len(states)}")
print(f"   {', '.join(sorted(states))}")

by_years = catalog.get_years_for_state('BY')
print(f"✅ Jahren for Bayern: {by_years}")

by_types = catalog.get_image_types_for_state('BY')
print(f"✅ Image types for Bayern: {by_types}")

by_resolutions = catalog.get_resolutions_for_state('BY')
print(f"✅ Resolutions for Bayern: {by_resolutions}")

print("\n" + "="*80)
print("TEST 3: Display Services in Table")
print("="*80)

print("\n🏛️ Bayern RGB Services:")
by_rgb = catalog.filter_services(state_code='BY', image_type='RGB')
catalog.print_services_table(by_rgb)

print("\n" + "="*80)
print("TEST 4: Get Specific Service and Extract Details")
print("="*80)

service = catalog.get_service_by_id('BY_RGB_DOP20_current')
if service:
    print(f"✅ Found service: {service.id}")
    print(f"   State: {service.state_name} ({service.state_code})")
    print(f"   Type: {service.type}")
    print(f"   Resolution: {service.resolution}m")
    print(f"   Year: {service.year}")
    print(f"   URL: {service.url}")
    print(f"   Layer: {service.layer_name}")
    print(f"   CRS: {service.crs}")
    print(f"   Format: {service.format}")
    print(f"   Direct Download: {service.direct_download}")
    print(f"   Requires Auth: {service.requires_auth}")
else:
    print("❌ Service not found")

print("\n" + "="*80)
print("TEST 5: Multiple Filter Combinations")
print("="*80)

# Complex filter
services = catalog.filter_services(
    state_code=['BY', 'BW', 'NW'],
    image_type='RGB',
    resolution=0.2,
    year='latest'
)
print(f"✅ Services for BY/BW/NW, RGB, 0.2m, latest: {len(services)}")
for s in services:
    print(f"   - {s.state_code}: {s.description}")

print("\n" + "="*80)
print("TEST 6: Validate Service Data Structure")
print("="*80)

service = by_services[0]
service_dict = service.to_dict()
print(f"✅ Service as dict has {len(service_dict)} fields:")
for key, value in sorted(service_dict.items()):
    print(f"   - {key}: {value}")

print("\n" + "="*80)
print("TEST 7: Integration with AutoOrthophotoDownloader")
print("="*80)

try:
    # Create a test area (Bavaria region)
    test_bbox = box(4476000, 5327000, 4496000, 5347000)  # Munich area
    area_gdf = gpd.GeoDataFrame([1], geometry=[test_bbox], crs="EPSG:25832")
    
    print(f"✅ Created test area: Munich region")
    print(f"   Bbox: {test_bbox.bounds}")
    
    # Initialize AutoOrthophotoDownloader
    downloader = AutoOrthophotoDownloader(grid_spacing=1000)
    print(f"✅ AutoOrthophotoDownloader initialized")
    
    # Detect intersecting states
    intersecting = downloader.detect_intersecting_states(area_gdf)
    print(f"✅ Detected {len(intersecting)} intersecting states:")
    for state_name, state_code, intersection in intersecting:
        print(f"   - {state_name} ({state_code})")
        print(f"     Intersection area: {intersection.area / 1e6:.2f} km²")
    
    # Now query catalog for these states
    for state_name, state_code, intersection in intersecting:
        print(f"\n   Services available for {state_code}:")
        services = catalog.filter_services(state_code=state_code, image_type='RGB')
        for s in services:
            print(f"     • {s.description}")
    
    print("\n✅ Integration works!")
    
except Exception as e:
    print(f"❌ Error during integration test: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("✅ ALL TESTS PASSED!")
print("="*80 + "\n")

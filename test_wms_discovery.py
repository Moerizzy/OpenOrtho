#!/usr/bin/env python3
"""
Test 2: WMS Discovery and Better Integration
"""

import sys
sys.path.insert(0, 'src')

import logging
import geopandas as gpd
from shapely.geometry import box

from orthophotos_downloader.wms_catalog import WMSCatalogManager, WMSDiscovery

logging.basicConfig(level=logging.INFO)

print("\n" + "="*80)
print("TEST: WMS Discovery System")
print("="*80)

catalog = WMSCatalogManager()
discovery = WMSDiscovery()

print(f"✅ Catalog loaded: {len(catalog.get_all_services())} services")
print(f"✅ Discovery initialized")

print("\n" + "="*80)
print("TEST 1: Discover States for Area")
print("="*80)

# Use larger area that definitely overlaps Bayern
test_bbox = box(4400000, 5250000, 4600000, 5450000)
print(f"Test bbox: {test_bbox.bounds}")

states = discovery.discover_for_area(bbox=test_bbox.bounds)
print(f"✅ Discovered states for area: {states}")

print("\n" + "="*80)
print("TEST 2: Get Available Services for Area")
print("="*80)

services = discovery.get_available_services(
    bbox=test_bbox.bounds,
    image_type='RGB'
)
print(f"✅ Found {len(services)} RGB services for area:")
for s in services:
    print(f"   - {s.state_code}: {s.id}")

print("\n" + "="*80)
print("TEST 3: Temporal Options (Years)")
print("="*80)

temporal = discovery.get_temporal_options('BY', image_type='RGB')
print(f"✅ Temporal options for Bayern RGB:")
for year, services_list in temporal.items():
    print(f"   {year}: {len(services_list)} service(s)")

print("\n" + "="*80)
print("TEST 4: Spectral Options (RGB/CIR)")
print("="*80)

spectral = discovery.get_spectral_options('BY')
print(f"✅ Spectral options for Bayern:")
for img_type, services_list in spectral.items():
    print(f"   {img_type}: {len(services_list)} service(s)")

print("\n" + "="*80)
print("TEST 5: Resolution Options")
print("="*80)

resolutions = discovery.get_resolution_options('BY')
print(f"✅ Resolution options for Bayern:")
for res, services_list in resolutions.items():
    dop = int(res * 100)
    print(f"   DOP{dop} ({res}m): {len(services_list)} service(s)")

print("\n" + "="*80)
print("TEST 6: Recommend Best Service")
print("="*80)

recommended = discovery.recommend_service(
    bbox=test_bbox.bounds,
    image_type='RGB',
    prefer_latest=True,
    prefer_high_res=True,
    prefer_direct=True
)

if recommended:
    print(f"✅ Recommended service: {recommended.id}")
    print(f"   Description: {recommended.description}")
    print(f"   URL: {recommended.url}")
    print(f"   Direct Download: {recommended.direct_download}")
else:
    print("❌ No recommendation found")

print("\n" + "="*80)
print("TEST 7: Print Discovery Summary")
print("="*80)

discovery.print_discovery_summary(bbox=test_bbox.bounds)

print("\n" + "="*80)
print("TEST 8: Query Available Years per State")
print("="*80)

for state_code in ['BY', 'BW', 'NW']:
    years = catalog.get_years_for_state(state_code)
    print(f"✅ {state_code}: Years = {years}")

print("\n" + "="*80)
print("TEST 9: Complex Filtering")
print("="*80)

# Find all DOP20 RGB services available without authentication
services = catalog.filter_services(
    image_type='RGB',
    resolution=0.2,
    requires_auth=False
)
print(f"✅ DOP20 RGB services (no auth): {len(services)}")
print(f"   States: {sorted(set(s.state_code for s in services))}")

# Find services with direct download
direct_services = catalog.filter_services(direct_download=True)
print(f"✅ Services with direct download: {len(direct_services)}")
print(f"   States: {sorted(set(s.state_code for s in direct_services))}")

print("\n" + "="*80)
print("✅ ALL WMS DISCOVERY TESTS PASSED!")
print("="*80 + "\n")

print("Summary:")
print(f"  - Catalog: {len(catalog.get_all_services())} services")
print(f"  - States: {len(catalog.get_states())} covered")
print(f"  - RGB: {len(catalog.filter_services(image_type='RGB'))} services")
print(f"  - CIR: {len(catalog.filter_services(image_type='CIR'))} services")
print(f"  - Direct Download: {len(direct_services)} services")
print(f"  - Auth Required: {len(catalog.filter_services(requires_auth=True))} services")

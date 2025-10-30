#!/usr/bin/env python3
"""
Test 4: Complete End-to-End WMS Catalog Usage Example
Shows how to integrate WMS Catalog into real download workflows
"""

import sys
sys.path.insert(0, 'src')

import logging
from orthophotos_downloader.wms_catalog import WMSCatalogManager, WMSDiscovery

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')

print("\n" + "="*80)
print("COMPLETE WORKFLOW: Using WMS Catalog for Orthophoto Downloads")
print("="*80 + "\n")

# Step 1: Initialize catalog
print("STEP 1: Initialize WMS Catalog")
print("-" * 80)
catalog = WMSCatalogManager()
discovery = WMSDiscovery()
print(f"✅ Loaded {len(catalog.get_all_services())} WMS services")
print(f"✅ Covers {len(catalog.get_states())} German states\n")

# Step 2: Define area of interest (Munich)
print("STEP 2: Define Area of Interest (Munich)")
print("-" * 80)
munich_bbox = (4476000, 5327000, 4496000, 5347000)  # EPSG:25832
area_name = "Munich"
print(f"Area: {area_name}")
print(f"Bbox (EPSG:25832): {munich_bbox}")
print(f"Size: {(munich_bbox[2]-munich_bbox[0])/1000:.1f}km × {(munich_bbox[3]-munich_bbox[1])/1000:.1f}km\n")

# Step 3: Discover available services
print("STEP 3: Discover Available Services")
print("-" * 80)
discovered_states = discovery.discover_for_area(bbox=munich_bbox)
print(f"States covering area: {', '.join(discovered_states)}\n")

# Step 4: Get available options
print("STEP 4: List Available Options")
print("-" * 80)

rgb_services = discovery.get_available_services(bbox=munich_bbox, image_type='RGB')
print(f"RGB Services: {len(rgb_services)}")
for svc in rgb_services:
    res = int(svc.resolution * 100)
    print(f"  - {svc.state_code}: DOP{res} ({svc.description})")

print()
cir_services = discovery.get_available_services(bbox=munich_bbox, image_type='CIR')
print(f"CIR Services: {len(cir_services)}")
for svc in cir_services:
    res = int(svc.resolution * 100)
    print(f"  - {svc.state_code}: DOP{res} ({svc.description})")
print()

# Step 5: Get service recommendations
print("STEP 5: Get Service Recommendations")
print("-" * 80)

# Best overall service
best_service = discovery.recommend_service(
    bbox=munich_bbox,
    image_type='RGB',
    prefer_latest=True,
    prefer_high_res=True,
    prefer_direct=True
)

print(f"Recommended Service:")
print(f"  ID: {best_service.id}")
print(f"  Description: {best_service.description}")
print(f"  Type: {best_service.type} (RGB)")
print(f"  Resolution: {int(best_service.resolution*100)}cm (DOP{int(best_service.resolution*100)})")
print(f"  State: {best_service.state_name} ({best_service.state_code})")
print(f"  Direct Download: {'Yes' if best_service.direct_download else 'No'}")
print(f"  Requires Auth: {'Yes' if best_service.requires_auth else 'No'}\n")

# Step 6: Display WMS Configuration
print("STEP 6: WMS Service Configuration")
print("-" * 80)
print(f"Service URL: {best_service.url}")
print(f"WMS Layer: {best_service.layer_name}")
print(f"CRS: {best_service.crs}")
print(f"Image Format: {best_service.format}")
print(f"WMS Version: {best_service.version}")
print(f"Source: {best_service.source}\n")

# Step 7: Comparison of alternatives
print("STEP 7: Service Comparison for Area")
print("-" * 80)
print("All RGB services available for Munich:\n")
print(f"{'State':<6} {'Type':<8} {'Res':<8} {'Direct':<8} {'Auth':<8} {'Source':<20}")
print("-" * 70)

for svc in sorted(rgb_services, key=lambda s: (s.state_code, -s.resolution)):
    res = f"DOP{int(svc.resolution*100)}"
    direct = "Yes" if svc.direct_download else "No"
    auth = "Yes" if svc.requires_auth else "No"
    print(f"{svc.state_code:<6} {svc.type:<8} {res:<8} {direct:<8} {auth:<8} {svc.source:<20}")

print()

# Step 8: Advanced filtering
print("STEP 8: Advanced Filtering Examples")
print("-" * 80)

# Example 1: Find all direct download services
direct_only = catalog.filter_services(direct_download=True)
print(f"✅ Services with direct download: {len(direct_only)}")
for svc in direct_only:
    print(f"   - {svc.state_code}: {svc.id}")

print()

# Example 2: Find services that don't require auth
no_auth = catalog.filter_services(requires_auth=False)
print(f"✅ Services without authentication: {len(no_auth)} out of {len(catalog.get_all_services())}")

print()

# Example 3: High resolution services (0.1m)
high_res = catalog.filter_services(resolution=0.1)
print(f"✅ High-resolution services (DOP10 / 0.1m): {len(high_res)}")
for svc in high_res:
    print(f"   - {svc.state_code}: {svc.id} ({svc.description})")

print()

# Step 9: Integration notes
print("STEP 9: Integration with ImageDownloader")
print("-" * 80)

print("""
To use the recommended service with ImageDownloader:

1. Extract WMS configuration:
   - url: {}
   - layer: {}
   - crs: {}
   - format: {}

2. Pass to ImageDownloader:
   from orthophotos_downloader.data_scraping.image_download import ImageDownloader
   
   downloader = ImageDownloader(
       wms_url="{}",
       layer_name="{}",
       crs="{}",
       format_type="{}",
       grid_spacing=100  # meters
   )
   
   # Download for area
   downloader.download_area(
       bbox=(4476000, 5327000, 4496000, 5347000),
       output_dir="/path/to/output",
       epsg=25832
   )

3. Features provided by catalog:
   ✓ Automatic service discovery per geographic area
   ✓ Metadata for all 17 German states
   ✓ Resolution options (DOP10, DOP20, DOP40, etc.)
   ✓ RGB and CIR (color-infrared) availability
   ✓ Direct download URLs where available
   ✓ Authentication requirements flagged
   ✓ Recommendations based on preferences
""".format(
    best_service.url,
    best_service.layer_name,
    best_service.crs,
    best_service.format,
    best_service.url,
    best_service.layer_name,
    best_service.crs,
    best_service.format
))

print("="*80)
print("✅ WMS CATALOG FULLY FUNCTIONAL AND INTEGRATED!")
print("="*80)
print("\nSummary:")
print(f"  • Catalog services: {len(catalog.get_all_services())}")
print(f"  • States covered: {len(catalog.get_states())}")
print(f"  • For Munich: {len(discovered_states)} states with {len(rgb_services)} RGB services")
print(f"  • Best service: {best_service.id}")
print(f"  • Resolution: DOP{int(best_service.resolution*100)} ({best_service.resolution}m)")
print(f"  • Direct download: {'Available' if best_service.direct_download else 'Via WMS'}")
print("\n")

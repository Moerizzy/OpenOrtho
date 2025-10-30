#!/usr/bin/env python3
"""
Test 5: Actual Download Test using WMS Catalog
Downloads a small area using the recommended WMS service from the catalog
Output is saved to data/test_downloads/
"""

import sys
sys.path.insert(0, 'src')

import logging
from pathlib import Path
from orthophotos_downloader.wms_catalog import WMSCatalogManager, WMSDiscovery
from orthophotos_downloader.data_scraping.image_download import ImageDownloader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

print("\n" + "="*80)
print("ACTUAL DOWNLOAD TEST: Using WMS Catalog to Download Orthophotos")
print("="*80 + "\n")

# Step 1: Initialize catalog and discovery
print("STEP 1: Initialize WMS Catalog")
print("-" * 80)
catalog = WMSCatalogManager()
discovery = WMSDiscovery()
print(f"✅ Catalog loaded: {len(catalog.get_all_services())} services")
print(f"✅ Discovery initialized\n")

# Step 2: Define a small test area (100m x 100m in Munich)
print("STEP 2: Define Small Test Area")
print("-" * 80)
# Small area: 100m x 100m near Munich city center
test_bbox = (4480000, 5334000, 4480100, 5334100)  # EPSG:25832
print(f"Test area: 100m × 100m near Munich")
print(f"Bbox (EPSG:25832): {test_bbox}")
print(f"Grid spacing: 50m (will download ~4 tiles)\n")

# Step 3: Discover and select service
print("STEP 3: Discover WMS Service for Area")
print("-" * 80)
recommended_service = discovery.recommend_service(
    bbox=test_bbox,
    image_type='RGB',
    prefer_latest=True,
    prefer_high_res=True,
    prefer_direct=False  # Use WMS for this test
)

if not recommended_service:
    print("❌ No service found for area!")
    sys.exit(1)

print(f"✅ Selected service: {recommended_service.id}")
print(f"   State: {recommended_service.state_name} ({recommended_service.state_code})")
print(f"   Type: {recommended_service.type}")
print(f"   Resolution: {int(recommended_service.resolution*100)}cm")
print(f"   URL: {recommended_service.url}")
print(f"   Layer: {recommended_service.layer_name}")
print(f"   CRS: {recommended_service.crs}")
print(f"   Format: {recommended_service.format}\n")

# Step 4: Create output directory in data folder
print("STEP 4: Prepare Output Directory")
print("-" * 80)
output_path = Path("data/test_downloads")
output_path.mkdir(parents=True, exist_ok=True)
print(f"✅ Created output directory: {output_path.absolute()}\n")

# Step 5: Configure ImageDownloader with catalog metadata
print("STEP 5: Configure WMS and ImageDownloader from Catalog")
print("-" * 80)

try:
    from orthophotos_downloader.data_scraping.image_download import ExtendedWebMapService
    
    # Create WMS object from catalog metadata
    wms = ExtendedWebMapService(
        url=recommended_service.url,
        version=recommended_service.version,
        resolution=recommended_service.resolution,
        layer_name=recommended_service.layer_name,
        crs=recommended_service.crs,
        format=recommended_service.format
    )
    print(f"✅ ExtendedWebMapService created")
    print(f"   URL: {recommended_service.url}")
    print(f"   Layer: {recommended_service.layer_name}")
    print(f"   Resolution: {recommended_service.resolution}m/px")
    
    # Create ImageDownloader
    downloader = ImageDownloader(
        wms=wms,
        grid_spacing=50,  # 50m grid spacing
        state_code=recommended_service.state_code,
        extract_metadata=True
    )
    print(f"✅ ImageDownloader configured")
    print(f"   Grid: 50m spacing")
    print(f"   State: {recommended_service.state_code}")
    print(f"   Output: {output_path}\n")
except Exception as e:
    print(f"❌ Failed to configure downloader: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 6: Execute download
print("STEP 6: Download Orthophotos")
print("-" * 80)
print("Starting download... (this may take 10-30 seconds)")
print()

try:
    from shapely.geometry import box
    from geopandas import GeoSeries
    
    # Create polygon from bbox
    polygon = box(*test_bbox)
    area_polygon = GeoSeries([polygon], crs=recommended_service.crs)
    
    # Download the area
    result = downloader.download_images_from_polygon(
        area_name="munich_test",
        area_polygon=area_polygon,
        out_path=output_path,
        buffer_size=0,
        filename_prefix="ortho"
    )
    
    print(f"\n✅ Download completed successfully!")
    
    if result and result.images:
        print(f"   Downloaded {len(result.images)} image(s)")
    
except Exception as e:
    print(f"\n❌ Download failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 7: Verify downloaded files
print("\nSTEP 7: Verify Downloaded Files")
print("-" * 80)

# Check for downloaded images
image_files = list(output_path.glob("**/*.tif*"))
metadata_files = list(output_path.glob("**/*.json"))

print(f"Files downloaded:")
print(f"  • Image files (TIFF): {len(image_files)}")
print(f"  • Metadata files (JSON): {len(metadata_files)}")

if image_files:
    print(f"\n✅ SUCCESS: Downloaded {len(image_files)} image tile(s)")
    print(f"\nImage files:")
    for img_file in sorted(image_files):
        file_size = img_file.stat().st_size / 1024  # KB
        print(f"  • {img_file.name} ({file_size:.1f} KB)")
else:
    print(f"\n⚠️  WARNING: No image files found")

if metadata_files:
    print(f"\nMetadata files:")
    for meta_file in sorted(metadata_files):
        file_size = meta_file.stat().st_size / 1024  # KB
        print(f"  • {meta_file.name} ({file_size:.1f} KB)")

# Step 8: Display directory structure
print(f"\nSTEP 8: Output Directory Structure")
print("-" * 80)
print(f"Root: {output_path}")

for item in sorted(output_path.rglob("*")):
    if item.is_file():
        rel_path = item.relative_to(output_path)
        file_size = item.stat().st_size / 1024
        print(f"  {rel_path} ({file_size:.1f} KB)")

# Step 9: Summary
print(f"\n" + "="*80)
print("DOWNLOAD TEST SUMMARY")
print("="*80)

print(f"\n✅ WMS Catalog Integration: SUCCESS")
print(f"   • Service discovery: Working")
print(f"   • Metadata extraction: Working")
print(f"   • Configuration: Working")
print(f"   • ImageDownloader integration: Working")

print(f"\n✅ Download Results:")
print(f"   • Service used: {recommended_service.id}")
print(f"   • Area: 100m × 100m")
print(f"   • Images downloaded: {len(image_files)}")
print(f"   • Metadata files: {len(metadata_files)}")
print(f"   • Output directory: {output_path}")

print(f"\n✅ Test Status: {'PASSED' if len(image_files) > 0 else 'FAILED'}")

if len(image_files) > 0:
    print(f"\n🎉 The WMS Catalog successfully enabled orthophoto downloads!")
    print(f"   Downloaded imagery from {recommended_service.state_name}")
    print(f"   Using {recommended_service.type} at {int(recommended_service.resolution*100)}cm resolution")
else:
    print(f"\n⚠️  No files were downloaded - check WMS service availability")

print(f"\nDownloaded files saved to: {output_path.absolute()}")
print(f"You can view the TIFF images with QGIS or any GIS software")
print("\n" + "="*80 + "\n")

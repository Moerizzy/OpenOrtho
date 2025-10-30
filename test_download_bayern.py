#!/usr/bin/env python3
"""
Test: Download from Bayern (Munich center) - known good location
"""

import sys
sys.path.insert(0, 'src')

import logging
from pathlib import Path
from shapely.geometry import box
from geopandas import GeoSeries
from orthophotos_downloader.wms_catalog import WMSCatalogManager
from orthophotos_downloader.data_scraping.image_download import ImageDownloader, ExtendedWebMapService

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

print("\n" + "="*80)
print("TEST: Download from known Bayern location (Munich)")
print("="*80 + "\n")

# Use catalog to get Bayern service
catalog = WMSCatalogManager()
bayern_service = catalog.filter_services(state_code='BY', image_type='RGB', resolution=0.2)[0]

print(f"Service: {bayern_service.id}")
print(f"URL: {bayern_service.url}")
print(f"Layer: {bayern_service.layer_name}\n")

# Munich center - Marienplatz (correct EPSG:25832 coordinates)
# Lat/Lon: 48.1374, 11.5755 -> EPSG:25832: 691603, 5334780
munich_center_bbox = (691550, 5334730, 691650, 5334830)  # 100m x 100m

print(f"Area: Munich city center (Marienplatz)")
print(f"Bbox (EPSG:25832): {munich_center_bbox}")
print(f"Size: 100m x 100m\n")

# Create WMS
wms = ExtendedWebMapService(
    url=bayern_service.url,
    version=bayern_service.version,
    resolution=bayern_service.resolution,
    layer_name=bayern_service.layer_name,
    crs=bayern_service.crs,
    format=bayern_service.format
)

# Create downloader
output_path = Path("data/test_downloads_bayern")
output_path.mkdir(parents=True, exist_ok=True)

downloader = ImageDownloader(
    wms=wms,
    grid_spacing=50,
    state_code='BY',
    extract_metadata=True
)

print(f"Downloading...\n")

# Create polygon and download
polygon = box(*munich_center_bbox)
area_polygon = GeoSeries([polygon], crs=bayern_service.crs)

result = downloader.download_images_from_polygon(
    area_name="munich_center",
    area_polygon=area_polygon,
    out_path=output_path,
    filename_prefix="bayern"
)

print(f"\n✅ Download complete!")
print(f"Files saved to: {output_path.absolute()}")

# Check if images have data
import rasterio
import numpy as np

image_files = list(output_path.glob("*.tiff"))
print(f"\nChecking {len(image_files)} images for actual data:")

for img_path in image_files:
    with rasterio.open(img_path) as ds:
        data = ds.read()
        unique_vals = len(np.unique(data))
        non_white = np.sum(data < 255)
        print(f"  {img_path.name}: {unique_vals} unique values, {non_white} non-white pixels")
        
print("\n" + "="*80 + "\n")

#!/usr/bin/env python3
"""
Example: Downloading Orthophotos with Automatic Metadata Extraction
=====================================================================

This example demonstrates how to download orthophotos and automatically
extract metadata, creating STAC (SpatioTemporal Asset Catalog) items
for each downloaded tile.

The metadata includes:
- Acquisition date
- Tile number
- Ground resolution
- Flight information
- And more (varies by German state)

Each downloaded GeoTIFF will have an accompanying JSON file with STAC metadata.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import geopandas as gpd
from shapely.geometry import box
from orthophotos_downloader import AutoOrthophotoDownloader

# Define your area of interest (EPSG:25832 - UTM Zone 32N)
# Example: Area in Munich, Bavaria
area_bbox = box(691000, 5334000, 692000, 5335000)
area_gdf = gpd.GeoDataFrame([1], geometry=[area_bbox], crs="EPSG:25832")

# Create output directory
output_dir = Path("./downloads_with_metadata")
output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("OpenOrtho - Download with Automatic Metadata Extraction")
print("=" * 80)
print(f"\n📍 Area: Munich, Bavaria")
print(f"📦 Output: {output_dir}")
print(f"📊 Features: RGB images + STAC metadata\n")

# Initialize the downloader
# Metadata extraction is enabled by default
downloader = AutoOrthophotoDownloader(grid_spacing=1000)

# Download RGB images with automatic metadata extraction
print("🚀 Starting download...")
print("   Metadata will be automatically extracted for each tile")
print("   STAC items will be saved as .json files alongside .tif files\n")

results = downloader.download_rgb_images_auto(
    area_polygon=area_gdf,
    area_name="munich_example",
    out_path=output_dir / "rgb"
)

print("\n" + "=" * 80)
print("📊 DOWNLOAD SUMMARY")
print("=" * 80)

for state_name, result in results.items():
    print(f"\n{state_name}:")
    print(f"  • Images downloaded: {len(result.images)}")
    print(f"  • Output path: {result.out_path}")
    
    # Check for STAC items
    stac_files = list(result.out_path.glob("*.json"))
    print(f"  • STAC items created: {len(stac_files)}")
    
    if stac_files:
        print(f"\n  📄 Example STAC item: {stac_files[0].name}")

print("\n" + "=" * 80)
print("✨ WHAT WAS CREATED")
print("=" * 80)
print("""
For each downloaded tile, you will find:

1. GeoTIFF file (*.tif)
   - RGB orthophoto image
   - Geographic coordinates embedded
   - Standard GeoTIFF format

2. STAC Item file (*.json)
   - Acquisition date
   - Spatial extent (bbox, geometry)
   - Resolution and projection info
   - State-specific metadata fields
   - Links to the image file

Example STAC Item structure:
{
  "stac_version": "1.0.0",
  "type": "Feature",
  "id": "RGB_32_691000_5334000",
  "bbox": [691000, 5334000, 692000, 5335000],
  "geometry": {...},
  "properties": {
    "datetime": "2024-08-24T00:00:00Z",
    "gsd": 0.2,
    "ortho:acquisition_date": "2024-08-24",
    "ortho:tile_name": "326915334",
    "ortho:ground_resolution": "20",
    ...
  },
  "assets": {
    "image": {
      "href": "RGB_32_691000_5334000.tif",
      "type": "image/tiff; application=geotiff"
    }
  }
}
""")

print("\n" + "=" * 80)
print("💡 USING THE METADATA")
print("=" * 80)
print("""
You can use the STAC items to:

1. Search and filter tiles by acquisition date
2. Build STAC catalogs for your orthophoto collections
3. Integrate with STAC-compatible tools and viewers
4. Track metadata provenance
5. Share discoverable geospatial datasets

Example - Load STAC item with pystac:
```python
import pystac

item = pystac.Item.from_file('RGB_32_691000_5334000.json')
print(f"Acquired: {item.properties['datetime']}")
print(f"Resolution: {item.properties['gsd']}m")
```

Example - Search by date:
```python
from pathlib import Path
import json
from datetime import datetime

def find_tiles_after_date(directory, cutoff_date):
    for json_file in Path(directory).glob('**/*.json'):
        with open(json_file) as f:
            item = json.load(f)
        item_date = datetime.fromisoformat(
            item['properties']['datetime'].replace('Z', '+00:00')
        )
        if item_date > cutoff_date:
            yield item

# Find all tiles acquired after Jan 1, 2024
recent_tiles = find_tiles_after_date(
    './downloads_with_metadata',
    datetime(2024, 1, 1)
)
```
""")

print("\n✅ Example complete!")
print(f"📁 Check {output_dir} for downloaded files and metadata\n")

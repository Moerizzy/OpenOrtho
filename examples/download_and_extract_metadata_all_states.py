#!/usr/bin/env python3
"""
Example: Download One Image Per State and Extract Metadata
===========================================================

This example demonstrates downloading a single orthophoto tile from each German state
and extracting metadata using the AutoOrthophotoDownloader.

Each downloaded tile will have:
- GeoTIFF image file (.tif)
- STAC metadata file (.json) with acquisition date, resolution, tile info, etc.
"""

import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import geopandas as gpd
from shapely.geometry import box
from orthophotos_downloader import AutoOrthophotoDownloader

# Test coordinates for each state (EPSG:25832 - UTM Zone 32N)
# These are actual locations within each state's coverage area
STATE_TEST_AREAS = {
    'BY': {  # Bayern - Munich area
        'bbox': (691000, 5334000, 692000, 5335000),
        'location': 'Munich (München)',
    },
    'BW': {  # Baden-Württemberg - Stuttgart area
        'bbox': (511500, 5398500, 512500, 5399500),
        'location': 'Stuttgart',
    },
    'NW': {  # Nordrhein-Westfalen - Cologne area
        'bbox': (356500, 5644500, 357500, 5645500),
        'location': 'Cologne (Köln)',
    },
    'TH': {  # Thüringen - Erfurt area
        'bbox': (650000, 5639000, 651000, 5640000),
        'location': 'Erfurt',
    },
    'HE': {  # Hessen - Frankfurt area
        'bbox': (478000, 5551000, 479000, 5552000),
        'location': 'Frankfurt am Main',
    },
    'NI': {  # Niedersachsen - Hannover area
        'bbox': (560000, 5805000, 561000, 5806000),
        'location': 'Hannover',
    },
    'SH': {  # Schleswig-Holstein - Kiel area
        'bbox': (565000, 6025000, 566000, 6026000),
        'location': 'Kiel',
    },
    'MV': {  # Mecklenburg-Vorpommern - Rostock area
        'bbox': (705000, 5990000, 706000, 5991000),
        'location': 'Rostock',
    },
    'BE': {  # Berlin - Berlin center
        'bbox': (790000, 5820000, 791000, 5821000),
        'location': 'Berlin',
    },
    'BB': {  # Brandenburg - Potsdam area
        'bbox': (780000, 5810000, 781000, 5811000),
        'location': 'Potsdam',
    },
    'SL': {  # Saarland - Saarbrücken area
        'bbox': (355000, 5468000, 356000, 5469000),
        'location': 'Saarbrücken',
    },
    'RP': {  # Rheinland-Pfalz - Koblenz area
        'bbox': (405500, 5580500, 406500, 5581500),
        'location': 'Koblenz',
    },
    'SN': {  # Sachsen - Dresden area
        'bbox': (813000, 5660000, 814000, 5661000),
        'location': 'Dresden',
    },
    'ST': {  # Sachsen-Anhalt - Magdeburg area
        'bbox': (690500, 5765500, 691500, 5766500),
        'location': 'Magdeburg',
    },
}


def download_and_extract_state(state_code, state_name, area_info, output_dir):
    """Download one image from a state and extract metadata."""
    
    bbox = area_info['bbox']
    location = area_info['location']
    
    print(f"\n{'='*80}")
    print(f"🏛️  Downloading from: {state_name} ({state_code})")
    print(f"{'='*80}")
    print(f"📍 Location: {location}")
    print(f"   Coordinates: {bbox} EPSG:25832")
    
    # Create bounding box for the area
    area_bbox = box(bbox[0], bbox[1], bbox[2], bbox[3])
    area_gdf = gpd.GeoDataFrame([1], geometry=[area_bbox], crs="EPSG:25832")
    
    # Create state-specific output directory
    state_output_dir = output_dir / state_code
    state_output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize downloader with metadata extraction enabled
        downloader = AutoOrthophotoDownloader(grid_spacing=1000, extract_metadata=True)
        
        print(f"📥 Downloading RGB imagery...")
        
        # Download RGB images
        results = downloader.download_rgb_images_auto(
            area_polygon=area_gdf,
            area_name=f"test_{state_code}_{location.replace(' ', '_')}",
            out_path=state_output_dir / "rgb",
            filename_prefix="RGB"
        )
        
        # Check results
        total_images = 0
        total_metadata = 0
        
        for state_result_name, result in results.items():
            if result and result.images:
                total_images += len(result.images)
                
                # Count metadata files
                metadata_files = list((result.out_path).glob("*.json"))
                total_metadata += len(metadata_files)
                
                print(f"   ✅ Downloaded: {len(result.images)} image(s)")
                print(f"   📄 Metadata files: {len(metadata_files)}")
                
                # Show first metadata file
                if metadata_files:
                    with open(metadata_files[0]) as f:
                        stac_item = json.load(f)
                        props = stac_item.get('properties', {})
                        
                        print(f"\n   ⭐ First tile metadata:")
                        if 'ortho:acquisition_date' in props:
                            print(f"      📅 Acquisition Date: {props['ortho:acquisition_date']}")
                        if 'ortho:tile_number' in props:
                            print(f"      🔢 Tile Number: {props['ortho:tile_number']}")
                        if 'ortho:resolution_x' in props:
                            res = props['ortho:resolution_x']
                            print(f"      📏 Resolution: {res}m")
        
        print(f"\n✅ Success: Downloaded {total_images} image(s) with {total_metadata} metadata file(s)")
        return True, total_images, total_metadata
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False, 0, 0


def main():
    """Download and extract metadata for all states."""
    
    print("=" * 80)
    print("OpenOrtho - Download & Metadata Extraction - All States")
    print("=" * 80)
    print("\nThis example downloads one RGB orthophoto tile from each German state")
    print("and demonstrates automatic STAC metadata extraction.\n")
    print("⏱️  This will take several minutes (network dependent)...\n")
    
    # Create output directory
    output_dir = Path("./data/metadata_extraction_all_states")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Output directory: {output_dir}\n")
    
    # States to download (in order)
    states_to_download = [
        ('BY', 'Bayern (Bavaria)'),
        ('BW', 'Baden-Württemberg'),
        ('NW', 'Nordrhein-Westfalen (NRW)'),
        ('TH', 'Thüringen (Thuringia)'),
        ('HE', 'Hessen (Hesse)'),
        ('NI', 'Niedersachsen (Lower Saxony)'),
        ('SH', 'Schleswig-Holstein'),
        ('MV', 'Mecklenburg-Vorpommern'),
        ('BE', 'Berlin'),
        ('BB', 'Brandenburg'),
        ('SL', 'Saarland'),
        ('RP', 'Rheinland-Pfalz (Rhineland-Palatinate)'),
        ('SN', 'Sachsen (Saxony)'),
        ('ST', 'Sachsen-Anhalt (Saxony-Anhalt)'),
    ]
    
    results = {}
    
    # Download from each state
    for state_code, state_name in states_to_download:
        if state_code in STATE_TEST_AREAS:
            area_info = STATE_TEST_AREAS[state_code]
            success, images, metadata = download_and_extract_state(
                state_code, state_name, area_info, output_dir
            )
            results[state_code] = {
                'name': state_name,
                'location': area_info['location'],
                'success': success,
                'images': images,
                'metadata': metadata
            }
        else:
            print(f"\n⚠️  No test coordinates configured for {state_code}")
            results[state_code] = {
                'name': state_name,
                'success': False,
                'images': 0,
                'metadata': 0
            }
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    successful = [code for code, data in results.items() if data['success']]
    failed = [code for code, data in results.items() if not data['success']]
    
    total_images = sum(data['images'] for data in results.values())
    total_metadata = sum(data['metadata'] for data in results.values())
    
    print(f"\n✅ Successful downloads: {len(successful)}/{len(results)}")
    print(f"❌ Failed downloads: {len(failed)}/{len(results)}")
    print(f"\n📊 Statistics:")
    print(f"   Total images downloaded: {total_images}")
    print(f"   Total metadata files created: {total_metadata}")
    print(f"   Output directory: {output_dir}")
    
    if successful:
        print(f"\n✅ Working states:")
        for code in successful:
            data = results[code]
            print(f"   • {code} ({data['location']}): {data['images']} image(s)")
    
    if failed:
        print(f"\n❌ Failed states:")
        for code in failed:
            data = results[code]
            print(f"   • {code} ({data['name']})")
    
    # Show sample metadata structure
    print("\n" + "=" * 80)
    print("📋 SAMPLE STAC METADATA")
    print("=" * 80)
    
    # Find first successful download with metadata
    for state_code in successful:
        state_output_dir = output_dir / state_code
        metadata_files = list(state_output_dir.rglob("*.json"))
        
        if metadata_files:
            print(f"\n📄 Example from {state_code}:")
            with open(metadata_files[0]) as f:
                stac_item = json.load(f)
                
                print(f"   Filename: {metadata_files[0].name}")
                print(f"   ID: {stac_item.get('id')}")
                print(f"   Collection: {stac_item.get('collection')}")
                
                props = stac_item.get('properties', {})
                print(f"\n   Key Properties:")
                print(f"   • datetime: {props.get('datetime')}")
                print(f"   • proj:epsg: {props.get('proj:epsg')}")
                print(f"   • ortho:acquisition_date: {props.get('ortho:acquisition_date')}")
                print(f"   • ortho:resolution_x: {props.get('ortho:resolution_x')}m")
                print(f"   • ortho:tile_path: {props.get('ortho:tile_path')}")
                
                # Show band information
                assets = stac_item.get('assets', {})
                if 'image' in assets and 'eo:bands' in assets['image']:
                    print(f"\n   Band Information:")
                    for i, band in enumerate(assets['image']['eo:bands']):
                        print(f"   • Band {i+1}: {band.get('name')} ({band.get('common_name')})")
            
            break
    
    # Instructions
    print("\n" + "=" * 80)
    print("💡 NEXT STEPS")
    print("=" * 80)
    print("""
1. 🔍 Inspect the downloaded images:
   ls -la data/metadata_extraction_all_states/*/rgb/*/
   
2. 📄 View STAC metadata:
   cat data/metadata_extraction_all_states/BY/rgb/Bayern/RGB_*.json | jq '.'
   
3. 📊 Analyze metadata:
   python3 -c "
   import json
   from pathlib import Path
   
   for json_file in Path('data/metadata_extraction_all_states').rglob('*.json'):
       with open(json_file) as f:
           item = json.load(f)
       props = item['properties']
       print(f'{json_file.parent.parent.parent.name}: {props.get(\"ortho:acquisition_date\", \"N/A\")}')"
   
4. 🎨 Visualize images:
   python3 -c "
   import rasterio
   import matplotlib.pyplot as plt
   from pathlib import Path
   
   tif_files = list(Path('data/metadata_extraction_all_states').rglob('*.tiff'))[:9]
   fig, axes = plt.subplots(3, 3, figsize=(12, 12))
   
   for ax, tif_file in zip(axes.flat, tif_files):
       with rasterio.open(tif_file) as src:
           img = src.read([1,2,3])
       ax.imshow(img.transpose(1,2,0)/255)
       ax.set_title(tif_file.parent.parent.parent.name, fontsize=10)
       ax.axis('off')
   
   plt.tight_layout()
   plt.savefig('metadata_extraction_overview.png', dpi=100)
   plt.show()"
    """)
    
    print(f"\n✨ Download complete! Check {output_dir} for results.\n")


if __name__ == '__main__':
    main()

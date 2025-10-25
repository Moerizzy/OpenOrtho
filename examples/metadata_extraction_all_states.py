#!/usr/bin/env python3
"""
Working Example: Metadata Extraction for All States
====================================================

This is a runnable example that demonstrates metadata extraction
for all German states using real WMS services.

Run this to see which states provide metadata and what information is available.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from orthophotos_downloader.metadata.metadata_extractor import TileMetadataExtractor

# State WMS URLs
STATE_WMS_URLS = {
    'BY': 'https://geoservices.bayern.de/od/wms/dop/v1/dop20?',
    'BW': 'https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_Services?',  # Main image service (metadata uses dedicated service)
    'NW': 'https://www.wms.nrw.de/geobasis/wms_nw_dop?',
    'TH': 'https://www.geoproxy.geoportal-th.de/geoproxy/services/DOP?',
    'HE': 'https://www.gds-srv.hessen.de/cgi-bin/lika-services/ogc-free-images.ows?language=ger&',
    'NI': 'https://opendata.lgln.niedersachsen.de/doorman/noauth/dop_wms?language=ger&',
    'SH': 'https://service.gdi-sh.de/WMS_SH_MD_DOP?',
    'MV': 'https://www.geodaten-mv.de/dienste/adv_dop?',
    'BE': 'https://isk.geobasis-bb.de/mapproxy/dop20c/service/wms?',
    'BB': 'https://isk.geobasis-bb.de/mapproxy/dop20c/service/wms?',
    'SL': 'https://geoportal.saarland.de/mapbender/php/wms.php?layer_id=46302&VERSION=1.1.1&withChilds=1&',
    'RP': 'https://geo4.service24.rlp.de/wms/rp_dop20.fcgi?VERSION=1.1.1&',
    'SN': 'https://geodienste.sachsen.de/wms_geosn_dop-rgb/guest?',
    'ST': 'https://www.geodatenportal.sachsen-anhalt.de/wss/service/ST_LVermGeo_DOP_WMS/guest?',  # Main image service (metadata uses dedicated service)
}

# Test coordinates for each state (EPSG:25832 - UTM Zone 32N)
# These are actual locations within each state's coverage area
STATE_TEST_COORDINATES = {
    'BY': {  # Bayern - Munich area
        'x': 691344,
        'y': 5334000,
        'location': 'Munich (München)'
    },
    'BW': {  # Baden-Württemberg - Stuttgart area
        'x': 511500,
        'y': 5398500,
        'location': 'Stuttgart'
    },
    'NW': {  # Nordrhein-Westfalen - Cologne area
        'x': 356500,
        'y': 5644500,
        'location': 'Cologne (Köln)'
    },
    'TH': {  # Thüringen - Erfurt area
        'x': 650000,
        'y': 5639000,
        'location': 'Erfurt'
    },
    'HE': {  # Hessen - Frankfurt area
        'x': 478000,
        'y': 5551000,
        'location': 'Frankfurt am Main'
    },
    'NI': {  # Niedersachsen - Hannover area
        'x': 560000,
        'y': 5805000,
        'location': 'Hannover'
    },
    'SH': {  # Schleswig-Holstein - Kiel area
        'x': 565000,
        'y': 6025000,
        'location': 'Kiel'
    },
    'MV': {  # Mecklenburg-Vorpommern - Rostock area
        'x': 705000,
        'y': 5990000,
        'location': 'Rostock'
    },
    'BE': {  # Berlin - Berlin center (Brandenburg Gate area)
        'x': 790000,
        'y': 5820000,
        'location': 'Berlin'
    },
    'BB': {  # Brandenburg - Potsdam area
        'x': 780000,
        'y': 5810000,
        'location': 'Potsdam'
    },
    'SL': {  # Saarland - Saarbrücken area
        'x': 355000,
        'y': 5468000,
        'location': 'Saarbrücken'
    },
    'RP': {  # Rheinland-Pfalz - Koblenz area
        'x': 405500,
        'y': 5580500,
        'location': 'Koblenz'
    },
    'SN': {  # Sachsen - Dresden area
        'x': 813000,
        'y': 5660000,
        'location': 'Dresden'
    },
    'ST': {  # Sachsen-Anhalt - Magdeburg area
        'x': 690500,
        'y': 5765500,
        'location': 'Magdeburg'
    },
}


def test_state_metadata(state_code, state_name, coords_info):
    """Test metadata extraction for a specific state."""
    x = coords_info['x']
    y = coords_info['y']
    location = coords_info['location']
    
    print(f"\n{'='*80}")
    print(f"🏛️  Testing: {state_name} ({state_code})")
    print(f"{'='*80}")
    print(f"📍 Test Location: {location}")
    print(f"   Coordinates: ({x}, {y}) EPSG:25832")
    
    # Check if we have a WMS URL for this state
    if state_code not in STATE_WMS_URLS:
        print("\n❌ WMS URL not configured for this state")
        print("   Only GeoTIFF metadata available")
        return None
    
    wms_url = STATE_WMS_URLS[state_code]
    extractor = TileMetadataExtractor(wms_url, state_code)
    
    # Check if state has WMS metadata support
    if state_code not in extractor.METADATA_LAYERS:
        print("\n❌ WMS metadata layer not configured for this state")
        print("   Only GeoTIFF metadata available")
        return None
    
    print(f"\n✅ WMS metadata layer: {extractor.METADATA_LAYERS[state_code]}")
    
    # Check for dedicated metadata service
    if state_code in extractor.METADATA_SERVICES:
        print(f"✨ Dedicated metadata service available")
    
    # Try to query metadata
    print(f"\n� Querying WMS metadata...")
    
    try:
        metadata = extractor._query_wms_metadata(
            center_x=x,
            center_y=y,
            crs='EPSG:25832'
        )
        
        if metadata:
            print(f"✅ Metadata retrieved successfully!")
            
            # Show key fields first
            print(f"\n⭐ KEY METADATA:")
            if 'acquisition_date' in metadata:
                print(f"   📅 Acquisition Date: {metadata['acquisition_date']}")
            if 'tile_number' in metadata or 'tile_name' in metadata:
                tile_id = metadata.get('tile_number') or metadata.get('tile_name')
                print(f"   🔢 Tile ID: {tile_id}")
            if 'ground_resolution' in metadata:
                print(f"   📏 Ground Resolution: {metadata['ground_resolution']}m")
            if 'photometry' in metadata:
                print(f"   🎨 Photometry: {metadata['photometry']}")
            
            # Show all fields
            print(f"\n📋 All available fields ({len(metadata)}):")
            for key, value in sorted(metadata.items()):
                if key != 'raw_response' and value is not None:
                    # Format the value nicely
                    if isinstance(value, str):
                        display_value = value[:80] if len(value) > 80 else value
                    else:
                        display_value = str(value)
                    print(f"   • {key}: {display_value}")
            
            return metadata
        else:
            print(f"⚠️  Query succeeded but no metadata returned")
            print(f"   This might indicate:")
            print(f"   - No data available at this specific location")
            print(f"   - Service returned empty response")
            return None
            
    except Exception as e:
        print(f"❌ Error querying metadata: {e}")
        print(f"\n   Possible issues:")
        print(f"   • Wrong/outdated WMS URL")
        print(f"   • Service connectivity issues")
        print(f"   • Authentication requirements")
        print(f"   • Unsupported parameter format")
        return None


def main():
    """Test all states."""
    print("=" * 80)
    print("OpenOrtho Metadata Extraction - All States Test")
    print("=" * 80)
    print("\nThis example tests WMS metadata extraction for all German states.")
    print("Each state is tested with coordinates in a major city within that state.")
    print("Note: Results depend on live WMS service availability.\n")
    
    # States with known WMS metadata support
    states_to_test = [
        ('BY', 'Bayern (Bavaria)'),
        ('BW', 'Baden-Württemberg'),
        ('NW', 'Nordrhein-Westfalen (North Rhine-Westphalia)'),
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
    
    # Test states with WMS support
    for state_code, state_name in states_to_test:
        coords_info = STATE_TEST_COORDINATES[state_code]
        result = test_state_metadata(state_code, state_name, coords_info)
        results[state_code] = {
            'name': state_name,
            'location': coords_info['location'],
            'success': result is not None,
            'has_date': result is not None and 'acquisition_date' in result,
            'metadata': result
        }
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    working = [code for code, data in results.items() if data['success']]
    with_dates = [code for code, data in results.items() if data['has_date']]
    failed = [code for code, data in results.items() if not data['success']]
    
    print(f"\n✅ Successful queries: {len(working)}/{len(results)}")
    print(f"📅 States with acquisition dates: {len(with_dates)}/{len(results)}")
    
    if with_dates:
        print(f"\n⭐ States with date metadata:")
        for code in with_dates:
            print(f"   • {code} ({results[code]['location']}): ", end='')
            if results[code]['metadata'] and 'acquisition_date' in results[code]['metadata']:
                date = results[code]['metadata']['acquisition_date']
                print(f"{date}")
    
    if working and not with_dates:
        print(f"\n🟡 States queried successfully but no date:")
        for code in working:
            if code not in with_dates:
                print(f"   • {code}: {results[code]['name']}")
    
    if failed:
        print(f"\n❌ Failed queries: {len(failed)}")
        for code in failed:
            print(f"   • {code}: {results[code]['name']}")
    
    # Statistics on metadata fields
    print(f"\n" + "=" * 80)
    print("📈 METADATA FIELDS COMPARISON")
    print("=" * 80)
    
    for code in working:
        if results[code]['metadata']:
            meta = results[code]['metadata']
            field_count = len([v for v in meta.values() if v is not None])
            print(f"\n{code} - {results[code]['name']}:")
            print(f"   Location: {results[code]['location']}")
            print(f"   Total fields: {field_count}")
            
            # Key fields
            key_fields = ['acquisition_date', 'tile_number', 'tile_name', 
                         'ground_resolution', 'photometry', 'flight_year']
            available = [f for f in key_fields if f in meta and meta[f]]
            if available:
                print(f"   Key fields: {', '.join(available)}")
    
    # Information about other states
    print("\n" + "=" * 80)
    print("ℹ️  OTHER GERMAN STATES (Not yet tested with proper coordinates)")
    print("=" * 80)
    
    other_states = {
        'MV': ('Mecklenburg-Vorpommern', 'Service moved'),
        'RP': ('Rheinland-Pfalz', 'Service moved'),
        'BB': ('Brandenburg', 'Server error on metadata query'),
        'SL': ('Saarland', 'Parameter/configuration issues'),
        'SN': ('Sachsen', 'May work with correct coordinates'),
        'BW': ('Baden-Württemberg', 'Not yet configured'),
        'ST': ('Sachsen-Anhalt', 'Not yet configured'),
        'HH': ('Hamburg', 'Not yet configured'),
        'HB': ('Bremen', 'Not yet configured'),
        'BE': ('Berlin', 'Not yet configured')
    }
    
    print("\nThese states need:")
    print("  • Correct WMS URLs")
    print("  • Test coordinates within state coverage")
    print("  • Investigation of service requirements")
    
    # Important notes
    print("\n" + "=" * 80)
    print("💡 IMPORTANT NOTES")
    print("=" * 80)
    print("""
1. 📍 State-Specific Test Coordinates
   Each state is now tested with coordinates in a major city:
   • Bayern: Munich (München)
   • NRW: Cologne (Köln)
   • Thüringen: Erfurt
   • Hessen: Frankfurt am Main
   • Niedersachsen: Hannover
   • Schleswig-Holstein: Kiel

2. 🌐 Live Service Dependency
   Results depend on WMS services being available
   Services may be temporarily down or have rate limits

3. 📄 GeoTIFF Metadata (100% Coverage)
   Even if WMS fails, GeoTIFF metadata always works:
   • Resolution, bounds, CRS from tile file
   • Reliable fallback for all states

4. 🔧 Troubleshooting
   For failed states, check:
   • Service URLs (may have changed)
   • Coordinate system (EPSG:25832)
   • Service availability

5. 📚 More Information
   • METADATA_EXTRACTION.md - User guide
   • METADATA_STATUS_REPORT.md - Detailed analysis
   • WORKING_METADATA_LAYERS.md - Working configs
   • diagnose_failing_states.py - Diagnostic tool
    """)
    
    print("\n✨ Example: Extract from a downloaded tile:")
    print("   from orthophotos_downloader.metadata.metadata_extractor import TileMetadataExtractor")
    print("   from pathlib import Path")
    print("")
    print("   wms_url = 'https://geoservices.bayern.de/od/wms/dop/v1/dop20?'")
    print("   extractor = TileMetadataExtractor(wms_url, 'BY')")
    print("   metadata = extractor.extract_tile_metadata(")
    print("       tile_path=Path('tile.tif'),")
    print("       center_x=691344,")
    print("       center_y=5334000")
    print("   )")
    print("   print(f'Resolution: {metadata[\"resolution\"]}m')")
    print("   print(f'Date: {metadata.get(\"acquisition_date\", \"N/A\")}')")
    print()


if __name__ == '__main__':
    main()

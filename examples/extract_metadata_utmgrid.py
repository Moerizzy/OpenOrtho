#!/usr/bin/env python3
"""
Extract Orthophoto Metadata from UTM Grid - No Image Downloads
==============================================================

This script reads a 1km UTM grid (ETRS89-UTM32) for Germany and extracts
metadata for all orthophoto tiles that intersect with grid cells.

Process:
1. Load the 1km UTM grid
2. Detect intersecting states for each grid cell
3. Query WMS metadata services for all intersecting cells
4. Store all metadata in a GeoPackage with georeferenced information
5. NO images are downloaded - metadata only!

Output:
- metadata_utm_grid_all_states.gpkg: GeoPackage with metadata for all tiles
- metadata_utm_grid_summary.csv: Summary statistics by state and grid cell

Each row contains:
- Grid cell geometry and ID
- State code and name
- Acquisition date (if available)
- Resolution, bounds, bands, CRS
- WMS metadata fields (state-specific)
- Extraction timestamp
"""

import sys
from pathlib import Path
from datetime import datetime
import geopandas as gpd
import pandas as pd
from shapely.geometry import box
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from orthophotos_downloader.metadata.metadata_extractor import TileMetadataExtractor
from orthophotos_downloader.data_scraping.auto_downloader import AutoOrthophotoDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s - %(levelname)s - %(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Map state codes to WMS URLs and metadata layers
STATE_WMS_CONFIG = {
    'BY': {
        'url': 'https://geoservices.bayern.de/wms/v1/gewaesserkarte?',
        'layer': 'by_dop20_info',
        'name': 'Bayern',
    },
    'BW': {
        'url': 'https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_DOP_20_Bildflugkacheln_Aktualitaet?',
        'layer': 'verm:v_dop_20_bildflugkacheln',
        'name': 'Baden-Württemberg',
    },
    'NW': {
        'url': 'https://www.wms.nrw.de/wms/token/...',
        'layer': 'nw_dop_utm_info',
        'name': 'Nordrhein-Westfalen',
    },
    'TH': {
        'url': 'https://geo.thueringen.de/odp/services/Basiskarten/...',
        'layer': 'th_dop_info',
        'name': 'Thüringen',
    },
    'HE': {
        'url': 'https://www.gds-srv.hessen.de/cgi-bin/lika-services/ogc-free-images.ows?language=ger&',
        'layer': 'wms_he_dop',
        'name': 'Hessen',
    },
    'NI': {
        'url': 'https://opendata.lgln.niedersachsen.de/doorman/noauth/dop_wms?language=ger&',
        'layer': 'ni_dop20_info',
        'name': 'Niedersachsen',
    },
    'SH': {
        'url': 'https://service.gdi-sh.de/WMS_SH_MD_DOP?',
        'layer': 'DOP20',
        'name': 'Schleswig-Holstein',
    },
    'MV': {
        'url': 'https://www.geoserver.mecklenburg-vorpommern.de/wms/...',
        'layer': 'mv_dop_info',
        'name': 'Mecklenburg-Vorpommern',
    },
    'BE': {
        'url': 'https://isk.geobasis-bb.de/ows/aktualitaeten_wms?',
        'layer': 'bb_dop_info',
        'name': 'Berlin',
    },
    'BB': {
        'url': 'https://isk.geobasis-bb.de/ows/aktualitaeten_wms?',
        'layer': 'bb_dop_info',
        'name': 'Brandenburg',
    },
    'SL': {
        'url': 'https://geoportal.saarland.de/freewms/truedop?',
        'layer': 'sl_dop_info',
        'name': 'Saarland',
    },
    'RP': {
        'url': 'https://www.wms.rlp.de/wms/dceleveserv_dop20_aktualitaet?',
        'layer': 'rp_dop20_info',
        'name': 'Rheinland-Pfalz',
    },
    'SN': {
        'url': 'https://geoportal.sachsen.de/wms_geosn_dop20...',
        'layer': 'sn_dop_020_info',
        'name': 'Sachsen',
    },
    'ST': {
        'url': 'https://www.geodatenportal.sachsen-anhalt.de/wss/service/ST_LVermGeo_DOP_WMS_Kacheluebersicht/guest?',
        'layer': 'Aktualität_der_Orthophotos41668',
        'name': 'Sachsen-Anhalt',
    },
}


def load_grid(grid_path):
    """Load the UTM grid GeoPackage."""
    logger.info(f"Loading UTM grid from {grid_path}")
    grid = gpd.read_file(grid_path)
    logger.info(f"  Loaded {len(grid)} grid cells")
    logger.info(f"  CRS: {grid.crs}")
    return grid


def detect_states_for_grid_cell(grid_cell_geom, states_gdf):
    """Detect which states intersect with a grid cell."""
    intersecting_states = []
    
    for _, state_row in states_gdf.iterrows():
        if grid_cell_geom.intersects(state_row.geometry):
            state_name = state_row['name']
            state_code = state_row['id'].split('-')[-1]
            intersecting_states.append((state_code, state_name))
    
    return intersecting_states


def query_metadata_for_cell(grid_cell, states_intersecting):
    """Query metadata for a grid cell from all intersecting states."""
    # Calculate center point of grid cell
    geom = grid_cell.geometry
    bounds = geom.bounds  # (minx, miny, maxx, maxy)
    center_x = (bounds[0] + bounds[2]) / 2
    center_y = (bounds[1] + bounds[3]) / 2
    
    metadata_records = []
    
    for state_code, state_name in states_intersecting:
        try:
            # Create metadata extractor
            config = STATE_WMS_CONFIG.get(state_code)
            if not config:
                logger.debug(f"No WMS config for {state_code}")
                continue
            
            extractor = TileMetadataExtractor(
                wms_url=config['url'],
                state_code=state_code
            )
            
            # Query metadata from WMS (no tile file needed for this)
            wms_metadata = extractor._query_wms_metadata(center_x, center_y, "EPSG:25832")
            
            # Create metadata record
            record = {
                'grid_cell_id': grid_cell.get('id', 'unknown'),
                'state_code': state_code,
                'state_name': state_name,
                'center_x': center_x,
                'center_y': center_y,
                'acquisition_date': wms_metadata.get('acquisition_date'),
                'extraction_timestamp': datetime.now().isoformat(),
                'crs': 'EPSG:25832',
                'geometry': geom,
            }
            
            # Add all WMS metadata fields
            for key, val in wms_metadata.items():
                if key not in ['raw_response_html', 'raw_response']:
                    # Clean up field names for GeoPackage compatibility
                    clean_key = f"wms_{key}" if not key.startswith('wms_') else key
                    # Truncate to 254 chars for GeoPackage
                    if isinstance(val, str):
                        val = val[:254]
                    record[clean_key] = val
            
            metadata_records.append(record)
            
        except Exception as e:
            logger.debug(f"Failed to query metadata for {state_code} at grid cell {grid_cell.get('id')}: {e}")
            continue
    
    return metadata_records


def main():
    """Main execution."""
    grid_path = Path('/home/morizzi/git/OpenOrtho/OpenOrtho/examples/data/DE_Grid_ETRS89-UTM32_1km.gpkg')
    output_dir = Path('/home/morizzi/git/OpenOrtho/OpenOrtho/examples/data/metadata_utm_grid')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 80)
    print("EXTRACT ORTHOPHOTO METADATA FROM UTM GRID - ALL STATES")
    print("=" * 80 + "\n")
    
    logger.info(f"Output directory: {output_dir}")
    
    # Load grid and states
    grid = load_grid(grid_path)
    
    # Load German states for intersection detection
    logger.info("Loading German federal states...")
    states_url = "https://raw.githubusercontent.com/isellsoap/deutschlandGeoJSON/main/2_bundeslaender/4_niedrig.geo.json"
    states_gdf = gpd.read_file(states_url).to_crs("EPSG:25832")
    logger.info(f"  Loaded {len(states_gdf)} states")
    
    # Process grid cells
    logger.info(f"\nProcessing {len(grid)} grid cells...")
    logger.info("  Note: This will only query metadata, NOT download images")
    logger.info("  Using center point of each cell for WMS queries\n")
    
    all_metadata = []
    processed_count = 0
    metadata_count = 0
    
    for idx, (_, grid_cell) in enumerate(grid.iterrows()):
        processed_count += 1
        
        if processed_count % 500 == 0:
            print(f"  Processed {processed_count} cells, extracted {metadata_count} metadata records...")
        
        # Detect intersecting states
        states_intersecting = detect_states_for_grid_cell(
            grid_cell.geometry,
            states_gdf
        )
        
        if not states_intersecting:
            continue
        
        # Query metadata for this cell from all intersecting states
        cell_metadata = query_metadata_for_cell(grid_cell, states_intersecting)
        
        if cell_metadata:
            all_metadata.extend(cell_metadata)
            metadata_count += len(cell_metadata)
    
    print(f"\n  Total: Processed {processed_count} cells, extracted {metadata_count} metadata records")
    
    if all_metadata:
        # Create GeoDataFrame from metadata
        logger.info("\nCreating GeoDataFrame from metadata...")
        metadata_gdf = gpd.GeoDataFrame(all_metadata, crs="EPSG:25832")
        
        # Save to GeoPackage
        output_gpkg = output_dir / 'metadata_utm_grid_all_states.gpkg'
        logger.info(f"Saving metadata to {output_gpkg}")
        metadata_gdf.to_file(output_gpkg, driver='GPKG')
        logger.info(f"  ✅ Saved {len(metadata_gdf)} records")
        
        # Create summary CSV by state
        logger.info("\nGenerating summary statistics...")
        summary = metadata_gdf.groupby('state_code').agg({
            'grid_cell_id': 'count',
            'acquisition_date': lambda x: x.notna().sum(),
        }).rename(columns={
            'grid_cell_id': 'total_records',
            'acquisition_date': 'records_with_date',
        })
        
        summary_csv = output_dir / 'metadata_utm_grid_summary.csv'
        summary.to_csv(summary_csv)
        logger.info(f"  ✅ Saved summary to {summary_csv}")
        
        # Print summary
        print("\n" + "=" * 80)
        print("SUMMARY BY STATE")
        print("=" * 80)
        print(summary.to_string())
        
        # Print sample records
        print("\n" + "=" * 80)
        print("SAMPLE METADATA RECORDS")
        print("=" * 80)
        display_cols = ['grid_cell_id', 'state_code', 'state_name', 'acquisition_date', 
                       'center_x', 'center_y']
        print(metadata_gdf[display_cols].head(10).to_string())
        
    else:
        logger.warning("No metadata records extracted!")
    
    print("\n" + "=" * 80)
    print("✅ METADATA EXTRACTION COMPLETE")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    main()

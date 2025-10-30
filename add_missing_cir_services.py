"""Add missing CIR services to WMS catalog."""

import yaml
from pathlib import Path

# Missing CIR services to add
missing_cir_services = [
    {
        'id': 'HE_CIR_DOP20_current',
        'state_code': 'HE',
        'state_name': 'Hessen',
        'type': 'CIR',
        'resolution': 0.2,
        'year': 'latest',
        'temporal_coverage': '2017-current',
        'url': 'https://www.gds-srv.hessen.de/cgi-bin/lika-services/ogc-free-images.ows?language=ger&',
        'version': '1.1.1',
        'layer_name': 'dop20cir',
        'crs': 'EPSG:25832',
        'format': 'image/tiff',
        'availability': 'state-wide',
        'description': 'Hessen DOP20 CIR - Latest imagery',
        'direct_download': False,
        'source': 'Hessische Verwaltung für Bodenmanagement und Geoinformation',
        'metadata': {
            'metadata_service_url': 'https://www.gds-srv.hessen.de/cgi-bin/lika-services/ogc-free-images.ows?language=ger&',
            'metadata_layer': 'wms_he_dop',
            'metadata_description': 'Dedicated Hessen metadata service with detailed acquisition info',
            'metadata_wms_version': '1.3.0'
        }
    },
    {
        'id': 'MV_CIR_DOP20_current',
        'state_code': 'MV',
        'state_name': 'Mecklenburg-Vorpommern',
        'type': 'CIR',
        'resolution': 0.2,
        'year': 'latest',
        'temporal_coverage': '2018-current',
        'url': 'https://www.geodaten-mv.de/dienste/gdimv_dopcir',
        'version': '1.3.0',
        'layer_name': 'gdimv_dopcir',
        'crs': 'EPSG:25832',
        'format': 'image/png',
        'availability': 'state-wide',
        'description': 'Mecklenburg-Vorpommern DOP20 CIR - Latest imagery',
        'direct_download': False,
        'source': 'Landesamt für innere Verwaltung Mecklenburg-Vorpommern',
        'metadata': {
            'metadata_layer': 'mv_dop_info',
            'metadata_description': 'Mecklenburg-Vorpommern metadata layer',
            'metadata_wms_version': '1.3.0'
        }
    },
    {
        'id': 'NW_CIR_DOP_current',
        'state_code': 'NW',
        'state_name': 'Nordrhein-Westfalen',
        'type': 'CIR',
        'resolution': 0.1,
        'year': 'latest',
        'temporal_coverage': '2018-current',
        'url': 'https://www.wms.nrw.de/geobasis/wms_nw_dop',
        'version': '1.3.0',
        'layer_name': 'nw_dop_cir',
        'crs': 'EPSG:25832',
        'format': 'image/png',
        'availability': 'state-wide',
        'description': 'Nordrhein-Westfalen DOP10 CIR - Latest imagery',
        'direct_download': False,
        'source': 'Geobasis NRW',
        'metadata': {
            'metadata_layer': 'nw_dop_utm_info',
            'metadata_description': 'Nordrhein-Westfalen metadata layer',
            'metadata_wms_version': '1.1.1'
        }
    },
    {
        'id': 'RP_CIR_DOP20_current',
        'state_code': 'RP',
        'state_name': 'Rheinland-Pfalz',
        'type': 'CIR',
        'resolution': 0.2,
        'year': 'latest',
        'temporal_coverage': '2018-current',
        'url': 'https://www.geoportal.rlp.de/mapbender/php/wms.php?inspire=1&layer_id=38922&withChilds=1',
        'version': '1.3.0',
        'layer_name': 'DOP_CIR',
        'crs': 'EPSG:25832',
        'format': 'image/png',
        'availability': 'state-wide',
        'description': 'Rheinland-Pfalz DOP20 CIR - Latest imagery',
        'direct_download': False,
        'source': 'Landesamt für Vermessung und Geobasisinformation Rheinland-Pfalz',
        'metadata': {
            'metadata_layer': 'rp_dop20_info',
            'metadata_description': 'Rheinland-Pfalz metadata layer',
            'metadata_wms_version': '1.3.0'
        }
    },
    {
        'id': 'SL_CIR_DOP20_current',
        'state_code': 'SL',
        'state_name': 'Saarland',
        'type': 'CIR',
        'resolution': 0.2,
        'year': 'latest',
        'temporal_coverage': '2018-current',
        'url': 'https://geoportal.saarland.de/mapbender/php/wms.php?layer_id=46302&VERSION=1.1.1&withChilds=1',
        'version': '1.1.1',
        'layer_name': 'DOP_CIR',
        'crs': 'EPSG:25832',
        'format': 'image/png',
        'availability': 'state-wide',
        'description': 'Saarland DOP20 CIR - Latest imagery',
        'direct_download': False,
        'source': 'Landesamt für Vermessung, Geoinformation und Landentwicklung Saarland',
        'metadata': {
            'metadata_service_url': 'https://geoportal.saarland.de/freewms/truedop?',
            'metadata_layer': 'sl_dop_info',
            'metadata_description': 'Saarland metadata service',
            'metadata_extra_params': {'STYLES': ''},
            'metadata_info_format': 'text/html',
            'metadata_wms_version': '1.1.1'
        }
    }
]

# Load existing catalog
catalog_path = Path(__file__).parent / 'src/orthophotos_downloader/wms_catalog/wms_services.yaml'

with open(catalog_path, 'r') as f:
    catalog = yaml.safe_load(f)

print(f"Current services: {len(catalog['services'])}")

# Find where to insert each CIR service (after its RGB counterpart)
for cir_service in missing_cir_services:
    state_code = cir_service['state_code']
    
    # Find the RGB service for this state
    rgb_index = None
    for i, service in enumerate(catalog['services']):
        if service['state_code'] == state_code and service['type'] == 'RGB':
            rgb_index = i
            break
    
    if rgb_index is not None:
        # Check if CIR already exists
        cir_exists = any(
            s['state_code'] == state_code and s['type'] == 'CIR'
            for s in catalog['services']
        )
        
        if not cir_exists:
            # Insert CIR right after RGB
            catalog['services'].insert(rgb_index + 1, cir_service)
            print(f"✅ Added {cir_service['id']}")
        else:
            print(f"ℹ️  {state_code} CIR already exists")
    else:
        print(f"⚠️  No RGB service found for {state_code}")

print(f"New total services: {len(catalog['services'])}")

# Save updated catalog
with open(catalog_path, 'w') as f:
    yaml.dump(catalog, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print(f"✅ Catalog updated at {catalog_path}")

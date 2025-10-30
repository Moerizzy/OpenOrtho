#!/usr/bin/env python3
"""
Update WMS catalog with metadata service information
"""

import yaml
from pathlib import Path

# Metadata service configurations from metadata_extractor.py
metadata_configs = {
    'BE': {
        'url': 'https://isk.geobasis-bb.de/ows/aktualitaeten_wms?',
        'layer': 'bb_dop_info',
        'description': 'Berlin dedicated metadata service with orthophoto info (shared with Brandenburg)',
        'extra_params': {},
        'info_format': 'text/plain',
        'wms_version': '1.3.0',
    },
    'BB': {
        'url': 'https://isk.geobasis-bb.de/ows/aktualitaeten_wms?',
        'layer': 'bb_dop_info',
        'description': 'Brandenburg dedicated metadata service with orthophoto info (shared with Berlin)',
        'extra_params': {},
        'info_format': 'text/plain',
        'wms_version': '1.3.0',
    },
    'BW': {
        'url': 'https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_DOP_20_Bildflugkacheln_Aktualitaet?',
        'layer': 'v_dop_20_bildflugkacheln',
        'description': 'Baden-Württemberg dedicated metadata service with flight info',
        'extra_params': {'FORMAT': 'image/png'},
        'wms_version': '1.1.1',
    },
    'BY': {
        'layer': 'by_dop20_info',  # Uses same WMS service, different layer
        'description': 'Bayern metadata layer in same WMS service',
        'wms_version': '1.1.1',
    },
    'HE': {
        'url': 'https://www.gds-srv.hessen.de/cgi-bin/lika-services/ogc-free-images.ows?language=ger&',
        'layer': 'wms_he_dop',
        'description': 'Dedicated Hessen metadata service with detailed acquisition info',
        'extra_params': {},
        'wms_version': '1.3.0',
    },
    'MV': {
        'layer': 'mv_dop_info',  # Uses same WMS service
        'description': 'Mecklenburg-Vorpommern metadata layer',
        'wms_version': '1.3.0',
    },
    'NI': {
        'url': 'https://opendata.lgln.niedersachsen.de/doorman/noauth/dop_wms?language=ger&',
        'layer': 'ni_dop20_info',
        'description': 'Niedersachsen metadata service returning HTML',
        'extra_params': {'FORMAT': 'image/png', 'STYLES': ''},
        'info_format': 'text/html',
        'wms_version': '1.3.0',
    },
    'NW': {
        'layer': 'nw_dop_utm_info',  # Uses same WMS service
        'description': 'Nordrhein-Westfalen metadata layer',
        'wms_version': '1.1.1',
    },
    'RP': {
        'layer': 'rp_dop20_info',  # Uses same WMS service
        'description': 'Rheinland-Pfalz metadata layer',
        'wms_version': '1.3.0',
    },
    'SH': {
        'url': 'https://service.gdi-sh.de/WMS_SH_MD_DOP?',
        'layer': 'DOP20',
        'description': 'Schleswig-Holstein dedicated metadata WMS service',
        'extra_params': {},
        'wms_version': '1.1.1',
    },
    'SL': {
        'url': 'https://geoportal.saarland.de/freewms/truedop?',
        'layer': 'sl_dop_info',
        'description': 'Saarland metadata service',
        'extra_params': {'STYLES': ''},
        'info_format': 'text/html',
        'wms_version': '1.1.1',
    },
    'SN': {
        'layer': 'sn_dop_020_info',  # Uses same WMS service
        'description': 'Sachsen metadata layer',
        'wms_version': '1.3.0',
    },
    'ST': {
        'url': 'https://www.geodatenportal.sachsen-anhalt.de/wss/service/ST_LVermGeo_DOP_WMS_Kacheluebersicht/guest?',
        'layer': 'Aktualität_der_Orthophotos41668',
        'description': 'Sachsen-Anhalt metadata service',
        'extra_params': {},
        'info_format': 'text/html',
        'wms_version': '1.1.1',
    },
    'TH': {
        'layer': 'th_dop_info',  # Uses same WMS service
        'description': 'Thüringen metadata layer',
        'wms_version': '1.1.1',
    },
}

# Load current YAML
yaml_path = Path('src/orthophotos_downloader/wms_catalog/wms_services.yaml')
with open(yaml_path, 'r') as f:
    catalog = yaml.safe_load(f)

# Update services with metadata
for service in catalog['services']:
    state = service['state_code']
    
    if state in metadata_configs:
        config = metadata_configs[state]
        metadata = {}
        
        # Add metadata service URL if different from main service
        if 'url' in config:
            metadata['metadata_service_url'] = config['url']
        
        # Add metadata layer
        if 'layer' in config:
            metadata['metadata_layer'] = config['layer']
        
        # Add description
        if 'description' in config:
            metadata['metadata_description'] = config['description']
        
        # Add extra params if any
        if 'extra_params' in config and config['extra_params']:
            metadata['metadata_extra_params'] = config['extra_params']
        
        # Add info format if not text/plain
        if 'info_format' in config:
            metadata['metadata_info_format'] = config['info_format']
        
        # Add WMS version
        if 'wms_version' in config:
            metadata['metadata_wms_version'] = config['wms_version']
        
        # Add metadata section to service
        if metadata:
            service['metadata'] = metadata

# Save updated YAML
with open(yaml_path, 'w') as f:
    yaml.dump(catalog, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print(f"✅ Updated {len(catalog['services'])} services with metadata information")
print(f"✅ States with metadata: {len(metadata_configs)}")

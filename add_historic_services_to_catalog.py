"""
Add all historic WMS services to the catalog.
"""

import pandas as pd
import yaml
from pathlib import Path
import re

def extract_year_from_name(name):
    """Extract year or year range from service name."""
    year_patterns = [
        r'(\d{4})-(\d{4})',  # Year range like 2019-2021
        r'(\d{4})',          # Single year like 2020
    ]
    
    for pattern in year_patterns:
        match = re.search(pattern, name)
        if match:
            if len(match.groups()) == 2:
                return f"{match.group(1)}-{match.group(2)}"
            else:
                return match.group(1)
    return 'historic'

def create_service_id(state_code, service_type, year, index=0):
    """Create a unique service ID."""
    year_str = year.replace('-', '_')
    suffix = f"_{index}" if index > 0 else ""
    return f"{state_code}_{service_type}_DOP20_{year_str}{suffix}"

# State name mapping
STATE_NAMES = {
    'BW': 'Baden-Württemberg',
    'BY': 'Bayern',
    'BE': 'Berlin',
    'BB': 'Brandenburg',
    'HB': 'Bremen',
    'HH': 'Hamburg',
    'HE': 'Hessen',
    'MV': 'Mecklenburg-Vorpommern',
    'NI': 'Niedersachsen',
    'NW': 'Nordrhein-Westfalen',
    'RP': 'Rheinland-Pfalz',
    'SL': 'Saarland',
    'SN': 'Sachsen',
    'ST': 'Sachsen-Anhalt',
    'SH': 'Schleswig-Holstein',
    'TH': 'Thüringen',
}

# Read historic services
df = pd.read_excel('WMS_Overview.xlsx', sheet_name='Historic')

historic_services_to_add = []
current_state = None

# Track service IDs to ensure uniqueness
service_id_counts = {}

for idx, row in df.iterrows():
    if idx == 0:
        continue
    
    if pd.notna(row.get('State Code')):
        current_state = row.get('State Code')
    
    if pd.isna(row.get('Link')) or current_state is None:
        continue
    
    name = str(row.get('Name', ''))
    url = str(row.get('Link', ''))
    
    if name == 'nan' or url == 'nan' or 'http' not in url:
        continue
    
    has_rgb = str(row.get('Layers', '')).strip() == 'x'
    has_cir = pd.notna(row.get('Unnamed: 5')) and str(row.get('Unnamed: 5')).strip() == 'x'
    has_meta = pd.notna(row.get('Unnamed: 8')) and str(row.get('Unnamed: 8')).strip() == 'x'
    
    year = extract_year_from_name(name)
    service_type = 'RGB' if has_rgb else ('CIR' if has_cir else 'RGB')  # Default to RGB if unknown
    
    # Create unique service ID
    base_id = f"{current_state}_{service_type}_{year}"
    if base_id not in service_id_counts:
        service_id_counts[base_id] = 0
    count = service_id_counts[base_id]
    service_id_counts[base_id] += 1
    
    service_id = create_service_id(current_state, service_type, year, count)
    
    # Create service entry
    service = {
        'id': service_id,
        'state_code': current_state,
        'state_name': STATE_NAMES[current_state],
        'type': service_type,
        'resolution': 0.2,  # Most are DOP20
        'year': year,
        'url': url,
        'version': '1.3.0',
        'layer_name': None,  # Will be determined from GetCapabilities
        'crs': 'EPSG:25832',
        'format': 'image/png',
        'availability': 'historic',
        'description': name,
        'direct_download': False,
        'source': f"{STATE_NAMES[current_state]} - Historic",
        'requires_auth': False,
        'temporal_coverage': year,
    }
    
    # Add metadata info if available
    if has_meta:
        service['metadata'] = {
            'metadata_layer': None,  # Will need to be determined
            'metadata_description': f'{name} - metadata layer',
            'metadata_wms_version': '1.3.0'
        }
    
    historic_services_to_add.append(service)

print(f"\\nPrepared {len(historic_services_to_add)} historic services to add to catalog")

# Load current catalog
catalog_path = Path('src/orthophotos_downloader/wms_catalog/wms_services.yaml')
with open(catalog_path, 'r') as f:
    catalog = yaml.safe_load(f)

current_count = len(catalog['services'])
print(f"Current catalog: {current_count} services")

# Add historic services
catalog['services'].extend(historic_services_to_add)

new_count = len(catalog['services'])
print(f"New catalog: {new_count} services")
print(f"Added: {new_count - current_count} historic services")

# Save updated catalog
with open(catalog_path, 'w') as f:
    yaml.dump(catalog, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print(f"\\n✅ Catalog updated at {catalog_path}")
print(f"\\nNext steps:")
print("  1. Run validation script to test all historic services")
print("  2. Query GetCapabilities to get actual layer names")
print("  3. Update metadata layer information")

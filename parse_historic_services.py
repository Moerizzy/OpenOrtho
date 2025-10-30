"""
Parse and add historic WMS services from Excel to the catalog.
"""

import pandas as pd
import yaml
from pathlib import Path
import re

def extract_year_from_name(name):
    """Extract year or year range from service name."""
    # Match patterns like 2020, 2019-2021, 1960-1969, etc.
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
    return None

# Read historic services
df = pd.read_excel('WMS_Overview.xlsx', sheet_name='Historic')

print("=" * 100)
print("PROCESSING HISTORIC WMS SERVICES")
print("=" * 100)
print()

historic_services = []
current_state = None
current_state_name = None

for idx, row in df.iterrows():
    if idx == 0:  # Skip header
        continue
    
    # Update current state
    if pd.notna(row.get('State')) and pd.notna(row.get('State Code')):
        current_state = row.get('State Code')
        current_state_name = row.get('State')
    
    # Skip rows without links
    if pd.isna(row.get('Link')) or current_state is None:
        continue
    
    name = str(row.get('Name', ''))
    url = str(row.get('Link', ''))
    
    # Skip if name or URL is invalid
    if name == 'nan' or url == 'nan' or 'http' not in url:
        continue
    
    # Determine service type
    has_rgb = str(row.get('Layers', '')).strip() == 'x'
    has_cir = pd.notna(row.get('Unnamed: 5')) and str(row.get('Unnamed: 5')).strip() == 'x'
    has_meta = pd.notna(row.get('Unnamed: 8')) and str(row.get('Unnamed: 8')).strip() == 'x'
    
    # Extract year from name
    year = extract_year_from_name(name)
    
    service_type = 'RGB' if has_rgb else ('CIR' if has_cir else 'UNKNOWN')
    
    service_info = {
        'state_code': current_state,
        'state_name': current_state_name,
        'name': name,
        'url': url,
        'type': service_type,
        'year': year if year else 'historic',
        'has_meta': has_meta,
        'row_idx': idx
    }
    
    historic_services.append(service_info)
    
    year_str = f"[{year}]" if year else "[historic]"
    meta_str = "META" if has_meta else ""
    print(f"{idx:3d}. {current_state:3s} {year_str:15s} {service_type:4s} {meta_str:5s} | {name[:50]}")

print()
print(f"Total historic services found: {len(historic_services)}")
print()

# Group by state
by_state = {}
for s in historic_services:
    state = s['state_code']
    if state not in by_state:
        by_state[state] = []
    by_state[state].append(s)

print("Services per state:")
for state in sorted(by_state.keys()):
    services = by_state[state]
    print(f"  {state}: {len(services)} historic services")

print()
print("=" * 100)

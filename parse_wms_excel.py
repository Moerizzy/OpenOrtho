"""
Parse WMS_Overview.xlsx and add historical/additional WMS services to catalog.
"""

import pandas as pd
import yaml
from pathlib import Path

# Read Excel file
df = pd.read_excel('WMS_Overview.xlsx')

print("=" * 80)
print("Parsing WMS_Overview.xlsx")
print("=" * 80)
print()

# Parse services from Excel
services_to_add = []
current_state = None
current_state_code = None

for idx, row in df.iterrows():
    # Skip header row
    if idx == 0:
        continue
    
    # Skip rows without links
    if pd.isna(row['Link']):
        continue
    
    # Update current state if specified
    if pd.notna(row['State']) and pd.notna(row['State Code']):
        current_state = row['State']
        current_state_code = row['State Code']
    
    if current_state is None or current_state_code is None:
        continue
    
    # Parse service details
    name = str(row['Name']) if pd.notna(row['Name']) else ''
    link = str(row['Link'])
    
    # Check service types (columns are: RGB, CIR, IR, PAN, META)
    has_rgb = str(row['Layers']).strip() == 'x' if pd.notna(row['Layers']) else False
    has_cir = str(row['Unnamed: 5']).strip() == 'x' if pd.notna(row['Unnamed: 5']) else False
    has_ir = str(row['Unnamed: 6']).strip() == 'x' if pd.notna(row['Unnamed: 6']) else False
    has_pan = str(row['Unnamed: 7']).strip() == 'x' if pd.notna(row['Unnamed: 7']) else False
    has_meta = str(row['Unnamed: 8']).strip() == 'x' if pd.notna(row['Unnamed: 8']) else False
    
    service_info = {
        'state': current_state,
        'state_code': current_state_code,
        'name': name,
        'url': link,
        'has_rgb': has_rgb,
        'has_cir': has_cir,
        'has_ir': has_ir,
        'has_pan': has_pan,
        'has_meta': has_meta,
        'row_idx': idx
    }
    
    services_to_add.append(service_info)
    
    type_flags = []
    if has_rgb: type_flags.append('RGB')
    if has_cir: type_flags.append('CIR')
    if has_ir: type_flags.append('IR')
    if has_pan: type_flags.append('PAN')
    if has_meta: type_flags.append('META')
    
    print(f"{idx:2d}. {current_state_code:3s} | {', '.join(type_flags):20s} | {name[:45]}")
    print(f"    {link[:100]}")

print()
print(f"Total services found: {len(services_to_add)}")
print()

# Load current catalog
catalog_path = Path('src/orthophotos_downloader/wms_catalog/wms_services.yaml')
with open(catalog_path, 'r') as f:
    catalog = yaml.safe_load(f)

current_service_count = len(catalog['services'])
print(f"Current catalog has: {current_service_count} services")
print()

# Check which services are new
print("Checking for new services...")
existing_urls = {s['url'] for s in catalog['services']}
new_services_count = 0

for service in services_to_add:
    if service['url'] not in existing_urls:
        new_services_count += 1
        print(f"  NEW: {service['state_code']} - {service['name'][:50]}")

print()
print(f"New services to add: {new_services_count}")
print()

# Group by features to understand what we have
print("Summary by feature:")
rgb_services = [s for s in services_to_add if s['has_rgb']]
cir_services = [s for s in services_to_add if s['has_cir']]
ir_services = [s for s in services_to_add if s['has_ir']]
pan_services = [s for s in services_to_add if s['has_pan']]
meta_services = [s for s in services_to_add if s['has_meta']]

print(f"  RGB services: {len(rgb_services)}")
print(f"  CIR services: {len(cir_services)}")
print(f"  IR services: {len(ir_services)}")
print(f"  PAN services: {len(pan_services)}")
print(f"  META services: {len(meta_services)}")

print()
print("=" * 80)

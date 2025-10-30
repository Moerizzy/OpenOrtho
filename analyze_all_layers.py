#!/usr/bin/env python3
"""
Analyze all WMS services and extract ALL available layers including years and metadata.
This will help us create separate service entries for each year and identify metadata layers.
"""

import yaml
import requests
from xml.etree import ElementTree as ET
import time
import json
from typing import Optional, List, Dict

def get_wms_layers_detailed(url: str, version: str = "1.3.0") -> Optional[List[Dict]]:
    """
    Query WMS GetCapabilities and extract all layer details.
    
    Returns:
        List of dicts with layer info (name, title, abstract, queryable), or None if request fails
    """
    try:
        params = {
            'SERVICE': 'WMS',
            'REQUEST': 'GetCapabilities',
            'VERSION': version
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        layers = []
        
        # Find all Layer elements
        for layer_elem in root.findall('.//{http://www.opengis.net/wms}Layer'):
            name_elem = layer_elem.find('{http://www.opengis.net/wms}Name')
            if name_elem is not None and name_elem.text:
                title_elem = layer_elem.find('{http://www.opengis.net/wms}Title')
                abstract_elem = layer_elem.find('{http://www.opengis.net/wms}Abstract')
                queryable = layer_elem.get('queryable', '0')
                
                layers.append({
                    'name': name_elem.text,
                    'title': title_elem.text if title_elem is not None else '',
                    'abstract': abstract_elem.text if abstract_elem is not None else '',
                    'queryable': queryable == '1'
                })
        
        # If no layers found with namespace, try without
        if not layers:
            for layer_elem in root.findall('.//Layer'):
                name_elem = layer_elem.find('Name')
                if name_elem is not None and name_elem.text:
                    title_elem = layer_elem.find('Title')
                    abstract_elem = layer_elem.find('Abstract')
                    queryable = layer_elem.get('queryable', '0')
                    
                    layers.append({
                        'name': name_elem.text,
                        'title': title_elem.text if title_elem is not None else '',
                        'abstract': abstract_elem.text if abstract_elem is not None else '',
                        'queryable': queryable == '1'
                    })
        
        return layers if layers else None
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:100]}")
        return None


def categorize_layers(layers: List[Dict]) -> Dict:
    """Categorize layers into image layers, info layers, and metadata layers."""
    
    result = {
        'image_layers': [],      # Actual image data layers
        'info_layers': [],       # _info suffix layers (metadata)
        'metadata_layers': [],   # Layers with 'meta', 'aktualitaet', 'info' in name
        'yearly_layers': [],     # Layers with years (1960, 2020, etc.)
        'parent_layers': [],     # Parent/group layers (usually non-queryable)
        'other_layers': []
    }
    
    for layer in layers:
        name = layer['name']
        name_lower = name.lower()
        
        # Info layers (metadata about images)
        if name.endswith('_info'):
            result['info_layers'].append(layer)
        # Metadata/Aktualitaet layers
        elif any(keyword in name_lower for keyword in ['meta', 'aktualitaet', 'aktualität', 'bildflug']):
            result['metadata_layers'].append(layer)
        # Yearly layers (contains 4-digit year or year range)
        elif any(year in name for year in [str(y) for y in range(1940, 2030)]):
            result['yearly_layers'].append(layer)
        # Parent layers (usually not queryable, serve as containers)
        elif not layer['queryable'] or name.startswith('WMS_'):
            result['parent_layers'].append(layer)
        # Image layers
        else:
            result['image_layers'].append(layer)
    
    return result


def analyze_service(service: Dict, output_file):
    """Analyze a single WMS service and write details to file."""
    
    service_id = service.get('id', 'unknown')
    url = service.get('url')
    version = service.get('version', '1.3.0')
    current_layer = service.get('layer_name')
    
    output_file.write(f"\n{'='*100}\n")
    output_file.write(f"SERVICE: {service_id}\n")
    output_file.write(f"{'='*100}\n")
    output_file.write(f"URL: {url}\n")
    output_file.write(f"Current layer: {current_layer}\n")
    output_file.write(f"State: {service.get('state_code')} - {service.get('state_name')}\n")
    output_file.write(f"Type: {service.get('type')}\n")
    output_file.write(f"Temporal coverage: {service.get('temporal_coverage', 'N/A')}\n")
    
    print(f"\n[{service_id}]")
    print(f"  URL: {url}")
    
    # Query GetCapabilities
    layers = get_wms_layers_detailed(url, version)
    
    if not layers:
        output_file.write("\n❌ Failed to retrieve layers\n")
        print(f"  ❌ Failed")
        return
    
    print(f"  ✅ Found {len(layers)} layers")
    
    # Categorize layers
    categorized = categorize_layers(layers)
    
    output_file.write(f"\nTOTAL LAYERS: {len(layers)}\n")
    output_file.write(f"\n📸 IMAGE LAYERS ({len(categorized['image_layers'])}):\n")
    for layer in categorized['image_layers']:
        output_file.write(f"  - {layer['name']}\n")
        if layer['title']:
            output_file.write(f"    Title: {layer['title']}\n")
    
    output_file.write(f"\n📅 YEARLY LAYERS ({len(categorized['yearly_layers'])}):\n")
    for layer in categorized['yearly_layers']:
        output_file.write(f"  - {layer['name']}\n")
        if layer['title']:
            output_file.write(f"    Title: {layer['title']}\n")
    
    output_file.write(f"\nℹ️  INFO/METADATA LAYERS ({len(categorized['info_layers'])}):\n")
    for layer in categorized['info_layers']:
        output_file.write(f"  - {layer['name']}\n")
        if layer['title']:
            output_file.write(f"    Title: {layer['title']}\n")
    
    output_file.write(f"\n🔍 METADATA LAYERS ({len(categorized['metadata_layers'])}):\n")
    for layer in categorized['metadata_layers']:
        output_file.write(f"  - {layer['name']}\n")
        if layer['title']:
            output_file.write(f"    Title: {layer['title']}\n")
    
    output_file.write(f"\n📁 PARENT/GROUP LAYERS ({len(categorized['parent_layers'])}):\n")
    for layer in categorized['parent_layers']:
        output_file.write(f"  - {layer['name']} (queryable: {layer['queryable']})\n")
        if layer['title']:
            output_file.write(f"    Title: {layer['title']}\n")
    
    # Recommendations
    output_file.write(f"\n💡 RECOMMENDATIONS:\n")
    
    if categorized['yearly_layers']:
        output_file.write(f"  ⚠️  This service has {len(categorized['yearly_layers'])} yearly layers!\n")
        output_file.write(f"     Consider creating separate service entries for each year.\n")
        output_file.write(f"     Years available: ")
        years = []
        for layer in categorized['yearly_layers']:
            # Extract years from layer names
            import re
            year_matches = re.findall(r'\b(19\d{2}|20\d{2})\b', layer['name'])
            years.extend(year_matches)
        output_file.write(f"{', '.join(sorted(set(years)))}\n")
    
    if categorized['info_layers']:
        output_file.write(f"  ℹ️  {len(categorized['info_layers'])} info layers available for metadata!\n")
        output_file.write(f"     These can be used as metadata_layer in service config.\n")
    
    if categorized['metadata_layers']:
        output_file.write(f"  🔍 {len(categorized['metadata_layers'])} metadata/aktualitaet layers found!\n")
    
    if current_layer and current_layer != 'None':
        # Check if current layer is appropriate
        all_layer_names = [l['name'] for l in layers]
        if current_layer not in all_layer_names:
            output_file.write(f"  ⚠️  WARNING: Current layer '{current_layer}' not found in GetCapabilities!\n")
        elif current_layer in [l['name'] for l in categorized['parent_layers']]:
            output_file.write(f"  ⚠️  Current layer '{current_layer}' is a parent layer (might not work for GetMap)!\n")


def main():
    catalog_path = 'src/orthophotos_downloader/wms_catalog/wms_services.yaml'
    output_path = 'wms_layers_analysis.txt'
    
    print("WMS Layers Analysis Tool")
    print("=" * 100)
    print()
    
    # Load catalog
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = yaml.safe_load(f)
    
    services = catalog.get('services', [])
    
    print(f"Analyzing {len(services)} services...")
    print(f"Output will be saved to: {output_path}")
    print()
    
    with open(output_path, 'w', encoding='utf-8') as output_file:
        output_file.write("WMS LAYERS ANALYSIS\n")
        output_file.write("=" * 100 + "\n")
        output_file.write(f"Total services: {len(services)}\n")
        output_file.write(f"Analysis date: 2025-10-29\n")
        
        for i, service in enumerate(services, 1):
            analyze_service(service, output_file)
            
            # Be nice to servers
            if i < len(services):
                time.sleep(0.5)
    
    print()
    print("=" * 100)
    print(f"✅ Analysis complete!")
    print(f"📄 Full details saved to: {output_path}")
    print()
    print("Next steps:")
    print("  1. Review wms_layers_analysis.txt")
    print("  2. Identify services that need multiple entries (one per year)")
    print("  3. Update catalog with all yearly layers")
    print("  4. Add metadata layer configurations where available")


if __name__ == '__main__':
    main()

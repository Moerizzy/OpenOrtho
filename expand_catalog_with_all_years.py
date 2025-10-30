#!/usr/bin/env python3
"""
Expand WMS catalog to include ALL yearly layers and metadata layers.
This will transform services with multiple year layers into separate catalog entries.
"""

import yaml
import re
from typing import Dict, List

# Load the detailed layer analysis
def load_analysis(analysis_file: str) -> Dict:
    """Parse the wms_layers_analysis.txt file to get all layers per service."""
    
    service_layers = {}
    current_service = None
    current_section = None
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        for line in f:
            # Detect service start
            if line.startswith('SERVICE:'):
                current_service = line.split('SERVICE:')[1].strip()
                service_layers[current_service] = {
                    'image_layers': [],
                    'yearly_layers': [],
                    'info_layers': [],
                    'metadata_layers': [],
                    'parent_layers': []
                }
            
            # Detect section starts
            elif '📸 IMAGE LAYERS' in line:
                current_section = 'image_layers'
            elif '📅 YEARLY LAYERS' in line:
                current_section = 'yearly_layers'
            elif 'ℹ️  INFO/METADATA LAYERS' in line:
                current_section = 'info_layers'
            elif '🔍 METADATA LAYERS' in line:
                current_section = 'metadata_layers'
            elif '📁 PARENT/GROUP LAYERS' in line:
                current_section = 'parent_layers'
            elif '💡 RECOMMENDATIONS' in line:
                current_section = None
            
            # Parse layer entries
            elif current_service and current_section and line.strip().startswith('- '):
                layer_name = line.strip()[2:].split(' (queryable')[0]
                service_layers[current_service][current_section].append(layer_name)
    
    return service_layers


def expand_catalog(catalog_path: str, analysis_file: str, output_path: str):
    """Expand catalog with all yearly layers."""
    
    # Load existing catalog
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = yaml.safe_load(f)
    
    # Load layer analysis
    service_layers = load_analysis(analysis_file)
    
    existing_services = catalog.get('services', [])
    expanded_services = []
    
    stats = {
        'original': len(existing_services),
        'expanded': 0,
        'added_years': 0,
        'added_metadata': 0
    }
    
    print(f"Expanding catalog from {stats['original']} services...")
    print("=" * 100)
    
    for service in existing_services:
        service_id = service.get('id')
        
        # Get layers for this service
        layers_info = service_layers.get(service_id, {})
        yearly_layers = layers_info.get('yearly_layers', [])
        info_layers = layers_info.get('info_layers', [])
        
        print(f"\n{service_id}:")
        print(f"  Yearly layers: {len(yearly_layers)}")
        print(f"  Info layers: {len(info_layers)}")
        
        # If no yearly layers, keep service as-is
        if not yearly_layers:
            # But update layer_name if currently None
            if service.get('layer_name') in [None, 'None']:
                # Use first image layer or parent layer
                image_layers = layers_info.get('image_layers', [])
                parent_layers = layers_info.get('parent_layers', [])
                if image_layers:
                    service['layer_name'] = image_layers[0]
                    print(f"  → Updated layer_name to: {image_layers[0]}")
                elif parent_layers:
                    service['layer_name'] = parent_layers[0]
                    print(f"  → Updated layer_name to: {parent_layers[0]}")
            
            expanded_services.append(service)
            continue
        
        # Service has yearly layers - create one entry per year
        print(f"  → Expanding to {len(yearly_layers)} yearly services...")
        
        for year_layer in yearly_layers:
            # Extract year from layer name
            year_match = re.search(r'(19\d{2}|20\d{2})', year_layer)
            year = year_match.group(1) if year_match else 'unknown'
            
            # Find matching info/metadata layer
            metadata_layer = None
            for info_layer in info_layers:
                if year in info_layer:
                    metadata_layer = info_layer
                    break
            
            # Create new service entry
            new_service = service.copy()
            
            # Update ID to include year
            base_id = service_id.replace('_historic', '').replace('_1', '').replace('_2', '')
            new_id = f"{base_id}_{year}"
            new_service['id'] = new_id
            
            # Update fields
            new_service['layer_name'] = year_layer
            new_service['year'] = year
            new_service['temporal_coverage'] = year
            
            # Add description
            desc = service.get('description', '')
            new_service['description'] = f"{desc} - Year {year}".strip(' -')
            
            # Add metadata if found
            if metadata_layer:
                if 'metadata' not in new_service:
                    new_service['metadata'] = {}
                
                # If service already has metadata config, update layer
                if isinstance(new_service.get('metadata'), dict):
                    new_service['metadata']['metadata_layer'] = metadata_layer
                    new_service['metadata']['metadata_description'] = f"Metadata for {year}"
                else:
                    # Create new metadata config using same service URL
                    new_service['metadata'] = {
                        'metadata_service_url': service.get('url'),
                        'metadata_layer': metadata_layer,
                        'metadata_description': f"Metadata for {year}",
                        'metadata_wms_version': service.get('version', '1.3.0')
                    }
                
                stats['added_metadata'] += 1
            
            expanded_services.append(new_service)
            stats['added_years'] += 1
    
    stats['expanded'] = len(expanded_services)
    
    # Update catalog
    catalog['services'] = expanded_services
    catalog['last_updated'] = '2025-10-29'
    
    # Save expanded catalog
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(catalog, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print("\n" + "=" * 100)
    print("EXPANSION COMPLETE!")
    print(f"  Original services: {stats['original']}")
    print(f"  Expanded services: {stats['expanded']}")
    print(f"  Added yearly entries: {stats['added_years']}")
    print(f"  Services with metadata: {stats['added_metadata']}")
    print(f"\n✅ Expanded catalog saved to: {output_path}")
    
    return stats


if __name__ == '__main__':
    catalog_path = 'src/orthophotos_downloader/wms_catalog/wms_services.yaml'
    analysis_file = 'wms_layers_analysis.txt'
    output_path = 'wms_services_expanded.yaml'
    
    print("WMS Catalog Expansion Tool")
    print("=" * 100)
    print()
    
    stats = expand_catalog(catalog_path, analysis_file, output_path)
    
    print("\nNext steps:")
    print("  1. Review wms_services_expanded.yaml")
    print("  2. Test a few expanded services")
    print("  3. Backup current catalog and replace with expanded version")
    print(f"     mv src/orthophotos_downloader/wms_catalog/wms_services.yaml src/orthophotos_downloader/wms_catalog/wms_services.yaml.backup")
    print(f"     mv wms_services_expanded.yaml src/orthophotos_downloader/wms_catalog/wms_services.yaml")

#!/usr/bin/env python3
"""
Query GetCapabilities for all WMS services and update layer names in catalog.
This will replace all layer_name: None entries with actual layer names from WMS.
"""

import yaml
import requests
from xml.etree import ElementTree as ET
import time
from typing import Optional, List

def get_wms_layers(url: str, version: str = "1.3.0") -> Optional[List[str]]:
    """
    Query WMS GetCapabilities and extract all layer names.
    
    Args:
        url: Base WMS URL
        version: WMS version (1.1.1 or 1.3.0)
    
    Returns:
        List of layer names, or None if request fails
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
        
        # Find all layer names (skip parent layers without actual data)
        # WMS 1.3.0 uses different namespace
        namespaces = {
            '': 'http://www.opengis.net/wms',
            'wms': 'http://www.opengis.net/wms'
        }
        
        layers = []
        
        # Try without namespace first (some services don't use it)
        for layer in root.findall('.//Layer/Name', namespaces):
            if layer.text:
                layers.append(layer.text)
        
        # If no layers found, try without namespace
        if not layers:
            for layer in root.findall('.//Layer/Name'):
                if layer.text:
                    layers.append(layer.text)
        
        # Filter out parent layers (usually they don't have queryable="1")
        # For now, return all layers and let user choose
        return layers if layers else None
        
    except Exception as e:
        print(f"  ❌ Error querying {url}: {str(e)[:100]}")
        return None


def update_catalog_layer_names(catalog_path: str, dry_run: bool = False):
    """
    Update all layer names in the catalog by querying GetCapabilities.
    
    Args:
        catalog_path: Path to wms_services.yaml
        dry_run: If True, only print what would be changed
    """
    # Load catalog
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = yaml.safe_load(f)
    
    services = catalog.get('services', [])
    
    print(f"Processing {len(services)} services...")
    print("=" * 100)
    
    updated_count = 0
    error_count = 0
    already_set_count = 0
    
    for i, service in enumerate(services, 1):
        service_id = service.get('id', 'unknown')
        url = service.get('url')
        version = service.get('version', '1.3.0')
        current_layer = service.get('layer_name')
        
        print(f"\n[{i}/{len(services)}] {service_id}")
        print(f"  URL: {url}")
        print(f"  Current layer: {current_layer}")
        
        if current_layer and current_layer != 'None':
            print(f"  ✓ Layer already set, skipping")
            already_set_count += 1
            continue
        
        # Query GetCapabilities
        layers = get_wms_layers(url, version)
        
        if layers:
            print(f"  ✅ Found {len(layers)} layers: {layers}")
            
            # Use first layer if only one, otherwise list them
            if len(layers) == 1:
                new_layer = layers[0]
                print(f"  → Will update to: {new_layer}")
                
                if not dry_run:
                    service['layer_name'] = new_layer
                updated_count += 1
            else:
                # Multiple layers - try to pick the most relevant one
                # Look for common patterns like DOP, RGB, etc.
                preferred_layer = None
                
                # Try to match service ID patterns
                service_type = service.get('type', 'RGB').upper()
                
                for layer in layers:
                    layer_upper = layer.upper()
                    if service_type in layer_upper or 'DOP' in layer_upper:
                        preferred_layer = layer
                        break
                
                if not preferred_layer:
                    preferred_layer = layers[0]  # Default to first
                
                print(f"  → Will update to: {preferred_layer} (from {len(layers)} options)")
                print(f"     Other options: {layers[1:] if len(layers) > 1 else []}")
                
                if not dry_run:
                    service['layer_name'] = preferred_layer
                updated_count += 1
        else:
            print(f"  ❌ Failed to get layers")
            error_count += 1
        
        # Be nice to servers
        time.sleep(0.5)
    
    print("\n" + "=" * 100)
    print("SUMMARY:")
    print(f"  ✅ Updated: {updated_count}")
    print(f"  ✓ Already set: {already_set_count}")
    print(f"  ❌ Errors: {error_count}")
    print(f"  Total: {len(services)}")
    
    if not dry_run and updated_count > 0:
        # Backup original
        backup_path = catalog_path + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            yaml.dump(catalog, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"\n✅ Backup saved to {backup_path}")
        
        # Save updated catalog
        with open(catalog_path, 'w', encoding='utf-8') as f:
            yaml.dump(catalog, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"✅ Updated catalog saved to {catalog_path}")
    elif dry_run:
        print("\n⚠️  DRY RUN - No changes made")
        print("   Run with dry_run=False to apply changes")


if __name__ == '__main__':
    catalog_path = 'src/orthophotos_downloader/wms_catalog/wms_services.yaml'
    
    print("WMS Layer Name Update Tool")
    print("=" * 100)
    print()
    
    # Run in normal mode (not dry run)
    update_catalog_layer_names(catalog_path, dry_run=False)
    
    print("\n" + "=" * 100)
    print("✅ Complete!")
    print()
    print("Next steps:")
    print("  1. Review the updated layer names")
    print("  2. Test downloads with updated layer names")
    print("  3. Update metadata layers if needed")

"""
Validate WMS services from the catalog by making GetCapabilities requests.
"""

import requests
import yaml
from pathlib import Path
from xml.etree import ElementTree as ET
import time

def validate_wms_service(url, service_name, timeout=10):
    """
    Validate a WMS service by making a GetCapabilities request.
    
    Returns: (status, message, layers)
    """
    # Clean URL - ensure it ends with ? or &
    if '?' not in url:
        url = url + '?'
    elif not url.endswith('?') and not url.endswith('&'):
        url = url + '&'
    
    # Build GetCapabilities request
    params = {
        'SERVICE': 'WMS',
        'REQUEST': 'GetCapabilities',
        'VERSION': '1.3.0'
    }
    
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Find layers
        # Handle different XML namespaces
        namespaces = {
            'wms': 'http://www.opengis.net/wms',
            '': ''  # Default namespace
        }
        
        layers = []
        # Try with namespace
        for layer in root.findall('.//wms:Layer/wms:Name', namespaces):
            if layer.text:
                layers.append(layer.text)
        
        # Try without namespace if no layers found
        if not layers:
            for layer in root.findall('.//Layer/Name'):
                if layer.text:
                    layers.append(layer.text)
        
        if layers:
            return 'OK', f'Found {len(layers)} layers', layers
        else:
            return 'WARNING', 'Service responds but no layers found', []
            
    except requests.exceptions.Timeout:
        return 'ERROR', f'Timeout after {timeout}s', []
    except requests.exceptions.RequestException as e:
        return 'ERROR', f'Request failed: {str(e)[:100]}', []
    except ET.ParseError as e:
        return 'ERROR', f'XML parse error: {str(e)[:100]}', []
    except Exception as e:
        return 'ERROR', f'Unexpected error: {str(e)[:100]}', []


def main():
    print("=" * 100)
    print("WMS SERVICE VALIDATION")
    print("=" * 100)
    print()
    
    # Load catalog
    catalog_path = Path('src/orthophotos_downloader/wms_catalog/wms_services.yaml')
    with open(catalog_path, 'r') as f:
        catalog = yaml.safe_load(f)
    
    services = catalog['services']
    
    print(f"Testing {len(services)} services from catalog...")
    print()
    
    results = {
        'OK': [],
        'WARNING': [],
        'ERROR': []
    }
    
    for idx, service in enumerate(services, 1):
        service_id = service['id']
        state_code = service['state_code']
        url = service['url']
        
        print(f"{idx:2d}/{len(services)} Testing {service_id:30s} ({state_code})...", end=' ', flush=True)
        
        status, message, layers = validate_wms_service(url, service_id)
        
        results[status].append({
            'id': service_id,
            'state': state_code,
            'url': url,
            'message': message,
            'layers': layers
        })
        
        # Color output
        if status == 'OK':
            print(f"✅ {message}")
        elif status == 'WARNING':
            print(f"⚠️  {message}")
        else:
            print(f"❌ {message}")
        
        # Small delay to be nice to servers
        time.sleep(0.2)
    
    print()
    print("=" * 100)
    print("VALIDATION SUMMARY")
    print("=" * 100)
    print()
    print(f"✅ Working: {len(results['OK'])}")
    print(f"⚠️  Warnings: {len(results['WARNING'])}")
    print(f"❌ Errors: {len(results['ERROR'])}")
    print()
    
    if results['WARNING']:
        print("Services with warnings:")
        for r in results['WARNING']:
            print(f"  ⚠️  {r['id']:30s} - {r['message']}")
        print()
    
    if results['ERROR']:
        print("Services with errors:")
        for r in results['ERROR']:
            print(f"  ❌ {r['id']:30s}")
            print(f"     {r['message']}")
            print(f"     {r['url'][:80]}")
        print()
    
    # Show sample of layers from working services
    if results['OK']:
        print("Sample layers from working services:")
        for r in results['OK'][:5]:  # Show first 5
            print(f"\n  {r['id']} ({len(r['layers'])} layers):")
            for layer in r['layers'][:3]:  # Show first 3 layers
                print(f"    - {layer}")
            if len(r['layers']) > 3:
                print(f"    ... and {len(r['layers']) - 3} more")
    
    print()
    print("=" * 100)
    
    # Save detailed results
    output_file = 'wms_validation_results.txt'
    with open(output_file, 'w') as f:
        f.write("WMS SERVICE VALIDATION RESULTS\n")
        f.write("=" * 100 + "\n\n")
        
        for status in ['OK', 'WARNING', 'ERROR']:
            f.write(f"\n{status} ({len(results[status])} services)\n")
            f.write("-" * 100 + "\n")
            for r in results[status]:
                f.write(f"\n{r['id']}\n")
                f.write(f"  State: {r['state']}\n")
                f.write(f"  URL: {r['url']}\n")
                f.write(f"  Status: {r['message']}\n")
                if r['layers']:
                    f.write(f"  Layers ({len(r['layers'])}):\n")
                    for layer in r['layers'][:10]:  # First 10
                        f.write(f"    - {layer}\n")
                    if len(r['layers']) > 10:
                        f.write(f"    ... and {len(r['layers']) - 10} more\n")
    
    print(f"Detailed results saved to: {output_file}")
    print()


if __name__ == '__main__':
    main()

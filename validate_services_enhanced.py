"""
Enhanced WMS service validation with layer name checking.
"""

import argparse
import json
import requests
import yaml
from pathlib import Path
from xml.etree import ElementTree as ET
import time
from collections import defaultdict

from orthophotos_downloader.data_scraping.file_downloader import FileServiceDownloader

def validate_wms_service(service):
    """
    Validate a WMS service and check if the specified layer exists.
    
    Returns: (status, message, layers, layer_found)
    """
    # Get URL - prefer wms_url, fallback to url
    url = service.get('wms_url') or service.get('url')
    if not url:
        return 'ERROR', 'No URL specified', [], False
    
    # Get specified layer name
    specified_layer = service.get('layer_name', '')
    
    # Clean URL - ensure it ends with ? or &
    if '?' not in url:
        url = url + '?'
    elif not url.endswith('?') and not url.endswith('&'):
        url = url + '&'
    
    # Get version
    version = service.get('wms_version') or service.get('version', '1.3.0')
    
    # Build GetCapabilities request
    params = {
        'SERVICE': 'WMS',
        'REQUEST': 'GetCapabilities',
        'VERSION': version
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Find layers - handle different namespaces
        layers = []
        
        # Try with namespace
        for layer in root.findall('.//{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Name'):
            if layer.text:
                layers.append(layer.text)
        
        # Try without namespace if no layers found
        if not layers:
            for layer in root.findall('.//Layer/Name'):
                if layer.text:
                    layers.append(layer.text)
        
        if not layers:
            return 'WARNING', 'Service responds but no layers found', [], False
        
        # Check if specified layer exists
        layer_found = specified_layer in layers if specified_layer else None
        
        if specified_layer and not layer_found:
            return 'WARNING', f'Layer "{specified_layer}" not found ({len(layers)} layers available)', layers, False
        
        return 'OK', f'Found {len(layers)} layers', layers, layer_found
            
    except requests.exceptions.Timeout:
        return 'ERROR', 'Timeout after 15s', [], False
    except requests.exceptions.RequestException as e:
        return 'ERROR', f'Request failed: {str(e)[:80]}', [], False
    except ET.ParseError as e:
        return 'ERROR', f'XML parse error: {str(e)[:80]}', [], False
    except Exception as e:
        return 'ERROR', f'Unexpected error: {str(e)[:80]}', [], False


def validate_wcs_service(service):
    files = service.get('files', {})
    url = files.get('wcs_url') or service.get('wcs_url') or service.get('url')
    if not url:
        return 'ERROR', 'No WCS URL specified', [], None

    if '?' not in url:
        url = url + '?'
    elif not url.endswith('?') and not url.endswith('&'):
        url = url + '&'

    params = {
        'SERVICE': 'WCS',
        'REQUEST': 'GetCapabilities',
        'VERSION': files.get('wcs_version') or service.get('wcs_version') or '2.0.1'
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        coverages = []
        for elem in root.findall('.//{http://www.opengis.net/wcs/2.0}CoverageId'):
            if elem.text:
                coverages.append(elem.text)
        if not coverages:
            for elem in root.findall('.//CoverageId'):
                if elem.text:
                    coverages.append(elem.text)
        if not coverages:
            for elem in root.findall('.//{http://www.opengis.net/wcs/1.1}Identifier'):
                if elem.text:
                    coverages.append(elem.text)

        coverage_id = files.get('wcs_coverage') or service.get('wcs_coverage')
        if coverage_id and coverage_id not in coverages:
            return 'WARNING', f'Coverage "{coverage_id}" not found ({len(coverages)} available)', coverages, None

        message = f'Found {len(coverages)} coverages'
        return 'OK', message, coverages, None

    except requests.exceptions.Timeout:
        return 'ERROR', 'Timeout after 15s', [], None
    except requests.exceptions.RequestException as e:
        return 'ERROR', f'Request failed: {str(e)[:80]}', [], None
    except ET.ParseError as e:
        return 'ERROR', f'XML parse error: {str(e)[:80]}', [], None
    except Exception as e:
        return 'ERROR', f'Unexpected error: {str(e)[:80]}', [], None


def validate_atom_service(service):
    files = service.get('files', {})
    feed_url = files.get('atom_feed_url')
    if not feed_url:
        return 'ERROR', 'No Atom feed URL specified', [], None

    try:
        response = requests.get(feed_url, timeout=30)
        response.raise_for_status()
        entries = FileServiceDownloader._parse_atom_feed(response.content)
        message = f'Found {len(entries)} tiles'
        sample = [entry.get('code') or entry.get('title') for entry in entries[:5]]
        return ('OK' if entries else 'WARNING'), message, sample, None
    except requests.exceptions.Timeout:
        return 'ERROR', 'Timeout after 30s', [], None
    except requests.exceptions.RequestException as e:
        return 'ERROR', f'Request failed: {str(e)[:80]}', [], None
    except Exception as e:
        return 'ERROR', f'Unexpected error: {str(e)[:80]}', [], None


def validate_geojson_service(service):
    files = service.get('files', {})
    url = files.get('geojson_url')
    if not url:
        return 'ERROR', 'No GeoJSON URL specified', [], None

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            features = data.get('features', [])
            message = f'Found {len(features)} tiles'
            return ('OK' if features else 'WARNING'), message, [], None
        return 'WARNING', 'GeoJSON response has unexpected format', [], None
    except requests.exceptions.Timeout:
        return 'ERROR', 'Timeout after 30s', [], None
    except requests.exceptions.RequestException as e:
        return 'ERROR', f'Request failed: {str(e)[:80]}', [], None
    except json.JSONDecodeError as e:
        return 'ERROR', f'JSON parse error: {str(e)[:80]}', [], None
    except Exception as e:
        return 'ERROR', f'Unexpected error: {str(e)[:80]}', [], None


def validate_files_url_service(service):
    files = service.get('files', {})
    url = files.get('url') or files.get('base_url') or service.get('files_url')
    if not url:
        return 'ERROR', 'No files URL specified', [], None

    try:
        response = requests.head(url, timeout=15)
        if response.status_code >= 400:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
        message = f'Endpoint reachable (status {response.status_code})'
        return 'OK', message, [], None
    except requests.exceptions.Timeout:
        return 'ERROR', 'Timeout after 15s', [], None
    except requests.exceptions.RequestException as e:
        return 'ERROR', f'Request failed: {str(e)[:80]}', [], None
    except Exception as e:
        return 'ERROR', f'Unexpected error: {str(e)[:80]}', [], None


def validate_service(service):
    files = service.get('files', {}) or {}
    index_type = files.get('index_type')

    if index_type == 'wcs':
        return validate_wcs_service(service), 'WCS'
    if index_type == 'atom':
        return validate_atom_service(service), 'ATOM'
    if index_type == 'geojson':
        return validate_geojson_service(service), 'GEOJSON'
    if index_type and (files.get('url') or files.get('base_url') or service.get('files_url')):
        return validate_files_url_service(service), 'FILES'
    if service.get('wms_url') or service.get('layer_name') or not index_type:
        return validate_wms_service(service), 'WMS'
    if files.get('url') or files.get('base_url') or service.get('files_url'):
        return validate_files_url_service(service), 'FILES'
    return (('WARNING', 'No validation handler for service', [], None), 'UNKNOWN')


def main():
    parser = argparse.ArgumentParser(description="Validate WMS services from the catalog with optional filters.")
    parser.add_argument('--state', action='append', help='Filter by state code (repeat or comma separated).')
    parser.add_argument('--year', action='append', help='Filter by year (repeat or comma separated).')
    parser.add_argument('--type', action='append', help='Filter by imagery type (RGB, CIR, RGBI, etc.).')
    parser.add_argument('--id', action='append', help='Filter by service id (substring match).')
    parser.add_argument('--limit', type=int, help='Limit the number of services validated after filtering.')
    parser.add_argument('--contains', action='append', help='Filter by substring contained in description or URL.')
    args = parser.parse_args()

    def _collect(values, transform=lambda x: x):
        if not values:
            return set()
        collected = set()
        for entry in values:
            if entry is None:
                continue
            for part in str(entry).split(','):
                cleaned = transform(part.strip())
                if cleaned:
                    collected.add(cleaned)
        return collected

    state_filters = _collect(args.state, lambda x: x.upper())
    year_filters = _collect(args.year, lambda x: str(x).lower())
    type_filters = _collect(args.type, lambda x: x.upper())
    id_filters = _collect(args.id, lambda x: x.lower())
    contains_filters = _collect(args.contains, lambda x: x.lower())

    print("=" * 100)
    print("ENHANCED SERVICE VALIDATION")
    print("=" * 100)
    print()
    
    # Load catalog
    catalog_path = Path('src/orthophotos_downloader/wms_catalog/wms_services.yaml')
    with open(catalog_path, 'r') as f:
        catalog = yaml.safe_load(f)
    
    services = catalog['services']

    filtered_services = services

    if state_filters:
        filtered_services = [
            s for s in filtered_services
            if s.get('state_code', '').upper() in state_filters
        ]

    if year_filters:
        filtered_services = [
            s for s in filtered_services
            if any(f in str(s.get('year', '')).lower() for f in year_filters)
        ]

    if type_filters:
        filtered_services = [
            s for s in filtered_services
            if s.get('type', '').upper() in type_filters
        ]

    if id_filters:
        filtered_services = [
            s for s in filtered_services
            if any(f in s.get('id', '').lower() for f in id_filters)
        ]

    if contains_filters:
        filtered_services = [
            s for s in filtered_services
            if any(
                f in (s.get('description', '') or '').lower()
                or f in (s.get('url', '') or '').lower()
                or f in (s.get('wms_url', '') or '').lower()
                for f in contains_filters
            )
        ]

    if args.limit is not None and args.limit >= 0:
        filtered_services = filtered_services[:args.limit]

    if not filtered_services:
        print("No services matched the provided filters.")
        return

    if len(filtered_services) != len(services):
        print(f"Testing {len(filtered_services)} services from catalog (filtered from {len(services)} total)...")
    else:
        print(f"Testing {len(filtered_services)} services from catalog...")
    print()
    
    results = {
        'OK': [],
        'WARNING': [],
        'ERROR': []
    }
    
    layer_mismatches = []
    
    for idx, service in enumerate(filtered_services, 1):
        service_id = service['id']
        state_code = service.get('state_code', '??')
        
        (validation_result, validation_mode) = validate_service(service)
        status, message, layers, layer_found = validation_result

        print(f"{idx:3d}/{len(filtered_services)} {service_id:35s} ({state_code})...", end=' ', flush=True)

        files = service.get('files', {}) or {}
        if validation_mode == 'WCS':
            service_url = files.get('wcs_url') or service.get('wcs_url') or service.get('url', 'NO URL')
        elif validation_mode == 'ATOM':
            service_url = files.get('atom_feed_url') or service.get('url', 'NO URL')
        elif validation_mode == 'GEOJSON':
            service_url = files.get('geojson_url') or service.get('url', 'NO URL')
        elif validation_mode == 'FILES':
            service_url = files.get('url') or files.get('base_url') or service.get('files_url') or service.get('url', 'NO URL')
        else:
            service_url = service.get('wms_url') or service.get('url', 'NO URL')

        result = {
            'id': service_id,
            'state': state_code,
            'url': service_url,
            'message': message,
            'layers': layers,
            'specified_layer': service.get('layer_name', '') if validation_mode == 'WMS' else '',
            'layer_found': layer_found,
            'mode': validation_mode,
        }

        results[status].append(result)

        if result['specified_layer'] and layer_found is False:
            layer_mismatches.append(result)

        prefix = {
            'OK': '✅',
            'WARNING': '⚠️ ',
            'ERROR': '❌'
        }.get(status, '')

        if status == 'OK' and result['specified_layer'] and layer_found is False:
            print(f"⚠️  [{validation_mode}] {message} - LAYER MISMATCH!")
        else:
            print(f"{prefix} [{validation_mode}] {message}")
        
        # Small delay to be nice to servers
        time.sleep(0.1)
    
    print()
    print("=" * 100)
    print("VALIDATION SUMMARY")
    print("=" * 100)
    print()
    print(f"✅ Working: {len(results['OK'])}")
    print(f"⚠️  Warnings: {len(results['WARNING'])}")
    print(f"❌ Errors: {len(results['ERROR'])}")
    print(f"🔍 Layer mismatches: {len(layer_mismatches)}")
    print()
    
    # Show layer mismatches
    if layer_mismatches:
        print("=" * 100)
        print("LAYER NAME MISMATCHES (Catalog layer not found in WMS)")
        print("=" * 100)
        print()
        for r in layer_mismatches:
            print(f"Service: {r['id']}")
            print(f"  Specified layer: {r['specified_layer']}")
            print(f"  Available layers ({len(r['layers'])}):")
            for layer in r['layers'][:5]:
                print(f"    - {layer}")
            if len(r['layers']) > 5:
                print(f"    ... and {len(r['layers']) - 5} more")
            print()
    
    # Show errors
    if results['ERROR']:
        print("=" * 100)
        print("SERVICES WITH ERRORS")
        print("=" * 100)
        print()
        for r in results['ERROR'][:20]:  # Show first 20
            print(f"❌ {r['id']}")
            mode_str = f"[{r.get('mode', 'WMS')}] " if r.get('mode') else ''
            print(f"   {mode_str}{r['message']}")
            print(f"   {r['url'][:80]}")
            print()
        if len(results['ERROR']) > 20:
            print(f"   ... and {len(results['ERROR']) - 20} more errors")
    
    # Group by state
    print()
    print("=" * 100)
    print("SUMMARY BY STATE")
    print("=" * 100)
    print()
    
    by_state = defaultdict(lambda: {'ok': 0, 'warning': 0, 'error': 0, 'total': 0})
    
    for status in ['OK', 'WARNING', 'ERROR']:
        for r in results[status]:
            state = r['state']
            by_state[state][status.lower()] += 1
            by_state[state]['total'] += 1
    
    for state in sorted(by_state.keys()):
        stats = by_state[state]
        success_rate = (stats['ok'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"{state:4s}: {stats['ok']:3d} OK, {stats['warning']:3d} WARN, {stats['error']:3d} ERR / {stats['total']:3d} total ({success_rate:5.1f}% success)")
    
    print()
    print("=" * 100)
    
    # Save detailed results
    output_file = 'wms_validation_results_enhanced.txt'
    with open(output_file, 'w') as f:
        f.write("ENHANCED SERVICE VALIDATION RESULTS\n")
        f.write("=" * 100 + "\n\n")
        
        f.write(f"Total services: {len(filtered_services)} (filtered from {len(services)})\n")
        f.write(f"OK: {len(results['OK'])}\n")
        f.write(f"WARNING: {len(results['WARNING'])}\n")
        f.write(f"ERROR: {len(results['ERROR'])}\n")
        f.write(f"Layer mismatches: {len(layer_mismatches)}\n\n")
        
        if layer_mismatches:
            f.write("\n" + "=" * 100 + "\n")
            f.write("LAYER NAME MISMATCHES\n")
            f.write("=" * 100 + "\n\n")
            for r in layer_mismatches:
                f.write(f"{r['id']}\n")
                f.write(f"  State: {r['state']}\n")
                f.write(f"  Specified layer: {r['specified_layer']}\n")
                f.write(f"  Available layers ({len(r['layers'])}):\n")
                for layer in r['layers'][:20]:
                    f.write(f"    - {layer}\n")
                if len(r['layers']) > 20:
                    f.write(f"    ... and {len(r['layers']) - 20} more\n")
                f.write("\n")
        
        for status in ['ERROR', 'WARNING', 'OK']:
            f.write(f"\n{status} ({len(results[status])} services)\n")
            f.write("-" * 100 + "\n")
            for r in results[status]:
                f.write(f"\n{r['id']}\n")
                f.write(f"  State: {r['state']}\n")
                f.write(f"  URL: {r['url']}\n")
                if r.get('mode'):
                    f.write(f"  Mode: {r['mode']}\n")
                f.write(f"  Status: {r['message']}\n")
                if r['specified_layer']:
                    f.write(f"  Specified layer: {r['specified_layer']}\n")
                    f.write(f"  Layer found: {r['layer_found']}\n")
                f.write("\n")
    
    print(f"Detailed results saved to: {output_file}")
    print()


if __name__ == '__main__':
    main()

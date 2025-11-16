"""
Monitor catalog services for changes and updates.

Periodically checks:
- If services are still accessible
- If new layers have been added to known WMS endpoints
- If service metadata has changed (resolution, coverage, etc.)
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from owslib.wms import WebMapService

from orthophotos_downloader.wms_catalog.catalog_manager import WMSCatalogManager

logger = logging.getLogger(__name__)


class ServiceMonitor:
    """
    Monitor WMS services for changes and availability.
    
    Can detect:
    - Services that are down
    - New layers added to existing endpoints
    - Changes in service metadata
    - Potential new services
    """
    
    def __init__(self, catalog_path: Optional[Path] = None):
        """Initialize monitor with catalog."""
        self.catalog = WMSCatalogManager(catalog_path)
        self.results_path = Path(__file__).parent.parent.parent.parent / 'data' / 'monitoring'
        self.results_path.mkdir(parents=True, exist_ok=True)
    
    def check_service_health(self, service_id: str) -> Dict[str, Any]:
        """
        Check if a service is accessible and responding correctly.
        
        Returns:
            Dictionary with health check results
        """
        service = self.catalog.get_service_by_id(service_id)
        if not service:
            return {'status': 'not_found', 'service_id': service_id}
        
        try:
            wms = WebMapService(service.url, version=service.version, timeout=30)
            
            # Check if layer exists
            if service.layer_name in wms.contents:
                layer = wms.contents[service.layer_name]
                return {
                    'status': 'healthy',
                    'service_id': service_id,
                    'accessible': True,
                    'layer_found': True,
                    'title': getattr(layer, 'title', ''),
                    'checked_at': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'layer_not_found',
                    'service_id': service_id,
                    'accessible': True,
                    'layer_found': False,
                    'available_layers': list(wms.contents.keys())[:10],  # First 10
                    'checked_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'service_id': service_id,
                'accessible': False,
                'error': str(e),
                'checked_at': datetime.now().isoformat()
            }
    
    def check_all_services(self, max_services: Optional[int] = None) -> Dict[str, Any]:
        """
        Health check all services in catalog.
        
        Args:
            max_services: Limit number of services to check (for testing)
        
        Returns:
            Summary of health checks
        """
        all_services = self.catalog.get_all_services()
        if max_services:
            all_services = all_services[:max_services]
        
        results = {
            'healthy': [],
            'errors': [],
            'layer_not_found': [],
            'checked_at': datetime.now().isoformat(),
            'total_checked': len(all_services)
        }
        
        for i, service in enumerate(all_services, 1):
            logger.info(f"Checking {i}/{len(all_services)}: {service.id}")
            health = self.check_service_health(service.id)
            
            if health['status'] == 'healthy':
                results['healthy'].append(health)
            elif health['status'] == 'layer_not_found':
                results['layer_not_found'].append(health)
            else:
                results['errors'].append(health)
        
        # Save results
        results_file = self.results_path / f"health_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {results_file}")
        return results
    
    def discover_new_layers(self, wms_url: str) -> List[str]:
        """
        Discover all orthophoto layers at a WMS endpoint.
        
        Args:
            wms_url: WMS endpoint URL
        
        Returns:
            List of layer names that look like orthophotos
        """
        try:
            wms = WebMapService(wms_url, version='1.3.0', timeout=30)
            
            orthophoto_layers = []
            orthophoto_keywords = ['dop', 'orthophoto', 'luftbild', 'aerial', 'rgb', 'cir']
            
            for layer_name, layer in wms.contents.items():
                title = getattr(layer, 'title', '').lower()
                if any(kw in layer_name.lower() or kw in title for kw in orthophoto_keywords):
                    orthophoto_layers.append(layer_name)
            
            return orthophoto_layers
            
        except Exception as e:
            logger.error(f"Failed to discover layers from {wms_url}: {e}")
            return []
    
    def find_new_services(self) -> Dict[str, List[str]]:
        """
        Check all known WMS endpoints for new layers not in catalog.
        
        Returns:
            Dictionary mapping WMS URLs to new layer names
        """
        # Get unique WMS endpoints from catalog
        endpoints = set()
        for service in self.catalog.get_all_services():
            if service.has_wms():
                endpoints.add(service.wms_url)
        
        new_layers_by_endpoint = {}
        
        for url in endpoints:
            logger.info(f"Checking endpoint: {url}")
            
            # Get all layers from endpoint
            all_layers = self.discover_new_layers(url)
            
            # Get layers already in catalog for this endpoint
            catalog_layers = set()
            for service in self.catalog.get_all_services():
                if service.has_wms() and service.wms_url == url:
                    catalog_layers.add(service.wms_layer_name)
            
            # Find new layers
            new_layers = [layer for layer in all_layers if layer not in catalog_layers]
            
            if new_layers:
                new_layers_by_endpoint[url] = new_layers
                logger.info(f"Found {len(new_layers)} new layers at {url}")
        
        return new_layers_by_endpoint


def main():
    """CLI for service monitoring."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor WMS catalog services')
    parser.add_argument('action', choices=['health', 'discover'], 
                       help='Action to perform')
    parser.add_argument('--max-services', type=int, help='Limit services to check')
    parser.add_argument('--catalog', type=Path, help='Path to catalog file')
    
    args = parser.parse_args()
    
    monitor = ServiceMonitor(args.catalog)
    
    if args.action == 'health':
        print("🏥 Running health checks...")
        results = monitor.check_all_services(max_services=args.max_services)
        
        print(f"\n📊 Results:")
        print(f"  ✅ Healthy: {len(results['healthy'])}")
        print(f"  ⚠️  Layer not found: {len(results['layer_not_found'])}")
        print(f"  ❌ Errors: {len(results['errors'])}")
        
        if results['errors']:
            print("\n❌ Services with errors:")
            for err in results['errors'][:5]:
                print(f"  - {err['service_id']}: {err.get('error', 'Unknown error')}")
    
    elif args.action == 'discover':
        print("🔍 Discovering new layers...")
        new_layers = monitor.find_new_services()
        
        print(f"\n📊 Found new layers at {len(new_layers)} endpoints:")
        for url, layers in new_layers.items():
            print(f"\n{url}:")
            for layer in layers[:5]:
                print(f"  - {layer}")
            if len(layers) > 5:
                print(f"  ... and {len(layers) - 5} more")


if __name__ == '__main__':
    main()

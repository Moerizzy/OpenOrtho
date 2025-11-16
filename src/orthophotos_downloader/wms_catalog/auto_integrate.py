"""
Automatic WMS service integration into the catalog.

Provides tools to:
1. Auto-discover services from WMS GetCapabilities
2. Extract metadata from layer information
3. Validate and test new services
4. Add them to the catalog with proper formatting
"""

import logging
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse, parse_qs
from owslib.wms import WebMapService
from shapely.geometry import box, Polygon
import geopandas as gpd

from orthophotos_downloader.wms_catalog.catalog_manager import WMSCatalogManager, WMSService
from orthophotos_downloader.wms_catalog.service_discovery import ServiceDiscovery

logger = logging.getLogger(__name__)


class ServiceAutoIntegrator:
    """
    Automatically discover and integrate new WMS services into the catalog.
    
    This tool can:
    - Parse WMS GetCapabilities to discover layers
    - Extract metadata (year, type, resolution) from layer names/titles
    - Test services for actual coverage
    - Generate properly formatted catalog entries
    - Add new services to the catalog with validation
    """
    
    def __init__(self, catalog_path: Optional[Path] = None):
        """
        Initialize the auto-integrator.
        
        Args:
            catalog_path: Path to catalog YAML file
        """
        self.catalog = WMSCatalogManager(catalog_path)
        self.catalog_path = catalog_path or self.catalog.catalog_path
        self.discovery = ServiceDiscovery(catalog_path)
        
    def discover_from_wms(
        self,
        wms_url: str,
        state_code: str,
        state_name: str,
        test_bbox: Optional[Tuple[float, float, float, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Discover all orthophoto layers from a WMS GetCapabilities document.
        
        Args:
            wms_url: Base WMS URL
            state_code: 2-letter state code (e.g., 'BY', 'NW')
            state_name: Full state name (e.g., 'Bayern')
            test_bbox: Optional bbox to test coverage (minx, miny, maxx, maxy in EPSG:25832)
        
        Returns:
            List of discovered service configurations
        """
        logger.info(f"Discovering services from {wms_url}")
        
        try:
            # Get capabilities for different WMS versions
            discovered_services = []
            
            for version in ['1.3.0', '1.1.1', '1.1.0']:
                try:
                    wms = WebMapService(wms_url, version=version)
                    logger.info(f"Connected to WMS version {version}")
                    
                    # Find orthophoto layers
                    for layer_name, layer in wms.contents.items():
                        service_config = self._extract_service_info(
                            layer_name=layer_name,
                            layer=layer,
                            wms_url=wms_url,
                            wms_version=version,
                            state_code=state_code,
                            state_name=state_name
                        )
                        
                        if service_config:
                            # Test coverage if bbox provided
                            if test_bbox:
                                coverage = self._test_service_coverage(
                                    service_config, test_bbox
                                )
                                service_config['tested_coverage'] = coverage
                            
                            discovered_services.append(service_config)
                    
                    break  # Success, stop trying other versions
                    
                except Exception as e:
                    logger.debug(f"Failed with version {version}: {e}")
                    continue
            
            logger.info(f"Discovered {len(discovered_services)} potential services")
            return discovered_services
            
        except Exception as e:
            logger.error(f"Failed to discover services: {e}")
            return []
    
    def _extract_service_info(
        self,
        layer_name: str,
        layer: Any,
        wms_url: str,
        wms_version: str,
        state_code: str,
        state_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract service information from a WMS layer.
        
        Tries to identify:
        - Type (RGB/CIR)
        - Year
        - Resolution
        - Description
        """
        title = getattr(layer, 'title', layer_name)
        abstract = getattr(layer, 'abstract', '')
        
        # Skip non-orthophoto layers
        orthophoto_keywords = ['dop', 'orthophoto', 'luftbild', 'aerial']
        if not any(kw in layer_name.lower() or kw in title.lower() for kw in orthophoto_keywords):
            logger.debug(f"Skipping non-orthophoto layer: {layer_name}")
            return None
        
        # Extract metadata
        image_type = self._extract_image_type(layer_name, title)
        year = self._extract_year(layer_name, title, abstract)
        resolution = self._extract_resolution(layer_name, title, abstract)
        
        # Determine CRS
        crs_list = getattr(layer, 'crsOptions', [])
        crs = 'EPSG:25832' if 'EPSG:25832' in crs_list else (crs_list[0] if crs_list else 'EPSG:25832')
        
        # Generate service ID
        year_str = str(year).replace('-', '_') if year else 'unknown'
        service_id = f"{state_code}_{image_type}_DOP{int(resolution*100) if resolution else 20}_{year_str}"
        
        return {
            'id': service_id,
            'state_code': state_code,
            'state_name': state_name,
            'type': image_type,
            'resolution': resolution or 0.2,
            'year': year or 'latest',
            'url': wms_url,
            'version': wms_version,
            'layer_name': layer_name,
            'crs': crs,
            'format': 'image/png',
            'description': title or f"{state_name} {image_type} orthophotos",
            'availability': 'state-wide',
            'source': f"Auto-discovered from {urlparse(wms_url).netloc}",
            'temporal_coverage': str(year) if year and year != 'latest' else 'current',
        }
    
    def _extract_image_type(self, layer_name: str, title: str) -> str:
        """Extract RGB or CIR from layer name/title."""
        text = f"{layer_name} {title}".lower()
        if 'cir' in text or 'infrared' in text or 'rgbn' in text:
            return 'CIR'
        return 'RGB'
    
    def _extract_year(self, layer_name: str, title: str, abstract: str) -> Optional[str]:
        """Extract year or year range from metadata."""
        text = f"{layer_name} {title} {abstract}"
        
        # Look for year patterns
        patterns = [
            r'(\d{4})-(\d{4})',  # Range: 2019-2021
            r'(\d{4})',          # Single: 2020
            r'hist.*(\d{4})',    # Historic: hist_1951
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:
                    return f"{match.group(1)}-{match.group(2)}"
                else:
                    year = int(match.group(1))
                    if 1900 <= year <= 2030:  # Sanity check
                        return year
        
        # Check for "current" or "aktuelle"
        if any(kw in text.lower() for kw in ['current', 'aktuelle', 'latest']):
            return 'latest'
        
        return None
    
    def _extract_resolution(self, layer_name: str, title: str, abstract: str) -> Optional[float]:
        """Extract resolution from metadata."""
        text = f"{layer_name} {title} {abstract}".lower()
        
        # Look for DOP patterns
        dop_patterns = [
            (r'dop\s*10', 0.1),
            (r'dop\s*20', 0.2),
            (r'dop\s*40', 0.4),
            (r'dop10', 0.1),
            (r'dop20', 0.2),
            (r'dop40', 0.4),
        ]
        
        for pattern, resolution in dop_patterns:
            if re.search(pattern, text):
                return resolution
        
        # Look for explicit resolution in cm
        cm_match = re.search(r'(\d+)\s*cm', text)
        if cm_match:
            return float(cm_match.group(1)) / 100
        
        return None
    
    def _test_service_coverage(
        self,
        service_config: Dict[str, Any],
        test_bbox: Tuple[float, float, float, float]
    ) -> str:
        """
        Test if a service actually provides coverage for a test area.
        
        Returns:
            'high', 'medium', 'low', or 'none'
        """
        try:
            # Create temporary WMSService object
            temp_service = WMSService(**service_config)
            
            # Create test polygon
            test_polygon = box(*test_bbox)
            test_area = gpd.GeoSeries([test_polygon], crs="EPSG:25832")
            
            # Use existing coverage verification
            from orthophotos_downloader.wms_catalog.service_discovery import CoverageVerifier
            verifier = CoverageVerifier()
            
            result = verifier.verify_coverage_multipoint(
                service=temp_service,
                area_polygon=test_polygon,
                num_points=5
            )
            
            percentage = result['coverage_percentage']
            if percentage >= 60:
                return 'high'
            elif percentage >= 30:
                return 'medium'
            elif percentage > 0:
                return 'low'
            else:
                return 'none'
                
        except Exception as e:
            logger.warning(f"Coverage test failed: {e}")
            return 'unknown'
    
    def add_service_to_catalog(
        self,
        service_config: Dict[str, Any],
        validate: bool = True,
        test_bbox: Optional[Tuple[float, float, float, float]] = None
    ) -> bool:
        """
        Add a new service to the catalog.
        
        Args:
            service_config: Service configuration dictionary
            validate: Whether to validate the service before adding
            test_bbox: Optional bbox for coverage testing
        
        Returns:
            True if successfully added, False otherwise
        """
        if validate:
            # Check if service already exists
            existing = self.catalog.get_service_by_id(service_config['id'])
            if existing:
                logger.warning(f"Service {service_config['id']} already exists in catalog")
                return False
            
            # Test coverage if bbox provided
            if test_bbox:
                coverage = self._test_service_coverage(service_config, test_bbox)
                if coverage == 'none':
                    logger.warning(f"Service {service_config['id']} has no coverage in test area")
                    return False
                logger.info(f"Service {service_config['id']} coverage: {coverage}")
        
        # Load current catalog
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            catalog_data = yaml.safe_load(f)
        
        # Add new service
        catalog_data['services'].append(service_config)
        
        # Update last_updated
        from datetime import date
        catalog_data['last_updated'] = date.today().strftime('%Y-%m-%d')
        
        # Write back to file
        with open(self.catalog_path, 'w', encoding='utf-8') as f:
            yaml.dump(catalog_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        logger.info(f"✅ Added service {service_config['id']} to catalog")
        return True
    
    def batch_add_services(
        self,
        wms_url: str,
        state_code: str,
        state_name: str,
        test_bbox: Optional[Tuple[float, float, float, float]] = None,
        auto_add: bool = False,
        min_coverage: str = 'low'
    ) -> Dict[str, List[Dict]]:
        """
        Discover and optionally add multiple services from a WMS endpoint.
        
        Args:
            wms_url: WMS endpoint URL
            state_code: State code
            state_name: State name
            test_bbox: Optional test area
            auto_add: If True, automatically add services with sufficient coverage
            min_coverage: Minimum coverage level ('low', 'medium', 'high')
        
        Returns:
            Dictionary with 'discovered', 'added', and 'skipped' services
        """
        discovered = self.discover_from_wms(wms_url, state_code, state_name, test_bbox)
        
        result = {
            'discovered': discovered,
            'added': [],
            'skipped': []
        }
        
        if auto_add:
            coverage_levels = {'low': 0, 'medium': 1, 'high': 2}
            min_level = coverage_levels.get(min_coverage, 0)
            
            for service in discovered:
                coverage = service.get('tested_coverage', 'unknown')
                coverage_level = coverage_levels.get(coverage, -1)
                
                if coverage_level >= min_level:
                    if self.add_service_to_catalog(service, validate=False):
                        result['added'].append(service)
                    else:
                        result['skipped'].append(service)
                else:
                    logger.info(f"Skipping {service['id']} - coverage {coverage} below minimum {min_coverage}")
                    result['skipped'].append(service)
        
        return result


def main():
    """CLI interface for auto-integration."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Auto-discover and integrate WMS services')
    parser.add_argument('wms_url', help='WMS endpoint URL')
    parser.add_argument('state_code', help='State code (e.g., BY, NW)')
    parser.add_argument('state_name', help='State name (e.g., Bayern)')
    parser.add_argument('--test-bbox', nargs=4, type=float, metavar=('MINX', 'MINY', 'MAXX', 'MAXY'),
                       help='Test bbox in EPSG:25832')
    parser.add_argument('--auto-add', action='store_true', help='Automatically add services')
    parser.add_argument('--min-coverage', choices=['low', 'medium', 'high'], default='low',
                       help='Minimum coverage to auto-add')
    parser.add_argument('--catalog', type=Path, help='Path to catalog file')
    
    args = parser.parse_args()
    
    integrator = ServiceAutoIntegrator(args.catalog)
    
    result = integrator.batch_add_services(
        wms_url=args.wms_url,
        state_code=args.state_code,
        state_name=args.state_name,
        test_bbox=tuple(args.test_bbox) if args.test_bbox else None,
        auto_add=args.auto_add,
        min_coverage=args.min_coverage
    )
    
    print(f"\n📊 Discovery Results:")
    print(f"  Discovered: {len(result['discovered'])} services")
    print(f"  Added: {len(result['added'])} services")
    print(f"  Skipped: {len(result['skipped'])} services")
    
    print("\n🔍 Discovered Services:")
    for svc in result['discovered']:
        coverage = svc.get('tested_coverage', 'not tested')
        print(f"  - {svc['id']}: {svc['type']} {svc['year']} (coverage: {coverage})")


if __name__ == '__main__':
    main()

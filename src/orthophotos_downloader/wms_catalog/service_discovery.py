"""
WMS Service Discovery with Coverage Verification

Discovers available WMS services for a geographic area with optional
multi-point coverage verification for accurate results.

Integrates with AutoOrthophotoDownloader for efficient downloading.
"""

import logging
import requests
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
from shapely.geometry import Polygon, Point
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import json
import hashlib
from xml.etree import ElementTree as ET
from io import BytesIO

from orthophotos_downloader.wms_catalog.catalog_manager import WMSCatalogManager, WMSService

logger = logging.getLogger(__name__)


class ServiceCoverageCache:
    """
    Cache service coverage verification results.
    
    Stores results per service-area combination to avoid repeated verification.
    Cache expires after 7 days.
    """
    
    def __init__(self, cache_path: Optional[Path] = None):
        """
        Initialize coverage cache.
        
        Args:
            cache_path: Path to cache file. If None, uses ~/.openortho/coverage_cache.json
        """
        if cache_path is None:
            cache_dir = Path.home() / '.openortho'
            cache_dir.mkdir(exist_ok=True)
            cache_path = cache_dir / 'coverage_cache.json'
        
        self.cache_path = cache_path
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Load cache from disk."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                return {}
        return {}
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_path, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def _hash_area(self, area_polygon: Polygon) -> str:
        """Create hash of area for cache key (rounded to 1km)."""
        bounds = area_polygon.bounds
        # Round to 1km precision for cache sharing
        rounded = tuple(round(b, -3) for b in bounds)
        return hashlib.md5(str(rounded).encode()).hexdigest()[:8]
    
    def get_coverage(
        self, 
        service_id: str, 
        area_polygon: Polygon,
        layer_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached coverage result for service + area combination."""
        area_hash = self._hash_area(area_polygon)
        # Include layer_name in cache key so cache invalidates when layer names change
        if layer_name:
            cache_key = f"{service_id}_{layer_name}_{area_hash}"
        else:
            cache_key = f"{service_id}_{area_hash}"
        
        entry = self.cache.get(cache_key)
        if entry and not self._is_expired(entry):
            return entry['result']
        
        return None
    
    def set_coverage(
        self,
        service_id: str,
        area_polygon: Polygon,
        result: Dict[str, Any],
        layer_name: Optional[str] = None
    ):
        """Cache verification result."""
        area_hash = self._hash_area(area_polygon)
        # Include layer_name in cache key so cache invalidates when layer names change
        if layer_name:
            cache_key = f"{service_id}_{layer_name}_{area_hash}"
        else:
            cache_key = f"{service_id}_{area_hash}"
        
        self.cache[cache_key] = {
            'result': result,
            'cached_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=7)).isoformat()
        }
        self._save_cache()
    
    def _is_expired(self, entry: Dict) -> bool:
        """Check if cache entry is expired (7 days)."""
        try:
            expires = datetime.fromisoformat(entry['expires_at'])
            return datetime.now() > expires
        except:
            return True
    
    def clear_service(self, service_id: str):
        """Clear all cached entries for a service."""
        keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{service_id}_")]
        for key in keys_to_remove:
            del self.cache[key]
        self._save_cache()
    
    def clear_all(self):
        """Clear entire cache."""
        self.cache = {}
        self._save_cache()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.cache)
        expired = sum(1 for e in self.cache.values() if self._is_expired(e))
        
        return {
            'total_entries': total_entries,
            'expired_entries': expired,
            'active_entries': total_entries - expired,
            'cache_path': str(self.cache_path)
        }


class ServiceDiscovery:
    """
    Discover available WMS services for a geographic area.
    
    Provides two modes:
    - Fast: State-based filtering only (~0.1s)
    - Verified: Simple WMS availability test (~2-5s first time, cached afterwards)
    
    Verification is simple: if WMS returns valid imagery for the area center,
    the service is considered available. This is fast and reliable.
    """
    
    def __init__(
        self, 
        catalog_path: Optional[Path] = None,
        use_cache: bool = True
    ):
        """
        Initialize service discovery.
        
        Args:
            catalog_path: Path to custom catalog file. If None, uses default.
            use_cache: Whether to use coverage verification cache.
        """
        self.catalog = WMSCatalogManager(catalog_path)
        self.cache = ServiceCoverageCache() if use_cache else None
    
    def discover_services_for_area(
        self,
        area_polygon: Polygon,
        intersecting_states: List[Tuple[str, str, Polygon]],
        year_range: Optional[List[Union[str, int]]] = None,
        image_type: Optional[str] = 'RGB',
        resolution: Optional[float] = None,
        verify_coverage: bool = False,
        max_workers: int = 5
    ) -> Dict[str, Any]:
        """
        Discover available WMS services for a geographic area.
        
        Args:
            area_polygon: Area of interest (Shapely Polygon)
            intersecting_states: List of (state_name, state_code, intersection_geom) 
                                from AutoOrthophotoDownloader.detect_intersecting_states()
            year_range: Years to include (e.g., [2020, 2021, 2022] or ['latest'])
            image_type: 'RGB' or 'CIR'
            resolution: Filter by resolution (e.g., 0.2 for DOP20)
            verify_coverage: If True, verify WMS responds for the area (tests center point)
            max_workers: Number of parallel workers for verification
        
        Returns:
            Dictionary with discovered services and metadata:
            {
                'states': List of intersecting states,
                'candidate_services': All services from state filtering,
                'verified_services': Services after verification (if enabled),
                'recommended': Available services (same as verified_services),
                'by_year': Services organized by year,
                'verification': Verification details (if enabled),
                'summary': Statistics
            }
        """
        # Extract state codes
        state_codes = [code for _, code, _ in intersecting_states]
        
        logger.info(f"Discovering services for area intersecting states: {state_codes}")
        
        # Phase 1: Fast catalog filtering
        candidate_services = self.catalog.filter_services(
            state_code=state_codes,
            image_type=image_type,
            year=year_range,
            resolution=resolution
        )
        
        logger.info(f"Found {len(candidate_services)} candidate services from catalog")
        
        # Phase 2: Optional coverage verification
        verified_services = candidate_services
        verification_result = None
        
        if verify_coverage and candidate_services:
            logger.info(f"Verifying WMS availability for {len(candidate_services)} services...")
            
            verification_result = self._verify_services_with_cache(
                candidate_services,
                area_polygon,
                max_workers=max_workers
            )
            
            # Use available services
            verified_services = verification_result['recommended']
            
            logger.info(
                f"Verification complete: {len(verified_services)} available, "
                f"{len(verification_result['no_coverage'])} not available"
            )
        
        # Organize by year
        by_year = self._organize_by_year(verified_services)
        
        return {
            'states': intersecting_states,
            'candidate_services': candidate_services,
            'verified_services': verified_services,
            'recommended': verified_services,  # Same as verified in simple mode
            'partial_coverage': [],  # Not used in simple mode
            'by_year': by_year,
            'verification': verification_result,
            'summary': {
                'total_candidates': len(candidate_services),
                'verified_services': len(verified_services),
                'years_available': sorted(str(y) for y in by_year.keys()),
                'states_covered': state_codes,
                'verification_enabled': verify_coverage
            }
        }
    
    def _organize_by_year(self, services: List[WMSService]) -> Dict[str, List[WMSService]]:
        """Organize services by year."""
        by_year = {}
        for service in services:
            year = service.year or 'unknown'
            if year not in by_year:
                by_year[year] = []
            by_year[year].append(service)
        return by_year
    
    def _verify_services_with_cache(
        self,
        services: List[WMSService],
        area_polygon: Polygon,
        max_workers: int = 3
    ) -> Dict[str, Any]:
        """Verify services using cache when possible - simple available/not available."""
        
        available = []
        not_available = []
        errors = []
        
        # Separate cached and uncached services
        uncached_services = []
        cached_count = 0
        
        for service in services:
            if self.cache:
                cached_result = self.cache.get_coverage(service.id, area_polygon, service.layer_name)
                if cached_result:
                    # Use cached result
                    cached_count += 1
                    service._verification_result = cached_result
                    
                    if cached_result.get('has_coverage', False):
                        available.append(service)
                    else:
                        not_available.append(service)
                    continue
            
            uncached_services.append(service)
        
        logger.info(f"Using {cached_count} cached results, verifying {len(uncached_services)} services")
        
        # Verify uncached services in parallel
        if uncached_services:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_service = {
                    executor.submit(
                        self._verify_service_coverage,
                        service,
                        area_polygon
                    ): service
                    for service in uncached_services
                }
                
                for future in as_completed(future_to_service):
                    service = future_to_service[future]
                    
                    try:
                        result = future.result(timeout=10)
                        
                        # Store result
                        service._verification_result = result
                        
                        # Cache result with layer_name for automatic invalidation
                        if self.cache:
                            self.cache.set_coverage(service.id, area_polygon, result, service.layer_name)
                        
                        # Simple categorization: available or not
                        if result.get('has_coverage', False):
                            available.append(service)
                        else:
                            not_available.append(service)
                            
                    except Exception as e:
                        logger.warning(f"Error verifying {service.id}: {e}")
                        errors.append(service)
        
        return {
            'recommended': available,
            'partial_coverage': [],  # Not used in simple mode
            'no_coverage': not_available,
            'errors': errors,
            'cached_count': cached_count,
            'newly_verified': len(uncached_services),
            'statistics': {
                'total': len(services),
                'available': len(available),
                'not_available': len(not_available),
                'errors': len(errors)
            }
        }
    
    def _verify_service_coverage(
        self,
        service: WMSService,
        area_polygon: Polygon
    ) -> Dict[str, Any]:
        """
        Verify if service covers area using simple WMS test.
        
        Strategy:
        1. For file-only services (no WMS), automatically mark as available
        2. For WMS services, test 1 point in the center of the area
        3. If it has data, service is available
        4. Extract acquisition date if available
        5. Stop immediately if we find valid data
        
        This is fast and simple - if WMS works for the area, downloads will work.
        """
        # File-only services require feed/index verification
        if not service.has_wms() and service.has_files():
            return self._verify_file_service_coverage(service, area_polygon)
        
        # Test center point of area for WMS services
        centroid = area_polygon.centroid
        
        # Quick test with single point
        has_data = self._test_point_has_data(service, centroid, timeout=5)
        
        result = {
            'has_coverage': has_data,
            'coverage_ratio': 1.0 if has_data else 0.0,
            'coverage_category': 'full' if has_data else 'minimal',
            'tested_points': 1,
            'reason': 'WMS responds with valid imagery' if has_data else 'No valid imagery from WMS'
        }
        
        # If service has coverage, try to extract acquisition date
        if has_data:
            acquisition_date = self._extract_acquisition_date(service, centroid)
            if acquisition_date:
                result['acquisition_date'] = acquisition_date
        
        return result

    def _verify_file_service_coverage(
        self,
        service: WMSService,
        area_polygon: Polygon
    ) -> Dict[str, Any]:
        """
        Verify file-based services by checking their index (GeoJSON / Atom).
        """
        try:
            from orthophotos_downloader.data_scraping.file_downloader import FileServiceDownloader
        except Exception as exc:
            logger.warning(f"Unable to import FileServiceDownloader for {service.id}: {exc}")
            return {
                'has_coverage': False,
                'coverage_ratio': 0.0,
                'coverage_category': 'minimal',
                'tested_points': 0,
                'reason': 'File downloader unavailable for verification'
            }
        
        try:
            grid_spacing = int(service.files_grid_size or 1000)
        except Exception:
            grid_spacing = 1000
        
        try:
            downloader = FileServiceDownloader(
                service=service,
                grid_spacing=grid_spacing,
                extract_metadata=False,
                max_workers=1,
                verify_coverage=False
            )
            
            target_year = None
            if service.year and service.year not in ['latest', 'current']:
                year_str = str(service.year)
                if '-' not in year_str:
                    target_year = year_str
            
            tiles = []
            if service.files_index_type == 'geojson':
                tiles = downloader.get_tiles_from_geojson_index(
                    area_polygon=area_polygon,
                    target_year=target_year
                )
            elif service.files_index_type == 'atom':
                tiles = downloader.get_tiles_from_atom_feed(
                    area_polygon=area_polygon,
                    target_year=target_year
                )
            else:
                # For pattern-based downloads we cannot verify without data fetch
                logger.debug(
                    f"Service {service.id} uses unsupported index type "
                    f"{service.files_index_type} for coverage verification."
                )
            
            has_tiles = bool(tiles)
            result = {
                'has_coverage': has_tiles,
                'coverage_ratio': 1.0 if has_tiles else 0.0,
                'coverage_category': 'full' if has_tiles else 'minimal',
                'tested_points': len(tiles),
                'reason': (
                    'File index returns intersecting tiles'
                    if has_tiles else
                    'No intersecting tiles found in file index'
                )
            }
            
            if has_tiles and service.year and service.year not in ['latest', 'current']:
                result['acquisition_date'] = self._get_date_from_service_year(service)
            
            return result
        
        except Exception as exc:
            logger.warning(f"Failed to verify file service {service.id}: {exc}")
            return {
                'has_coverage': False,
                'coverage_ratio': 0.0,
                'coverage_category': 'minimal',
                'tested_points': 0,
                'reason': f'File index verification failed: {exc}'
            }
    
    def _generate_sample_grid(
        self,
        area_polygon: Polygon,
        grid_spacing: int = 2000,
        max_points: int = 15
    ) -> List[Point]:
        """Generate sample points within polygon using grid."""
        minx, miny, maxx, maxy = area_polygon.bounds
        
        sample_points = []
        x = minx
        while x <= maxx and len(sample_points) < max_points:
            y = miny
            while y <= maxy and len(sample_points) < max_points:
                point = Point(x, y)
                if area_polygon.contains(point):
                    sample_points.append(point)
                y += grid_spacing
            x += grid_spacing
        
        return sample_points
    
    def _test_points(
        self,
        service: WMSService,
        points: List[Point],
        timeout: int = 3
    ) -> int:
        """
        Test how many points have data.
        Returns count of points with valid imagery.
        """
        coverage_count = 0
        
        # Test points in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self._test_point_has_data, service, point, timeout): point
                for point in points
            }
            
            for future in as_completed(futures):
                try:
                    if future.result():
                        coverage_count += 1
                except Exception:
                    pass  # Count errors as no coverage
        
        return coverage_count
    
    def _test_point_has_data(
        self,
        service: WMSService,
        point: Point,
        timeout: int = 3
    ) -> bool:
        """Test if a point has imagery data via small GetMap request."""
        try:
            # Small bbox around point (100m x 100m)
            buffer = 50
            
            # Get WMS version - handle both old and new attribute names
            version = service.wms_version or service.version or '1.3.0'
            
            # WMS 1.3.0 with EPSG:25832 uses lat/lon order (y,x) not (x,y)!
            # But for most UTM CRS like EPSG:25832, the axis order is actually easting/northing (x,y)
            # Let's use the safer approach with owslib
            
            # Use wms_url or fall back to url
            wms_url = service.wms_url or service.url
            
            if not wms_url:
                logger.warning(f"No WMS URL for service {service.id}")
                return False
            
            # Build BBOX - for EPSG:25832, always use minx,miny,maxx,maxy
            bbox = f"{point.x - buffer},{point.y - buffer},{point.x + buffer},{point.y + buffer}"
            
            # WMS 1.1.1 uses SRS, WMS 1.3.0 uses CRS
            crs_param = 'CRS' if version.startswith('1.3') else 'SRS'
            crs_value = service.crs or 'EPSG:25832'
            
            params = {
                'SERVICE': 'WMS',
                'REQUEST': 'GetMap',
                'VERSION': version,
                'LAYERS': service.layer_name,
                'STYLES': '',
                'FORMAT': service.format or 'image/png',
                'WIDTH': 50,
                'HEIGHT': 50,
                crs_param: crs_value,
                'BBOX': bbox
            }
            
            response = requests.get(wms_url, params=params, timeout=timeout)
            
            if response.status_code != 200:
                return False
            
            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if 'image' not in content_type:
                return False
            
            # Check if image has variation (not blank)
            try:
                from PIL import Image
                img = Image.open(BytesIO(response.content))
                extrema = img.convert('L').getextrema()
                return (extrema[1] - extrema[0]) > 10  # Has contrast
            except:
                return True  # If we can't check, assume it's valid
                
        except Exception as e:
            logger.debug(f"GetMap test failed: {e}")
            return False
    
    def _get_date_from_service_year(self, service: WMSService) -> Optional[str]:
        """
        Extract acquisition date from service year field.
        
        Args:
            service: WMS service
            
        Returns:
            ISO date string (YYYY-MM-DD) or None if not available
        """
        if not service.year:
            return None
        
        year_str = str(service.year)
        
        # Handle year ranges like '2012-2025' -> use first year
        if '-' in year_str:
            year_str = year_str.split('-')[0]
        
        # Skip 'latest', 'current', etc.
        if not year_str.isdigit():
            return None
        
        try:
            year = int(year_str)
            # Return January 1st of that year
            return f"{year:04d}-01-01"
        except (ValueError, TypeError):
            return None
    
    def _extract_acquisition_date(
        self, 
        service: WMSService, 
        point: Point
    ) -> Optional[str]:
        """
        Extract acquisition date from WMS metadata or service configuration.
        
        Args:
            service: WMS service
            point: Point to query for metadata
            
        Returns:
            ISO date string (YYYY-MM-DD) or None if not available
        """
        # Try metadata layer first (most accurate)
        if service.metadata and service.metadata.get('metadata_layer'):
            date = self._query_metadata_date(service, point)
            if date:
                # Validate that metadata date matches service year
                # (NRW metadata may return dates for different years than requested)
                try:
                    metadata_year = date.split('-')[0]
                    service_year = str(service.year)
                    
                    # For non-numeric service years (latest, current, year ranges), accept metadata date as-is
                    if not service_year.isdigit():
                        return date
                    
                    if metadata_year == service_year:
                        return date
                    else:
                        # Metadata returned a different year - likely no coverage for this specific year
                        # Fall back to year-based date
                        logger.debug(f"Metadata year {metadata_year} doesn't match service year {service_year}, using fallback")
                except (ValueError, IndexError):
                    # If we can't parse the year, use the metadata date anyway
                    return date
        
        # Fallback to service year
        return self._get_date_from_service_year(service)
    
    def _query_metadata_date(
        self, 
        service: WMSService, 
        point: Point
    ) -> Optional[str]:
        """
        Query WMS GetFeatureInfo for acquisition date.
        
        Args:
            service: WMS service with metadata configuration
            point: Point to query
            
        Returns:
            ISO date string (YYYY-MM-DD) or None if not available
        """
        try:
            from orthophotos_downloader.metadata.metadata_extractor import TileMetadataExtractor
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
            
            # Create metadata extractor
            extractor = TileMetadataExtractor(
                wms_url=service.wms_url,
                state_code=service.state_code,
                wms_service=service
            )
            
            # Query WMS for metadata with thread-safe timeout
            # Use ThreadPoolExecutor for timeout since signal.alarm() doesn't work in threads
            def query_metadata():
                return extractor._query_wms_metadata(
                    center_x=point.x,
                    center_y=point.y,
                    crs=service.crs or 'EPSG:25832'
                )
            
            try:
                # Execute with timeout using ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(query_metadata)
                    metadata = future.result(timeout=10)  # 10 second timeout
                
                # Extract acquisition date from metadata
                if metadata and 'acquisition_date' in metadata:
                    return metadata['acquisition_date']
            
            except FuturesTimeoutError:
                logger.debug(f"Metadata query timed out for {service.id}")
                return None
            except Exception as e:
                logger.debug(f"Metadata query error for {service.id}: {e}")
                return None
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to query metadata date: {e}")
            return None
    
    def _categorize_coverage(self, ratio: float) -> str:
        """Categorize coverage ratio."""
        if ratio >= 0.9:
            return 'full'
        elif ratio >= 0.6:
            return 'high'
        elif ratio >= 0.3:
            return 'partial'
        else:
            return 'minimal'
    
    def get_available_years(
        self,
        area_polygon: Polygon,
        intersecting_states: List[Tuple[str, str, Polygon]],
        image_type: str = 'RGB'
    ) -> List[str]:
        """Get list of available years for an area."""
        result = self.discover_services_for_area(
            area_polygon,
            intersecting_states,
            image_type=image_type,
            verify_coverage=False  # Fast, no verification needed
        )
        return result['summary']['years_available']

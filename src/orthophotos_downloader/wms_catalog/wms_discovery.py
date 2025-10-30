"""
WMS Discovery System

Discovers available WMS services for a given geographic area and provides
filtering capabilities based on temporal, spectral, and spatial requirements.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from shapely.geometry import Polygon, box
import geopandas as gpd

from orthophotos_downloader.wms_catalog.catalog_manager import WMSCatalogManager, WMSService

logger = logging.getLogger(__name__)


class WMSDiscovery:
    """
    Discover and query available WMS services for orthophoto downloads.
    
    This class helps users:
    - Find which WMS services cover their area of interest
    - Filter by temporal criteria (year, date range)
    - Filter by spectral criteria (RGB, CIR)
    - Filter by spatial resolution
    - Get information about available options before downloading
    """
    
    # German state boundaries in EPSG:25832 (simplified bounding boxes)
    # These are approximate - for precise queries, use actual state boundaries
    STATE_BOUNDS = {
        'BW': (4461000, 5250000, 4641000, 5533000),  # Baden-Württemberg
        'BY': (4318000, 5227000, 4715000, 5605000),  # Bayern
        'BE': (4575000, 5808000, 4621000, 5844000),  # Berlin
        'BB': (4478000, 5700000, 4668000, 5945000),  # Brandenburg
        'HB': (4447000, 5867000, 4472000, 5892000),  # Bremen
        'HH': (4547000, 5919000, 4593000, 5954000),  # Hamburg
        'HE': (4472000, 5516000, 4617000, 5693000),  # Hessen
        'MV': (4478000, 5916000, 4741000, 6079000),  # Mecklenburg-Vorpommern
        'NI': (4285000, 5726000, 4627000, 5994000),  # Niedersachsen
        'NW': (4249000, 5605000, 4484000, 5755000),  # Nordrhein-Westfalen
        'RP': (4380000, 5458000, 4526000, 5633000),  # Rheinland-Pfalz
        'SL': (4380000, 5429000, 4447000, 5494000),  # Saarland
        'SN': (4561000, 5574000, 4738000, 5703000),  # Sachsen
        'ST': (4440000, 5645000, 4641000, 5803000),  # Sachsen-Anhalt
        'SH': (4472000, 5944000, 4627000, 6101000),  # Schleswig-Holstein
        'TH': (4500000, 5573000, 4641000, 5708000),  # Thüringen
    }
    
    def __init__(self, catalog_path: Optional[Path] = None):
        """
        Initialize WMS discovery.
        
        Args:
            catalog_path: Path to custom catalog file. If None, uses default.
        """
        self.catalog = WMSCatalogManager(catalog_path)
        
    def discover_for_area(
        self,
        area: Optional[Polygon] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        state_code: Optional[str] = None,
        crs: str = "EPSG:25832"
    ) -> List[str]:
        """
        Discover which states a geographic area covers.
        
        Args:
            area: Polygon geometry of area of interest
            bbox: Bounding box as (minx, miny, maxx, maxy)
            state_code: If provided, directly returns this state
            crs: Coordinate reference system of input geometry
            
        Returns:
            List of state codes that intersect with the area
        """
        if state_code:
            return [state_code]
        
        if area is None and bbox is None:
            logger.warning("No area specified. Use state_code, area, or bbox.")
            return []
        
        # Convert bbox to polygon if provided
        if bbox and area is None:
            area = box(*bbox)
        
        # For now, use simple bounding box intersection
        # TODO: Use actual state boundary geometries for precise determination
        intersecting_states = []
        area_bounds = area.bounds  # (minx, miny, maxx, maxy)
        
        for state, state_bounds in self.STATE_BOUNDS.items():
            # Check if bounding boxes intersect
            if self._boxes_intersect(area_bounds, state_bounds):
                intersecting_states.append(state)
        
        return intersecting_states
    
    def _boxes_intersect(self, box1: Tuple, box2: Tuple) -> bool:
        """Check if two bounding boxes intersect."""
        minx1, miny1, maxx1, maxy1 = box1
        minx2, miny2, maxx2, maxy2 = box2
        
        return not (maxx1 < minx2 or maxx2 < minx1 or 
                   maxy1 < miny2 or maxy2 < miny1)
    
    def get_available_services(
        self,
        area: Optional[Polygon] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        state_code: Optional[str] = None,
        image_type: Optional[str] = None,
        resolution: Optional[float] = None,
        year: Optional[str] = None,
        requires_auth: bool = False,
        crs: str = "EPSG:25832"
    ) -> List[WMSService]:
        """
        Get all available WMS services for an area with optional filters.
        
        Args:
            area: Polygon geometry of area of interest
            bbox: Bounding box as (minx, miny, maxx, maxy)
            state_code: Specific state code to query
            image_type: Filter by image type ('RGB', 'CIR')
            resolution: Filter by resolution (e.g., 0.2 for DOP20)
            year: Filter by year ('latest', 2023, etc.)
            requires_auth: If False, exclude services requiring authentication
            crs: Coordinate reference system
            
        Returns:
            List of WMSService objects matching criteria
        """
        # First, determine which states are relevant
        states = self.discover_for_area(area, bbox, state_code, crs)
        
        if not states:
            logger.warning("No states found for the specified area")
            return []
        
        # Filter services
        services = self.catalog.filter_services(
            state_code=states,
            image_type=image_type,
            resolution=resolution,
            year=year,
            requires_auth=requires_auth if not requires_auth else None
        )
        
        return services
    
    def get_temporal_options(
        self,
        state_code: str,
        image_type: Optional[str] = None,
        resolution: Optional[float] = None
    ) -> Dict[str, List[WMSService]]:
        """
        Get available temporal options (years) for a state.
        
        Args:
            state_code: Two-letter state code
            image_type: Filter by image type
            resolution: Filter by resolution
            
        Returns:
            Dictionary mapping years to lists of WMSService objects
        """
        services = self.catalog.filter_services(
            state_code=state_code,
            image_type=image_type,
            resolution=resolution
        )
        
        # Group by year
        temporal_options = {}
        for service in services:
            year = str(service.year)
            if year not in temporal_options:
                temporal_options[year] = []
            temporal_options[year].append(service)
        
        return temporal_options
    
    def get_spectral_options(
        self,
        state_code: str,
        year: Optional[str] = None,
        resolution: Optional[float] = None
    ) -> Dict[str, List[WMSService]]:
        """
        Get available spectral options (RGB, CIR) for a state.
        
        Args:
            state_code: Two-letter state code
            year: Filter by year
            resolution: Filter by resolution
            
        Returns:
            Dictionary mapping image types to lists of WMSService objects
        """
        services = self.catalog.filter_services(
            state_code=state_code,
            year=year,
            resolution=resolution
        )
        
        # Group by image type
        spectral_options = {}
        for service in services:
            img_type = service.type
            if img_type not in spectral_options:
                spectral_options[img_type] = []
            spectral_options[img_type].append(service)
        
        return spectral_options
    
    def get_resolution_options(
        self,
        state_code: str,
        image_type: Optional[str] = None,
        year: Optional[str] = None
    ) -> Dict[float, List[WMSService]]:
        """
        Get available resolution options for a state.
        
        Args:
            state_code: Two-letter state code
            image_type: Filter by image type
            year: Filter by year
            
        Returns:
            Dictionary mapping resolutions to lists of WMSService objects
        """
        services = self.catalog.filter_services(
            state_code=state_code,
            image_type=image_type,
            year=year
        )
        
        # Group by resolution
        resolution_options = {}
        for service in services:
            res = service.resolution
            if res not in resolution_options:
                resolution_options[res] = []
            resolution_options[res].append(service)
        
        return resolution_options
    
    def print_discovery_summary(
        self,
        area: Optional[Polygon] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        state_code: Optional[str] = None,
        crs: str = "EPSG:25832"
    ):
        """
        Print a summary of available services for an area.
        
        Args:
            area: Polygon geometry of area of interest
            bbox: Bounding box as (minx, miny, maxx, maxy)
            state_code: Specific state code
            crs: Coordinate reference system
        """
        states = self.discover_for_area(area, bbox, state_code, crs)
        
        print(f"\n{'=' * 80}")
        print(f"WMS Discovery Summary")
        print(f"{'=' * 80}")
        
        if bbox:
            print(f"Area (bbox): {bbox}")
        if state_code:
            print(f"State: {state_code}")
        
        print(f"\nStates covered: {len(states)}")
        print(f"States: {', '.join(states)}")
        
        print(f"\n{'=' * 80}")
        
        for state in states:
            print(f"\n{state} - Available Services:")
            print(f"{'-' * 80}")
            
            services = self.catalog.filter_services(state_code=state)
            
            # Group by image type
            rgb = [s for s in services if s.type == 'RGB']
            cir = [s for s in services if s.type == 'CIR']
            
            print(f"  RGB: {len(rgb)} service(s)")
            for s in rgb:
                print(f"    • {s.description}")
                print(f"      Year: {s.year}, Resolution: {s.resolution}m, Direct: {s.direct_download}")
            
            if cir:
                print(f"  CIR: {len(cir)} service(s)")
                for s in cir:
                    print(f"    • {s.description}")
                    print(f"      Year: {s.year}, Resolution: {s.resolution}m, Direct: {s.direct_download}")
            else:
                print(f"  CIR: Not available")
        
        print(f"\n{'=' * 80}\n")
    
    def recommend_service(
        self,
        area: Optional[Polygon] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        state_code: Optional[str] = None,
        image_type: str = 'RGB',
        prefer_latest: bool = True,
        prefer_high_res: bool = True,
        prefer_direct: bool = True,
        crs: str = "EPSG:25832"
    ) -> Optional[WMSService]:
        """
        Recommend the best service for given requirements.
        
        Args:
            area: Polygon geometry of area of interest
            bbox: Bounding box
            state_code: Specific state code
            image_type: Preferred image type
            prefer_latest: Prefer latest/current imagery
            prefer_high_res: Prefer higher resolution
            prefer_direct: Prefer services with direct download
            crs: Coordinate reference system
            
        Returns:
            Recommended WMSService or None
        """
        services = self.get_available_services(
            area=area,
            bbox=bbox,
            state_code=state_code,
            image_type=image_type,
            requires_auth=False,
            crs=crs
        )
        
        if not services:
            return None
        
        # Score services based on preferences
        scored = []
        for service in services:
            score = 0
            
            # Temporal preference
            if prefer_latest and str(service.year).lower() == 'latest':
                score += 10
            
            # Resolution preference (higher resolution = higher score)
            if prefer_high_res:
                # Inverse of resolution (0.2m gets higher score than 0.4m)
                score += (1.0 / service.resolution) * 5
            
            # Direct download preference
            if prefer_direct and service.direct_download:
                score += 10
            
            scored.append((score, service))
        
        # Return service with highest score
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create discovery instance
    discovery = WMSDiscovery()
    
    # Example 1: Discover services for Bayern
    print("\n" + "=" * 80)
    print("Example 1: Discover services for Bayern")
    print("=" * 80)
    discovery.print_discovery_summary(state_code='BY')
    
    # Example 2: Find services for a specific bbox (Munich area)
    print("\n" + "=" * 80)
    print("Example 2: Find services for Munich area")
    print("=" * 80)
    bbox = (4476000, 5327000, 4496000, 5347000)
    services = discovery.get_available_services(bbox=bbox, image_type='RGB')
    print(f"Found {len(services)} RGB services:")
    for s in services:
        print(f"  • {s}")
    
    # Example 3: Get temporal options
    print("\n" + "=" * 80)
    print("Example 3: Temporal options for Bayern RGB")
    print("=" * 80)
    temporal = discovery.get_temporal_options('BY', image_type='RGB')
    for year, services in temporal.items():
        print(f"Year {year}: {len(services)} service(s)")
        for s in services:
            print(f"  • {s}")
    
    # Example 4: Recommend a service
    print("\n" + "=" * 80)
    print("Example 4: Recommend best service for Munich")
    print("=" * 80)
    recommended = discovery.recommend_service(
        bbox=bbox,
        image_type='RGB',
        prefer_latest=True,
        prefer_high_res=True,
        prefer_direct=True
    )
    if recommended:
        print(f"Recommended: {recommended}")
        print(f"  ID: {recommended.id}")
        print(f"  URL: {recommended.url}")
        print(f"  Resolution: {recommended.resolution}m")
        print(f"  Direct download: {recommended.direct_download}")

"""
WMS Catalog Manager

Manages the catalog of WMS services, providing query and filter capabilities.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import yaml

logger = logging.getLogger(__name__)


class WMSService:
    """
    Represents a single WMS service entry from the catalog.
    
    Attributes:
        id: Unique identifier
        state_code: Two-letter state code
        state_name: Full state name
        type: Image type (RGB, CIR, etc.)
        resolution: Resolution in meters
        year: Year or 'latest'
        temporal_coverage: Time period covered
        url: WMS service URL
        version: WMS version
        layer_name: Layer name
        crs: Coordinate reference system
        format: Image format
        availability: Coverage description
        description: Human-readable description
        direct_download: Whether direct tile downloads are available
        tile_url_pattern: URL pattern for direct downloads
        source: Source organization
        requires_auth: Whether authentication is required
        auth_type: Type of authentication required
        metadata: Metadata service configuration (dict with service URL, layer, etc.)
    """
    
    def __init__(self, **kwargs):
        """Initialize WMS service from catalog entry."""
        self.id = kwargs.get('id')
        self.state_code = kwargs.get('state_code')
        self.state_name = kwargs.get('state_name')
        self.type = kwargs.get('type')
        self.resolution = float(kwargs.get('resolution', 0))
        self.year = kwargs.get('year')
        self.temporal_coverage = kwargs.get('temporal_coverage')
        self.url = kwargs.get('url')
        self.version = kwargs.get('version')
        self.layer_name = kwargs.get('layer_name')
        self.crs = kwargs.get('crs')
        self.format = kwargs.get('format')
        self.availability = kwargs.get('availability')
        self.description = kwargs.get('description')
        self.direct_download = kwargs.get('direct_download', False)
        self.tile_url_pattern = kwargs.get('tile_url_pattern')
        self.source = kwargs.get('source')
        self.requires_auth = kwargs.get('requires_auth', False)
        self.auth_type = kwargs.get('auth_type')
        # Metadata configuration (for metadata extraction)
        self.metadata = kwargs.get('metadata', {})
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    def __repr__(self) -> str:
        return f"WMSService(id='{self.id}', state='{self.state_code}', type='{self.type}', year='{self.year}')"
    
    def __str__(self) -> str:
        return f"{self.state_name} {self.type} DOP{int(self.resolution*100)} ({self.year})"


class WMSCatalogManager:
    """
    Manager for the WMS service catalog.
    
    Provides methods to:
    - Load catalog from YAML file
    - Query services by various criteria
    - Filter services
    - Get service details
    """
    
    DEFAULT_CATALOG_PATH = Path(__file__).parent / 'wms_services.yaml'
    
    def __init__(self, catalog_path: Optional[Path] = None):
        """
        Initialize the catalog manager.
        
        Args:
            catalog_path: Path to catalog YAML file. If None, uses default.
        """
        self.catalog_path = catalog_path or self.DEFAULT_CATALOG_PATH
        self.services: List[WMSService] = []
        self.catalog_metadata: Dict[str, Any] = {}
        self._load_catalog()
        
    def _load_catalog(self):
        """Load catalog from YAML file."""
        if not self.catalog_path.exists():
            logger.error(f"Catalog file not found: {self.catalog_path}")
            raise FileNotFoundError(f"Catalog file not found: {self.catalog_path}")
        
        try:
            with open(self.catalog_path, 'r') as f:
                data = yaml.safe_load(f)
            
            self.catalog_metadata = {
                'version': data.get('version'),
                'last_updated': data.get('last_updated'),
            }
            
            services_data = data.get('services', [])
            self.services = [WMSService(**service) for service in services_data]
            
            logger.info(f"Loaded {len(self.services)} WMS services from catalog")
            
        except Exception as e:
            logger.error(f"Error loading catalog: {e}")
            raise
    
    def get_all_services(self) -> List[WMSService]:
        """Get all services in the catalog."""
        return self.services
    
    def get_service_by_id(self, service_id: str) -> Optional[WMSService]:
        """
        Get a specific service by its ID.
        
        Args:
            service_id: Service identifier
            
        Returns:
            WMSService object or None if not found
        """
        for service in self.services:
            if service.id == service_id:
                return service
        return None
    
    def filter_services(
        self,
        state_code: Optional[Union[str, List[str]]] = None,
        image_type: Optional[Union[str, List[str]]] = None,
        resolution: Optional[Union[float, List[float]]] = None,
        year: Optional[Union[str, int, List[Union[str, int]]]] = None,
        requires_auth: Optional[bool] = None,
        direct_download: Optional[bool] = None,
    ) -> List[WMSService]:
        """
        Filter services by various criteria.
        
        Args:
            state_code: State code(s) to filter by (e.g., 'BY', ['BY', 'BW'])
            image_type: Image type(s) to filter by (e.g., 'RGB', ['RGB', 'CIR'])
            resolution: Resolution(s) to filter by (e.g., 0.2, [0.2, 0.4])
            year: Year(s) to filter by (e.g., 2023, 'latest', [2023, 2022])
            requires_auth: Filter by authentication requirement
            direct_download: Filter by direct download availability
            
        Returns:
            List of matching WMSService objects
        """
        filtered = self.services
        
        # Convert single values to lists for uniform filtering
        if state_code is not None and not isinstance(state_code, list):
            state_code = [state_code]
        if image_type is not None and not isinstance(image_type, list):
            image_type = [image_type]
        if resolution is not None and not isinstance(resolution, list):
            resolution = [resolution]
        if year is not None and not isinstance(year, list):
            year = [year]
        
        # Apply filters
        if state_code:
            filtered = [s for s in filtered if s.state_code in state_code]
        
        if image_type:
            # Case-insensitive comparison
            image_type_upper = [t.upper() for t in image_type]
            filtered = [s for s in filtered if s.type.upper() in image_type_upper]
        
        if resolution:
            filtered = [s for s in filtered if s.resolution in resolution]
        
        if year:
            # Convert years to strings for comparison (handles 'latest' and numeric years)
            year_str = [str(y) for y in year]
            filtered = [s for s in filtered if str(s.year) in year_str]
        
        if requires_auth is not None:
            filtered = [s for s in filtered if s.requires_auth == requires_auth]
        
        if direct_download is not None:
            filtered = [s for s in filtered if s.direct_download == direct_download]
        
        return filtered
    
    def get_states(self) -> List[str]:
        """
        Get list of all unique state codes in catalog.
        
        Returns:
            List of state codes
        """
        return sorted(list(set(s.state_code for s in self.services)))
    
    def get_years_for_state(self, state_code: str) -> List[str]:
        """
        Get available years for a specific state.
        
        Args:
            state_code: Two-letter state code
            
        Returns:
            List of available years (as strings)
        """
        services = self.filter_services(state_code=state_code)
        years = sorted(list(set(str(s.year) for s in services)))
        return years
    
    def get_image_types_for_state(self, state_code: str) -> List[str]:
        """
        Get available image types for a specific state.
        
        Args:
            state_code: Two-letter state code
            
        Returns:
            List of image types (e.g., ['RGB', 'CIR'])
        """
        services = self.filter_services(state_code=state_code)
        types = sorted(list(set(s.type for s in services)))
        return types
    
    def get_resolutions_for_state(self, state_code: str) -> List[float]:
        """
        Get available resolutions for a specific state.
        
        Args:
            state_code: Two-letter state code
            
        Returns:
            List of resolutions in meters
        """
        services = self.filter_services(state_code=state_code)
        resolutions = sorted(list(set(s.resolution for s in services)))
        return resolutions
    
    def print_summary(self):
        """Print a summary of the catalog."""
        print(f"\n{'=' * 80}")
        print(f"WMS Catalog Summary")
        print(f"{'=' * 80}")
        print(f"Catalog version: {self.catalog_metadata.get('version')}")
        print(f"Last updated: {self.catalog_metadata.get('last_updated')}")
        print(f"Total services: {len(self.services)}")
        print(f"\nStates covered: {len(self.get_states())}")
        print(f"States: {', '.join(self.get_states())}")
        
        # Count by type
        rgb_count = len(self.filter_services(image_type='RGB'))
        cir_count = len(self.filter_services(image_type='CIR'))
        print(f"\nImage types:")
        print(f"  RGB: {rgb_count}")
        print(f"  CIR: {cir_count}")
        
        # Count by resolution
        resolutions = {}
        for service in self.services:
            res = service.resolution
            resolutions[res] = resolutions.get(res, 0) + 1
        
        print(f"\nResolutions:")
        for res in sorted(resolutions.keys()):
            print(f"  {res}m (DOP{int(res*100)}): {resolutions[res]} services")
        
        # Direct download
        direct_count = len(self.filter_services(direct_download=True))
        print(f"\nDirect download available: {direct_count} services")
        
        # Authentication required
        auth_count = len(self.filter_services(requires_auth=True))
        print(f"Authentication required: {auth_count} services")
        
        print(f"{'=' * 80}\n")
    
    def print_services_table(self, services: Optional[List[WMSService]] = None):
        """
        Print services in a formatted table.
        
        Args:
            services: List of services to print. If None, prints all.
        """
        if services is None:
            services = self.services
        
        if not services:
            print("No services found.")
            return
        
        print(f"\n{'=' * 120}")
        print(f"{'ID':<35} {'State':<8} {'Type':<6} {'Res':<6} {'Year':<8} {'Description':<50}")
        print(f"{'=' * 120}")
        
        for service in services:
            res_str = f"{service.resolution}m"
            year_str = str(service.year)
            desc = service.description[:47] + '...' if len(service.description) > 50 else service.description
            
            print(f"{service.id:<35} {service.state_code:<8} {service.type:<6} {res_str:<6} {year_str:<8} {desc:<50}")
        
        print(f"{'=' * 120}\n")
        print(f"Total: {len(services)} services\n")


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create catalog manager
    catalog = WMSCatalogManager()
    
    # Print summary
    catalog.print_summary()
    
    # Get all Bayern services
    print("\n--- Bayern (BY) Services ---")
    by_services = catalog.filter_services(state_code='BY')
    catalog.print_services_table(by_services)
    
    # Get all RGB services
    print("\n--- RGB Services (all states) ---")
    rgb_services = catalog.filter_services(image_type='RGB')
    print(f"Found {len(rgb_services)} RGB services")
    
    # Get services with direct download
    print("\n--- Services with Direct Download ---")
    direct_services = catalog.filter_services(direct_download=True)
    catalog.print_services_table(direct_services)
    
    # Get specific service
    print("\n--- Specific Service ---")
    service = catalog.get_service_by_id('BY_RGB_DOP20_current')
    if service:
        print(f"Service: {service}")
        print(f"URL: {service.url}")
        print(f"Layer: {service.layer_name}")

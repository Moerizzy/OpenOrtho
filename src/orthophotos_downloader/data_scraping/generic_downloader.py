"""
Generic WMS Service Downloader

A unified downloader that works with any WMS service from the catalog,
eliminating the need for state-specific downloader classes.
"""

from orthophotos_downloader.data_scraping.image_download import (
    ImageDownloader,
    ExtendedWebMapService,
)
from orthophotos_downloader.wms_catalog.catalog_manager import WMSService


class WMSServiceDownloader(ImageDownloader):
    """
    Generic downloader that works with any WMS service from the catalog.
    
    Instead of having separate classes for each state/type/resolution combination,
    this class dynamically configures itself based on a WMSService object.
    
    Example:
        >>> from orthophotos_downloader.wms_catalog import WMSCatalogManager
        >>> catalog = WMSCatalogManager()
        >>> service = catalog.get_service_by_id('BY_RGB_DOP20_current')
        >>> downloader = WMSServiceDownloader(
        ...     service=service,
        ...     grid_spacing=1000,
        ...     extract_metadata=True
        ... )
        >>> downloader.download_images_auto(area_polygon)
    """
    
    def __init__(
        self,
        service: WMSService,
        grid_spacing: int,
        extract_metadata: bool = True,
        layer_name_override: str = None,
        max_workers: int = 4
    ):
        """
        Initialize the generic WMS service downloader.
        
        Args:
            service: WMSService object from the catalog
            grid_spacing: The grid spacing in meters for the image download
            extract_metadata: Whether to extract metadata and create STAC items
            layer_name_override: Optional layer name to override the service's default
                                 (useful for historic orthophotos with different layer names)
            max_workers: Maximum number of parallel download threads (default: 4)
        """
        # Use override layer name if provided, otherwise use service's layer name
        layer_name = layer_name_override if layer_name_override else service.layer_name
        
        # Create WMS configuration from catalog service
        wms = ExtendedWebMapService(
            url=service.url,
            version=service.version,
            resolution=service.resolution,
            layer_name=layer_name,
            crs=service.crs,
            format=service.format,
        )
        
        # Initialize parent ImageDownloader with WMS config
        super().__init__(
            wms=wms,
            grid_spacing=grid_spacing,
            state_code=service.state_code,
            extract_metadata=extract_metadata,
            max_workers=max_workers
        )
        
        # Store reference to service for metadata/logging
        self.service = service

"""
Integration module to add metadata extraction to existing downloader.

This module provides a wrapper around the ImageDownloader class that automatically
extracts and saves metadata for each downloaded tile.
"""

import logging
from pathlib import Path
from typing import Optional

from geopandas import GeoSeries
from shapely.geometry import Polygon

from orthophotos_downloader.data_scraping.image_download import (
    ImageDownloader,
    ExtendedWebMapService,
    Image,
)
from orthophotos_downloader.metadata.metadata_extractor import TileMetadataExtractor


logger = logging.getLogger(__name__)


class ImageDownloaderWithMetadata(ImageDownloader):
    """
    Extended ImageDownloader that automatically extracts metadata for each tile.
    
    This class wraps the standard ImageDownloader and adds automatic metadata
    extraction for resolution, acquisition date, and quality information.
    """
    
    def __init__(self, wms: ExtendedWebMapService, grid_spacing: int, state_code: str):
        """
        Initialize downloader with metadata extraction.
        
        Args:
            wms: Extended Web Map Service instance
            grid_spacing: Grid spacing in meters
            state_code: Two-letter state code (e.g., 'BY', 'NW')
        """
        super().__init__(wms=wms, grid_spacing=grid_spacing)
        self.state_code = state_code
        self.metadata_extractor = TileMetadataExtractor(wms.wms.url, state_code)
        
    @staticmethod
    def _download_tile(
        img_path: Path,
        bounding_box: Polygon,
        wms: ExtendedWebMapService,
        width_px: int,
        height_px: int,
        mask: Optional[GeoSeries] = None,
        driver: str = "GTiff",
        extract_metadata: bool = True,
        state_code: Optional[str] = None,
    ) -> Image:
        """
        Download a single tile and optionally extract metadata.
        
        This overrides the parent method to add metadata extraction after download.
        
        Args:
            img_path: Path where the image will be saved
            bounding_box: Bounding box polygon for the tile
            wms: Extended Web Map Service instance
            width_px: Image width in pixels
            height_px: Image height in pixels
            mask: Optional mask geometry
            driver: Rasterio driver (default: GTiff)
            extract_metadata: Whether to extract metadata (default: True)
            state_code: Two-letter state code for metadata extraction
            
        Returns:
            Image instance with download metadata
        """
        # Call parent implementation to download the tile
        image = ImageDownloader._download_tile(
            img_path, bounding_box, wms, width_px, height_px, mask, driver
        )
        
        # Extract and save metadata if requested
        if extract_metadata and state_code:
            try:
                # Calculate tile center for WMS query
                bounds = bounding_box.bounds
                center_x = (bounds[0] + bounds[2]) / 2
                center_y = (bounds[1] + bounds[3]) / 2
                
                # Extract metadata
                extractor = TileMetadataExtractor(wms.wms.url, state_code)
                metadata = extractor.extract_tile_metadata(
                    img_path,
                    center_x,
                    center_y,
                    crs=wms.crs
                )
                
                # Save metadata to JSON file
                metadata_path = TileMetadataExtractor.get_metadata_filename(img_path)
                extractor.save_metadata(metadata, metadata_path)
                
                logger.info(f"Metadata extracted and saved to: {metadata_path}")
                
            except Exception as e:
                logger.warning(f"Failed to extract metadata for {img_path}: {e}")
        
        return image


def create_downloader_with_metadata(
    wms_url: str,
    version: str,
    resolution: float,
    layer_name: str,
    crs: str,
    format: str,
    grid_spacing: int,
    state_code: str,
) -> ImageDownloaderWithMetadata:
    """
    Factory function to create an ImageDownloader with metadata extraction.
    
    Args:
        wms_url: WMS service URL
        version: WMS version
        resolution: Resolution in meters per pixel
        layer_name: WMS layer name
        crs: Coordinate reference system (e.g., 'EPSG:25832')
        format: Image format
        grid_spacing: Grid spacing in meters
        state_code: Two-letter state code
        
    Returns:
        ImageDownloaderWithMetadata instance
    """
    wms = ExtendedWebMapService(
        url=wms_url,
        version=version,
        resolution=resolution,
        layer_name=layer_name,
        crs=crs,
        format=format,
    )
    
    return ImageDownloaderWithMetadata(wms, grid_spacing, state_code)

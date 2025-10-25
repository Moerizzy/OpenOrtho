"""
STAC (SpatioTemporal Asset Catalog) Item Generator for Orthophoto Tiles.

This module creates STAC-compliant JSON items for downloaded orthophoto tiles,
including metadata extracted from WMS services and GeoTIFF files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

import rasterio
from rasterio.crs import CRS
from shapely.geometry import box, mapping

logger = logging.getLogger(__name__)


class STACItemGenerator:
    """
    Generate STAC Items for orthophoto tiles.
    
    STAC (SpatioTemporal Asset Catalog) is a specification for geospatial assets
    that makes them searchable and discoverable.
    """
    
    STAC_VERSION = "1.0.0"
    
    def __init__(self, collection_id: str = "german-orthophotos"):
        """
        Initialize STAC item generator.
        
        Args:
            collection_id: ID of the STAC collection these items belong to
        """
        self.collection_id = collection_id
    
    def create_stac_item(
        self,
        tile_path: Path,
        metadata: Dict[str, Any],
        item_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a STAC Item for a downloaded tile.
        
        Args:
            tile_path: Path to the GeoTIFF tile
            metadata: Metadata dictionary from TileMetadataExtractor
            item_id: Optional custom item ID (defaults to stem of tile_path)
        
        Returns:
            STAC Item as a dictionary
        """
        if item_id is None:
            item_id = tile_path.stem
        
        # Extract spatial information from GeoTIFF
        with rasterio.open(tile_path) as src:
            bounds = src.bounds
            crs = src.crs
            transform = src.transform
            width = src.width
            height = src.height
            num_bands = src.count
            
            # Create bounding box geometry
            bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]
            geometry = mapping(box(bounds.left, bounds.bottom, bounds.right, bounds.top))
        
        # Convert CRS to EPSG code for STAC
        if crs.is_epsg_code:
            epsg_code = crs.to_epsg()
        else:
            epsg_code = 4326  # Default to WGS84 if conversion fails
            logger.warning(f"Could not determine EPSG code for {tile_path}, using EPSG:4326")
        
        # Get acquisition date from metadata
        acquisition_date = metadata.get('acquisition_date')
        if acquisition_date:
            # Ensure it's in ISO 8601 format with timezone
            if 'T' not in acquisition_date:
                acquisition_date = f"{acquisition_date}T00:00:00Z"
            datetime_str = acquisition_date
        else:
            # Use current time if no acquisition date available
            datetime_str = datetime.utcnow().isoformat() + 'Z'
        
        # Determine image type and set appropriate band metadata
        filename = tile_path.name.upper()
        if 'RGBI' in filename:
            # 4-band: Red, Green, Blue, Near-Infrared
            eo_bands = [
                {"name": "red", "common_name": "red"},
                {"name": "green", "common_name": "green"},
                {"name": "blue", "common_name": "blue"},
                {"name": "nir", "common_name": "nir08"}
            ]
        elif 'CIR' in filename:
            # CIR: Red, Green, Near-Infrared (pseudo-color: NIR, Red, Green)
            eo_bands = [
                {"name": "nir", "common_name": "nir08"},
                {"name": "red", "common_name": "red"},
                {"name": "green", "common_name": "green"}
            ]
        else:
            # Default RGB: Red, Green, Blue
            eo_bands = [
                {"name": "red", "common_name": "red"},
                {"name": "green", "common_name": "green"},
                {"name": "blue", "common_name": "blue"}
            ]
        
        # Adjust bands to match actual number of bands in the file
        eo_bands = eo_bands[:num_bands]
        
        # Build STAC Item
        stac_item = {
            "stac_version": self.STAC_VERSION,
            "stac_extensions": [],
            "type": "Feature",
            "id": item_id,
            "bbox": bbox,
            "geometry": geometry,
            "properties": {
                "datetime": datetime_str,
                "created": datetime.utcnow().isoformat() + 'Z',
                "platform": "aerial",
                "instruments": ["camera"],
            },
            "collection": self.collection_id,
            "links": [
                {
                    "rel": "collection",
                    "href": f"./{self.collection_id}.json",
                    "type": "application/json"
                }
            ],
            "assets": {
                "image": {
                    "href": tile_path.name,
                    "type": "image/tiff; application=geotiff",
                    "roles": ["data"],
                    "title": "Orthophoto GeoTIFF",
                    "eo:bands": eo_bands
                }
            }
        }
        
        # Add projection extension if we have valid CRS
        if epsg_code:
            stac_item["stac_extensions"].append(
                "https://stac-extensions.github.io/projection/v1.0.0/schema.json"
            )
            stac_item["properties"]["proj:epsg"] = epsg_code
            stac_item["properties"]["proj:bbox"] = bbox
            stac_item["properties"]["proj:shape"] = [height, width]
            stac_item["properties"]["proj:transform"] = list(transform)[:6]
        
        # Add EO (Electro-Optical) extension for optical imagery
        stac_item["stac_extensions"].append(
            "https://stac-extensions.github.io/eo/v1.0.0/schema.json"
        )
        
        # Add all metadata fields as properties
        for key, value in metadata.items():
            # Skip internal fields
            if key in ['raw_response', 'raw_response_html']:
                continue
            
            # Add metadata with namespace prefix
            prop_key = f"ortho:{key}"
            
            # Convert values to JSON-serializable types
            if isinstance(value, (str, int, float, bool, type(None))):
                stac_item["properties"][prop_key] = value
            else:
                stac_item["properties"][prop_key] = str(value)
        
        # Add resolution if available
        if 'resolution' in metadata:
            stac_item["properties"]["gsd"] = metadata['resolution']
        
        # Add view extension if we have relevant metadata
        if any(k in metadata for k in ['sun_azimuth', 'sun_elevation', 'view_azimuth', 'view_elevation']):
            stac_item["stac_extensions"].append(
                "https://stac-extensions.github.io/view/v1.0.0/schema.json"
            )
            if 'sun_azimuth' in metadata:
                stac_item["properties"]["view:sun_azimuth"] = metadata['sun_azimuth']
            if 'sun_elevation' in metadata:
                stac_item["properties"]["view:sun_elevation"] = metadata['sun_elevation']
        
        return stac_item
    
    def save_stac_item(
        self,
        stac_item: Dict[str, Any],
        output_path: Path,
        indent: int = 2
    ) -> Path:
        """
        Save STAC Item to a JSON file.
        
        Args:
            stac_item: STAC Item dictionary
            output_path: Path where to save the JSON file
            indent: JSON indentation level
        
        Returns:
            Path to the saved file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stac_item, f, indent=indent, ensure_ascii=False)
        
        logger.info(f"STAC item saved to {output_path}")
        return output_path
    
    def create_and_save_stac_item(
        self,
        tile_path: Path,
        metadata: Dict[str, Any],
        item_id: Optional[str] = None,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Create and save a STAC Item in one call.
        
        Args:
            tile_path: Path to the GeoTIFF tile
            metadata: Metadata dictionary from TileMetadataExtractor
            item_id: Optional custom item ID
            output_path: Optional output path (defaults to tile_path with .json extension)
        
        Returns:
            Path to the saved STAC item JSON file
        """
        stac_item = self.create_stac_item(tile_path, metadata, item_id)
        
        if output_path is None:
            output_path = tile_path.with_suffix('.json')
        
        return self.save_stac_item(stac_item, output_path)

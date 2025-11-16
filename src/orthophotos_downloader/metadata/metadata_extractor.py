"""
Metadata extraction for orthophoto tiles.

This module provides functionality to extract metadata (resolution, date, quality)
from WMS services and downloaded GeoTIFF files.

Metadata service configurations are loaded from the central WMS catalog.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import rasterio
import requests
from xml.etree import ElementTree as ET


logger = logging.getLogger(__name__)


class TileMetadataExtractor:
    """
    Extract metadata for individual orthophoto tiles.
    
    Extracts:
    - Resolution: From GeoTIFF file
    - Acquisition date: From WMS GetFeatureInfo
    - Quality indicators: From WMS or GeoTIFF tags
    
    Metadata service configurations are loaded from the WMS catalog.
    """
    
    def __init__(self, wms_url: str, state_code: str, wms_service: Optional[Any] = None):
        """
        Initialize metadata extractor.
        
        Args:
            wms_url: Base URL of the WMS service
            state_code: Two-letter state code (e.g., 'BY', 'NW')
            wms_service: Optional WMSService object from catalog (preferred method)
        """
        self.wms_url = wms_url
        self.state_code = state_code
        self.wms_service = wms_service
        
        # Load metadata configuration from catalog if WMSService provided
        if wms_service and hasattr(wms_service, 'metadata') and wms_service.metadata:
            self.metadata_config = wms_service.metadata
        else:
            # Fallback: try to load from catalog by state code
            self.metadata_config = self._load_metadata_config_from_catalog()
    
    def _load_metadata_config_from_catalog(self) -> Dict[str, Any]:
        """
        Load metadata configuration from WMS catalog for this state.
        
        Returns:
            Dictionary with metadata service configuration, or empty dict if not found
        """
        try:
            # Lazy import to avoid circular dependency
            from orthophotos_downloader.wms_catalog import WMSCatalogManager
            
            catalog = WMSCatalogManager()
            services = catalog.filter_services(state_code=self.state_code)
            
            if services:
                # Use first service for this state (they share metadata config)
                service = services[0]
                if hasattr(service, 'metadata'):
                    logger.debug(f"Loaded metadata config for {self.state_code} from catalog")
                    return service.metadata
            
            logger.debug(f"No metadata config found for {self.state_code} in catalog")
            return {}
            
        except Exception as e:
            logger.warning(f"Failed to load metadata config from catalog: {e}")
            return {}
        
    def extract_tile_metadata(
        self, 
        tile_path: Path,
        center_x: float,
        center_y: float,
        crs: str = "EPSG:25832"
    ) -> Dict[str, Any]:
        """
        Extract complete metadata for a downloaded tile.
        
        Args:
            tile_path: Path to the downloaded GeoTIFF file
            center_x: X coordinate of tile center (for WMS query)
            center_y: Y coordinate of tile center (for WMS query)
            crs: Coordinate reference system
            
        Returns:
            Dictionary with metadata fields:
            
            Always present:
            - tile_path: Path to the tile file
            - extraction_timestamp: When metadata was extracted (ISO format)
            - state: Two-letter state code
            - resolution_x, resolution_y: Resolution in meters per pixel
            - resolution_unit: Always "meters"
            - width_pixels, height_pixels: Image dimensions
            - bands: Number of bands (3 for RGB)
            - crs: Coordinate reference system
            - bounds: Spatial extent (left, bottom, right, top)
            - dtype: Pixel data type
            
            State-dependent (from WMS):
            - acquisition_date: Date in ISO format (YYYY-MM-DD)
            - acquisition_date_raw: Original date string from WMS
            - tile_number: Tile identifier (Bayern)
            - update_number: Update cycle number (Bayern)
            - resolution_info: Resolution information text
            - quality: Quality indicator
            - flight_height: Flight altitude
            - sensor: Sensor information
            - source_layer: WMS layer name that provided metadata
            - raw_response: Full WMS response for debugging
            
            From GeoTIFF tags (if available):
            - geotiff_tags: Dictionary of TIFF tags
            - acquisition_date_from_tags: Date parsed from TIFF tags
        """
        metadata = {
            'tile_path': str(tile_path),
            'extraction_timestamp': datetime.now().isoformat(),
            'state': self.state_code,
        }
        
        # 1. Extract resolution from GeoTIFF
        try:
            geotiff_metadata = self._extract_geotiff_metadata(tile_path)
            metadata.update(geotiff_metadata)
        except Exception as e:
            logger.warning(f"Failed to extract GeoTIFF metadata: {e}")
            metadata['geotiff_error'] = str(e)
        
        # 2. Query WMS for acquisition date and quality
        # Query if state has metadata configuration in catalog
        if self.metadata_config and self.metadata_config.get('metadata_layer'):
            try:
                wms_metadata = self._query_wms_metadata(center_x, center_y, crs)
                
                # Check for year mismatch (NRW historic issue)
                # For NRW historic services, the metadata layer returns whichever year
                # has coverage at this location, which may not be the requested year
                if wms_metadata.get('metadata_year_mismatch'):
                    # Keep the WMS metadata (resolution, photometry, etc.) but use service year
                    logger.info(
                        f"Metadata year mismatch detected: WMS returned year "
                        f"{wms_metadata.get('extracted_year')}, but service year is "
                        f"{self.wms_service.year}. Using service year for acquisition_date."
                    )
                    # Use service year as the authoritative source
                    metadata['acquisition_date'] = f"{self.wms_service.year}-01-01"
                    metadata['acquisition_year'] = str(self.wms_service.year)
                    metadata['date_source'] = 'service_configuration'
                    
                    # Keep WMS-extracted date as reference (actual data at this location)
                    metadata['wms_extracted_date'] = wms_metadata.get('acquisition_date')
                    metadata['wms_extracted_year'] = wms_metadata.get('extracted_year')
                    
                    # Keep other useful WMS metadata
                    for key in ['resolution', 'photometry', 'ground_resolution', 'quality_info']:
                        if key in wms_metadata:
                            metadata[key] = wms_metadata[key]
                else:
                    # No mismatch - use WMS metadata as-is
                    metadata.update(wms_metadata)
                    
            except Exception as e:
                logger.warning(f"Failed to query WMS metadata: {e}")
                metadata['wms_error'] = str(e)
        else:
            metadata['wms_metadata'] = 'Not available for this state'
            
            # Fallback: Use year from service configuration if available
            # This helps services like Hamburg that have year-specific layers but no metadata service
            if self.wms_service and hasattr(self.wms_service, 'year') and self.wms_service.year:
                year = self.wms_service.year
                # Convert year to acquisition date (use January 1st as default)
                if isinstance(year, str) and year.isdigit():
                    metadata['acquisition_date'] = f"{year}-01-01"
                    metadata['acquisition_year'] = year
                    metadata['date_source'] = 'service_configuration'
                    logger.debug(f"Using year from service configuration: {year}")
                elif isinstance(year, int):
                    metadata['acquisition_date'] = f"{year}-01-01"
                    metadata['acquisition_year'] = str(year)
                    metadata['date_source'] = 'service_configuration'
                    logger.debug(f"Using year from service configuration: {year}")
        
        return metadata
    
    def _extract_geotiff_metadata(self, tile_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from GeoTIFF file.
        
        Returns resolution, bounds, CRS, and any embedded tags.
        """
        with rasterio.open(tile_path) as src:
            metadata = {
                'resolution_x': src.res[0],
                'resolution_y': src.res[1],
                'resolution_unit': 'meters',
                'width_pixels': src.width,
                'height_pixels': src.height,
                'bands': src.count,
                'crs': str(src.crs),
                'bounds': {
                    'left': src.bounds.left,
                    'bottom': src.bounds.bottom,
                    'right': src.bounds.right,
                    'top': src.bounds.top,
                },
                'dtype': str(src.dtypes[0]),
            }
            
            # Try to extract additional tags
            tags = src.tags()
            if tags:
                metadata['geotiff_tags'] = tags
                
                # Look for date in tags and parse it
                date_found = False
                for key in ['TIFFTAG_DATETIME', 'DateTime', 'date', 'acquisition_date']:
                    if key in tags:
                        parsed_date = self._parse_geotiff_datetime(tags[key])
                        if parsed_date:
                            metadata['acquisition_date_from_tags'] = parsed_date
                            date_found = True
                            break
                
                if not date_found and tags:
                    # Store raw tags if no date was parsed
                    metadata['geotiff_tags_raw'] = tags
            
            return metadata
    
    def _parse_geotiff_datetime(self, datetime_str: str) -> Optional[str]:
        """
        Parse datetime from GeoTIFF tags to ISO format.
        
        Common formats:
        - TIFFTAG_DATETIME: "2024:03:15 10:30:00"
        - Various other formats
        
        Returns:
            ISO formatted date string (YYYY-MM-DD) or None if parsing fails
        """
        from datetime import datetime
        import re
        
        # Try various datetime formats
        formats = [
            '%Y:%m:%d %H:%M:%S',    # 2024:03:15 10:30:00
            '%Y-%m-%d %H:%M:%S',    # 2024-03-15 10:30:00
            '%Y/%m/%d %H:%M:%S',    # 2024/03/15 10:30:00
            '%d.%m.%Y %H:%M:%S',    # 15.03.2024 10:30:00
            '%Y:%m:%d',             # 2024:03:15
            '%Y-%m-%d',             # 2024-03-15
            '%Y/%m/%d',             # 2024/03/15
            '%d.%m.%Y',             # 15.03.2024
        ]
        
        for fmt in formats:
            try:
                date_obj = datetime.strptime(datetime_str.strip(), fmt)
                return date_obj.strftime('%Y-%m-%d')
            except (ValueError, AttributeError):
                continue
        
        logger.debug(f"Could not parse GeoTIFF datetime: {datetime_str}")
        return None
    
    def _query_wms_metadata(
        self, 
        center_x: float, 
        center_y: float,
        crs: str
    ) -> Dict[str, Any]:
        """
        Query WMS GetFeatureInfo for metadata at tile location.
        
        Uses dedicated metadata service if available for the state,
        otherwise queries the standard WMS service.
        
        For NRW historic services: The metadata layer returns data for ALL years,
        but only for years that have actual coverage at the queried point. This
        means the returned metadata may be for a different year than the service year
        if the service year doesn't have coverage at this specific location.
        
        Args:
            center_x: X coordinate of query point
            center_y: Y coordinate of query point
            crs: Coordinate reference system
            
        Returns:
            Dictionary with acquisition date and quality info.
            For NRW historic, may include 'metadata_year_mismatch' warning.
        """
        # Use metadata configuration from catalog
        if not self.metadata_config:
            logger.debug(f"No metadata configuration available for {self.state_code}")
            return {'error': 'No metadata service configured for this state'}
        
        # Get metadata service URL (or use image service if same)
        wms_url = self.metadata_config.get('metadata_service_url', self.wms_url)
        metadata_layer = self.metadata_config.get('metadata_layer')
        info_format = self.metadata_config.get('metadata_info_format', 'text/plain')
        extra_params = self.metadata_config.get('metadata_extra_params', {})
        wms_version = self.metadata_config.get('metadata_wms_version', '1.3.0')
        
        if not metadata_layer:
            logger.debug(f"No metadata layer configured for {self.state_code}")
            return {'error': 'No metadata layer configured'}
        
        # For services with both image layer and metadata layer, query both
        # This is needed for NRW historic where metadata layer needs to know which year
        if self.wms_service and hasattr(self.wms_service, 'layer_name'):
            # Query both the image layer and metadata layer together
            layers = f"{self.wms_service.layer_name},{metadata_layer}"
            query_layers = metadata_layer  # Only query metadata layer for info
            year_info = f" (year: {self.wms_service.year})" if hasattr(self.wms_service, 'year') else ""
            logger.debug(f"Querying metadata for {self.state_code}: layers={layers}, query_layers={query_layers}{year_info}")
        else:
            # Fallback: just query metadata layer
            layers = metadata_layer
            query_layers = metadata_layer
            logger.debug(f"Querying metadata for {self.state_code}: layer={layers}")
        
        # Create bounding box around center point (1000m x 1000m)
        buffer = 500
        bbox = [
            center_x - buffer,
            center_y - buffer,
            center_x + buffer,
            center_y + buffer
        ]
        
        # Build GetFeatureInfo request based on WMS version
        if wms_version == '1.1.1':
            params = {
                'SERVICE': 'WMS',
                'REQUEST': 'GetFeatureInfo',
                'VERSION': '1.1.1',
                'LAYERS': layers,
                'QUERY_LAYERS': query_layers,
                'SRS': crs,  # WMS 1.1.1 uses SRS instead of CRS
                'BBOX': ','.join(map(str, bbox)),
                'WIDTH': 256,
                'HEIGHT': 256,
                'X': 128,  # WMS 1.1.1 uses X/Y instead of I/J
                'Y': 128,
                'INFO_FORMAT': info_format,
                'FEATURE_COUNT': '50',  # Request multiple features (for NRW historic multi-year responses)
            }
        else:  # WMS 1.3.0
            params = {
                'SERVICE': 'WMS',
                'REQUEST': 'GetFeatureInfo',
                'VERSION': '1.3.0',
                'LAYERS': layers,
                'QUERY_LAYERS': query_layers,
                'CRS': crs,
                'BBOX': ','.join(map(str, bbox)),
                'WIDTH': 256,
                'HEIGHT': 256,
                'I': 128,
                'J': 128,
                'INFO_FORMAT': info_format,
                'STYLES': '',  # Required by some services
                'FEATURE_COUNT': '50',  # Request multiple features (for NRW historic multi-year responses)
            }
        
        # Add any state-specific extra parameters from catalog
        params.update(extra_params)
        
        try:
            response = requests.get(wms_url, params=params, timeout=10)
            response.raise_for_status()
            
            # Log response for debugging (truncated if too long)
            response_preview = response.text[:500] if len(response.text) > 500 else response.text
            logger.debug(f"WMS metadata response received ({len(response.text)} chars): {response_preview}...")
            
            # Parse response
            parsed_metadata = self._parse_wms_response(response.text)
            
            # Check if we got useful metadata
            if parsed_metadata and 'acquisition_date' in parsed_metadata:
                logger.debug(f"Successfully extracted acquisition_date: {parsed_metadata['acquisition_date']}")
                
                # For NRW historic: Check if the extracted year matches the service year
                if self.wms_service and hasattr(self.wms_service, 'year'):
                    service_year = str(self.wms_service.year)
                    extracted_date = parsed_metadata['acquisition_date']
                    
                    # Skip year matching for non-numeric years (latest, current, year ranges)
                    # These always return the most current data available
                    is_numeric_year = service_year.isdigit()
                    
                    if is_numeric_year and service_year not in extracted_date:
                        # Year mismatch - metadata is for different year
                        # This is expected for NRW historic when the queried location doesn't have
                        # coverage for the specific service year
                        logger.warning(
                            f"Metadata year mismatch for {self.state_code}: "
                            f"service year={service_year}, extracted date={extracted_date}. "
                            f"This location may not have coverage for year {service_year}."
                        )
                        parsed_metadata['metadata_year_mismatch'] = True
                        parsed_metadata['service_year'] = service_year
                        parsed_metadata['extracted_year'] = extracted_date[:4]
                        
            elif parsed_metadata:
                logger.debug(f"Metadata extracted but no acquisition_date found. Keys: {list(parsed_metadata.keys())}")
            else:
                logger.debug("No metadata could be parsed from response")
                
            return parsed_metadata
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"WMS query failed: {e}")
            return {'wms_query_error': str(e)}
    
    def _parse_html_response(self, html_text: str) -> Dict[str, Any]:
        """
        Parse HTML response from WMS GetFeatureInfo (e.g., Niedersachsen).
        
        Extracts metadata from HTML table structure.
        """
        import re
        from datetime import datetime
        
        metadata = {}
        
        # Niedersachsen and Saarland HTML format patterns
        patterns = {
            # Niedersachsen patterns
            'tile_number': r'<b>Kachelnummer:</b></td>\s*<td[^>]*>([^<]+)</td>',
            'ni_ausgabe': r'<b>Ausgabe:</b></td>\s*<td[^>]*>([^<]+)</td>',
            'ni_befliegung': r'<b>Befliegung:</b></td>\s*<td[^>]*>([^<]+)</td>',
            'ni_bildflugnummer': r'<b>Bildflugnummer:</b></td>\s*<td[^>]*>([^<]+)</td>',
            'ground_resolution': r'<b>Bodenaufl.*?sung eines Pixels.*?</b></td>\s*<td[^>]*>\s*(\d+)</td>',
            'ni_orthophoto_date': r'<b>Datum der Orthophotoberechnung:</b></td>\s*<td[^>]*>([^<]+)</td>',
            'ni_import_date': r'<b>Importdatum:</b></td>\s*<td[^>]*>([^<]+)</td>',
            'ni_product': r'<b>Produkt:</b></td>\s*<td[^>]*>([^<]+)</td>',
            # Saarland patterns (no <b> tags, simpler format)
            'sl_name': r'<td>Name</td><td>([^<]+)</td>',
            'sl_nr': r'<td>Nr</td><td>([^<]+)</td>',
            'sl_titel': r'<td>Titel</td><td>([^<]+)</td>',
            'sl_erstellung': r'<td>Erstellung</td><td>([^<]+)</td>',
            'sl_aktualisierung': r'<td>Aktualisierung</td><td>([^<]+)</td>',
            'sl_publikation': r'<td>Publikation</td><td>([^<]+)</td>',
        }
        
        for field_name, pattern in patterns.items():
            match = re.search(pattern, html_text, re.IGNORECASE | re.DOTALL)
            if match:
                value = match.group(1).strip()
                # Clean HTML entities
                value = re.sub(r'&[a-z]+;', '', value)
                metadata[field_name] = value
        
        # Sachsen-Anhalt: Parse table with <th> headers and <td> data rows
        # Format: <th>Header1</th><th>Header2</th>...<tr><td>Value1</td><td>Value2</td>...
        th_pattern = r'<th>([^<]+)</th>'
        headers = re.findall(th_pattern, html_text, re.IGNORECASE)
        
        if headers:
            # Find the data row (first <tr> after headers with multiple <td> elements)
            # Match pattern: <tr><td>value1</td><td>value2</td>...
            tr_pattern = r'<tr>\s*(<td>[^<]+</td>\s*)+</tr>'
            tr_match = re.search(tr_pattern, html_text, re.IGNORECASE | re.DOTALL)
            
            if tr_match:
                # Extract all <td> values from the matched row
                td_pattern = r'<td>([^<]*)</td>'
                values = re.findall(td_pattern, tr_match.group(0), re.IGNORECASE)
                
                # Map headers to values
                for i, header in enumerate(headers):
                    if i < len(values):
                        value = values[i].strip()
                        if value:  # Only add non-empty values
                            # Normalize header name
                            field_name = header.lower().replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
                            field_name = re.sub(r'[^\w]+', '_', field_name)
                            field_name = f"st_{field_name}"
                            metadata[field_name] = value
        
        # Look for date pattern: "Datum der Befliegung:</b></td><td>2022-05-08</td>"
        date_match = re.search(
            r'<b>Datum der Befliegung:</b></td>\s*<td[^>]*>(\d{4}-\d{2}-\d{2})</td>',
            html_text,
            re.IGNORECASE | re.DOTALL
        )
        
        if date_match:
            date_str = date_match.group(1)
            try:
                # Already in ISO format YYYY-MM-DD
                datetime.strptime(date_str, '%Y-%m-%d')  # Validate
                metadata['acquisition_date'] = date_str
                metadata['acquisition_date_raw'] = f'Datum der Befliegung: {date_str}'
            except ValueError:
                logger.debug(f"Could not parse date: {date_str}")
        
        # Saarland: Check for Aktualisierung date (DD.MM.YYYY format)
        if 'sl_aktualisierung' in metadata and metadata['sl_aktualisierung'] != 'n/a':
            date_str = metadata['sl_aktualisierung']
            # Try to parse DD.MM.YYYY format
            date_pattern = r'(\d{2})\.(\d{2})\.(\d{4})'
            date_match = re.match(date_pattern, date_str)
            if date_match:
                day, month, year = date_match.groups()
                try:
                    date_obj = datetime(int(year), int(month), int(day))
                    metadata['acquisition_date'] = date_obj.strftime('%Y-%m-%d')
                    metadata['acquisition_date_raw'] = f'Aktualisierung: {date_str}'
                except ValueError:
                    logger.debug(f"Could not parse Saarland date: {date_str}")
        
        # Sachsen-Anhalt: Check for Befliegungsdatum date (DD.MM.YYYY format)
        if 'st_befliegungsdatum' in metadata:
            date_str = metadata['st_befliegungsdatum']
            # Try to parse DD.MM.YYYY format
            date_pattern = r'(\d{2})\.(\d{2})\.(\d{4})'
            date_match = re.match(date_pattern, date_str)
            if date_match:
                day, month, year = date_match.groups()
                try:
                    date_obj = datetime(int(year), int(month), int(day))
                    metadata['acquisition_date'] = date_obj.strftime('%Y-%m-%d')
                    metadata['acquisition_date_raw'] = f'Befliegungsdatum: {date_str}'
                except ValueError:
                    logger.debug(f"Could not parse Sachsen-Anhalt date: {date_str}")
        
        # Generic extraction: Extract ALL table rows with <b>label:</b><td>value</td> pattern
        # This captures any fields we might have missed with specific patterns
        generic_table_pattern = r'<b>([^<:]+):</b>\s*</td>\s*<td[^>]*>([^<]+)</td>'
        for match in re.finditer(generic_table_pattern, html_text, re.IGNORECASE | re.DOTALL):
            label = match.group(1).strip()
            value = match.group(2).strip()
            
            if label and value:
                # Create a field name from the label
                # Convert German characters and spaces to underscores
                field_name = label.lower()
                field_name = field_name.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
                field_name = re.sub(r'[^\w]+', '_', field_name)
                field_name = f"html_{field_name}"
                
                # Only add if not already captured with a specific pattern
                if field_name not in metadata and not any(v == value for v in metadata.values()):
                    # Clean HTML entities
                    value = re.sub(r'&[a-z]+;', '', value)
                    metadata[field_name] = value
        
        # Store raw HTML if reasonably small
        if len(html_text) < 5000:
            metadata['raw_response_html'] = html_text
        
        return metadata
    
    def _parse_nrw_feature(self, feature_text: str) -> Dict[str, Any]:
        """
        Parse a single NRW feature from GetFeatureInfo response.
        
        Args:
            feature_text: Text of one feature section
            
        Returns:
            Dictionary with extracted metadata
        """
        import re
        from datetime import datetime
        
        metadata = {}
        
        # Extract Bildflugdatum (flight date) - already in YYYY-MM-DD format
        date_match = re.search(r"Bildflugdatum\s*=\s*'([^']+)'", feature_text)
        if date_match:
            date_str = date_match.group(1)
            try:
                # NRW uses YYYY-MM-DD format
                if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                    metadata['acquisition_date'] = date_str
                    metadata['flight_date'] = date_str
                    metadata['wms_bildflugdatum'] = date_str
            except Exception as e:
                logger.debug(f"Failed to parse NRW date '{date_str}': {e}")
        
        # Extract resolution
        resolution_match = re.search(r"Bodenauflösung Originalbild \[m/Pixel\]\s*=\s*'([^']+)'", feature_text)
        if resolution_match:
            metadata['resolution'] = resolution_match.group(1)
            metadata['quality_info'] = f"Bodenauflösung = {resolution_match.group(1)}"
        
        # Extract photometry (RGB, RGBI, PAN, etc.)
        photo_match = re.search(r"Photometrie\s*=\s*'([^']+)'", feature_text)
        if photo_match:
            metadata['photometry'] = photo_match.group(1)
        
        # Extract original tile path
        tile_match = re.search(r"Download der Originalkachel\s*=\s*'([^']+)'", feature_text)
        if tile_match:
            metadata['wms_originalkachel'] = tile_match.group(1)
        
        return metadata
    
    def _parse_wms_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse WMS GetFeatureInfo response to extract date and quality.
        
        Different states return different formats, so we try multiple parsing strategies.
        Dates are converted to ISO format (YYYY-MM-DD).
        Handles both plain text and HTML responses.
        
        Special handling for NRW historic: Response contains multiple features (one per year).
        We need to find the feature matching the service's year.
        """
        import re
        from datetime import datetime
        
        metadata = {}
        
        # Check if response is HTML (Niedersachsen returns HTML)
        if '<html' in response_text.lower() or '<table' in response_text.lower():
            return self._parse_html_response(response_text)
        
        # Special handling for multi-feature responses (NRW historic)
        # Response may contain multiple "Feature XXX:" sections, one per available year
        # We need to find the one matching our service's year
        if 'Feature ' in response_text and self.wms_service and hasattr(self.wms_service, 'year'):
            year_to_find = str(self.wms_service.year)
            
            # Split response into individual features
            features = re.split(r'Feature \d+:', response_text)
            
            # Try to find matching feature by year in multiple ways:
            # 1. By download path (contains year in filename)
            # 2. By flight date field (Bildflugdatum contains year)
            best_match = None
            
            for feature_text in features:
                if not feature_text.strip():
                    continue
                    
                # Method 1: Check download path if available
                download_match = re.search(r"Download der Originalkachel\s*=\s*'([^']+)'", feature_text)
                if download_match:
                    download_path = download_match.group(1)
                    # Check if the path contains hist_dop_YYYY or _YYYY. in filename
                    if f'hist_dop_{year_to_find}/' in download_path or f'_nw_{year_to_find}.' in download_path:
                        logger.debug(f"Found matching feature by download path for year {year_to_find}")
                        return self._parse_nrw_feature(feature_text)
                
                # Method 2: Check Bildflugdatum (flight date) field
                date_match = re.search(r"Bildflugdatum\s*=\s*'([^']+)'", feature_text)
                if date_match:
                    date_str = date_match.group(1)
                    # Extract year from date (format: YYYY-MM-DD)
                    if date_str.startswith(year_to_find):
                        logger.debug(f"Found matching feature by Bildflugdatum for year {year_to_find}")
                        return self._parse_nrw_feature(feature_text)
            
            # If no exact match found, fall through to regular parsing
            logger.debug(f"No matching feature found for year {year_to_find} in multi-feature response")
        
        # Strategy 1: Look for state-specific date fields with various formats
        date_patterns = [
            # Bayern: ua = '10.06.2023' (DD.MM.YYYY)
            (r"ua\s*=\s*'(\d{2})\.(\d{2})\.(\d{4})'", 'dmy'),
            # NRW: Bildflugdatum = '01.03.2023' (DD.MM.YYYY)
            (r"Bildflugdatum\s*=\s*'(\d{2})\.(\d{2})\.(\d{4})'", 'dmy'),
            # Hessen: bildflug = '29-05-2023' (DD-MM-YYYY)
            (r"bildflug\s*=\s*'(\d{2})-(\d{2})-(\d{4})'", 'dmy_dash'),
            # Thüringen: Erstellung=02.05.2024 (DD.MM.YYYY without quotes)
            (r"Erstellung=(\d{2})\.(\d{2})\.(\d{4})", 'dmy'),
            # Berlin/Brandenburg: Ersterstellung = '04.06.2023' (DD.MM.YYYY with quotes)
            (r"Ersterstellung\s*=\s*'(\d{2})\.(\d{2})\.(\d{4})'", 'dmy'),
            # Mecklenburg-Vorpommern: Befliegungszeitraum = '2024-08-29' (YYYY-MM-DD)
            (r"Befliegungszeitraum\s*=\s*'(\d{4})-(\d{2})-(\d{2})'", 'ymd'),
            # Generic German format with keywords
            (r"datum[:\s=]+['\"]?(\d{2})\.(\d{2})\.(\d{4})['\"]?", 'dmy'),
            (r"aufnahme[:\s=]+['\"]?(\d{2})\.(\d{2})\.(\d{4})['\"]?", 'dmy'),
            (r"befliegung[:\s=]+['\"]?(\d{2})\.(\d{2})\.(\d{4})['\"]?", 'dmy'),
            # ISO format: YYYY-MM-DD
            (r"datum[:\s=]+['\"]?(\d{4})[-/](\d{2})[-/](\d{2})['\"]?", 'ymd'),
            (r"date[:\s=]+['\"]?(\d{4})[-/](\d{2})[-/](\d{2})['\"]?", 'ymd'),
            (r"aufnahme[:\s=]+['\"]?(\d{4})[-/](\d{2})[-/](\d{2})['\"]?", 'ymd'),
            # Generic patterns (try at end)
            (r"['\"]?(\d{2})\.(\d{2})\.(\d{4})['\"]?", 'dmy'),  # DD.MM.YYYY
            (r"['\"]?(\d{4})[-/](\d{2})[-/](\d{2})['\"]?", 'ymd'),  # YYYY-MM-DD
        ]
        
        date_str = None
        for pattern, date_format in date_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                try:
                    if date_format == 'dmy':
                        # DD.MM.YYYY format
                        day, month, year = match.groups()
                        date_obj = datetime(int(year), int(month), int(day))
                    elif date_format == 'dmy_dash':
                        # DD-MM-YYYY format (Hessen)
                        day, month, year = match.groups()
                        date_obj = datetime(int(year), int(month), int(day))
                    else:  # ymd
                        # YYYY-MM-DD format
                        year, month, day = match.groups()
                        date_obj = datetime(int(year), int(month), int(day))
                    
                    # Convert to ISO format
                    date_str = date_obj.strftime('%Y-%m-%d')
                    metadata['acquisition_date'] = date_str
                    metadata['acquisition_date_raw'] = match.group(0)
                    break
                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to parse date from '{match.group(0)}': {e}")
                    continue
        
        # Strategy 2: Extract structured fields from state-specific responses
        field_patterns = {
            # Bayern
            'tile_number': r"nummer\s*=\s*'([^']+)'",
            'update_number': r"unr\s*=\s*'([^']+)'",
            # NRW
            'tile_name': r"Kachelname\s*=\s*'([^']+)'",
            'flight_date': r"Bildflugdatum\s*=\s*'([^']+)'",
            'ground_resolution': r"Bodenauflösung\s*=\s*'([^']+)'",
            'photometry': r"Photometrie\s*=\s*'([^']+)'",
            'bits_per_channel': r"Bit_pro_Kanal\s*=\s*'([^']+)'",
            # Hessen (dedicated metadata service)
            'he_name': r"name\s*=\s*'([^']+)'",
            'he_land': r"land\s*=\s*'([^']+)'",
            'he_georef': r"georef\s*=\s*'([^']+)'",
            'he_resolution': r"aufloesung\s*=\s*'([^']+)'",
            'he_color': r"farbe\s*=\s*'([^']+)'",
            'he_reference': r"bezug\s*=\s*'([^']+)'",
            'he_flight_year': r"flugjahr\s*=\s*'([^']+)'",
            'he_last_update': r"aenderung\s*=\s*'([^']+)'",
            # Thüringen (special format with $#$ separators)
            'th_name': r"Name=([^$#]+)(?:\$#\$|$)",
            'th_title': r"Titel=([^$#]+)(?:\$#\$|$)",
            'th_publication': r"Publikation=([^$#]+)(?:\$#\$|$)",
            # Generic fields
            'resolution_info': r"aufloesung\s*=\s*'([^']+)'",
            'quality': r"qualitaet\s*=\s*'([^']+)'",
            'flight_height': r"flughoehe\s*=\s*'([^']+)'",
            'sensor': r"sensor\s*=\s*'([^']+)'",
        }
        
        for field_name, pattern in field_patterns.items():
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                metadata[field_name] = match.group(1)
        
        # Strategy 3: Look for quality indicators in text
        quality_keywords = ['qualität', 'quality', 'auflösung', 'resolution', 'genauigkeit', 'accuracy']
        for keyword in quality_keywords:
            if keyword in response_text.lower():
                lines = response_text.split('\n')
                for line in lines:
                    if keyword in line.lower():
                        metadata['quality_info'] = line.strip()
                        break
        
        # Strategy 4: Extract layer name if present
        layer_match = re.search(r"Layer\s+'([^']+)'", response_text)
        if layer_match:
            metadata['source_layer'] = layer_match.group(1)
        
        # Strategy 5: Generic extraction - capture ALL key-value pairs
        # This ensures we don't miss any fields not covered by specific patterns
        # Pattern: key = 'value' or key: value
        generic_patterns = [
            r"(\w+)\s*=\s*'([^']+)'",  # key = 'value'
            r"(\w+)\s*=\s*\"([^\"]+)\"",  # key = "value"
            r"(\w+)\s*=\s*([^\s$#]+)",  # key = value (no quotes)
            r"(\w+):\s*([^\n]+)",  # key: value (colon format)
        ]
        
        for pattern in generic_patterns:
            for match in re.finditer(pattern, response_text):
                key = match.group(1).lower().strip()
                value = match.group(2).strip()
                
                # Only add if we haven't already captured this field
                # and it's not an empty value
                if key and value and key not in metadata:
                    # Use original key name with prefix to avoid conflicts
                    field_name = f"wms_{key}"
                    metadata[field_name] = value
        
        # Store raw response for debugging (only if reasonably small)
        if len(response_text) < 1000:
            metadata['raw_response'] = response_text
        
        return metadata
    
    def save_metadata(self, metadata: Dict[str, Any], output_path: Path):
        """
        Save metadata to JSON file.
        
        Args:
            metadata: Metadata dictionary
            output_path: Path where to save the JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Metadata saved to: {output_path}")
    
    @staticmethod
    def get_metadata_filename(tile_path: Path) -> Path:
        """
        Generate metadata filename for a tile.
        
        Args:
            tile_path: Path to the tile file
            
        Returns:
            Path to metadata file (same location, .json extension)
        """
        return tile_path.with_suffix('.json')


def extract_and_save_tile_metadata(
    tile_path: Path,
    wms_url: str,
    state_code: str,
    center_x: float,
    center_y: float,
    crs: str = "EPSG:25832"
) -> Path:
    """
    Convenience function to extract and save metadata for a tile.
    
    Args:
        tile_path: Path to downloaded tile
        wms_url: WMS service URL
        state_code: Two-letter state code
        center_x: X coordinate of tile center
        center_y: Y coordinate of tile center
        crs: Coordinate reference system
        
    Returns:
        Path to saved metadata file
    """
    extractor = TileMetadataExtractor(wms_url, state_code)
    metadata = extractor.extract_tile_metadata(tile_path, center_x, center_y, crs)
    
    metadata_path = TileMetadataExtractor.get_metadata_filename(tile_path)
    extractor.save_metadata(metadata, metadata_path)
    
    return metadata_path

"""
Metadata extraction for orthophoto tiles.

This module provides functionality to extract metadata (resolution, date, quality)
from WMS services and downloaded GeoTIFF files.
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
    """
    
    # State-specific metadata layer mapping
    METADATA_LAYERS = {
        'BY': 'by_dop20_info',      # Bayern
        'BW': None,                   # Baden-Württemberg (dedicated metadata service)
        'BE': None,                   # Berlin (dedicated metadata service)
        'BB': None,                   # Brandenburg (dedicated metadata service)
        'HB': None,                   # Bremen
        'HH': None,                   # Hamburg
        'HE': 'wms_he_dop',          # Hessen (dedicated metadata service)
        'MV': 'mv_dop_info',         # Mecklenburg-Vorpommern
        'NI': 'ni_dop20_info',       # Niedersachsen
        'NW': 'nw_dop_utm_info',     # Nordrhein-Westfalen
        'RP': 'rp_dop20_info',       # Rheinland-Pfalz
        'SL': None,                   # Saarland (dedicated metadata service)
        'SN': 'sn_dop_020_info',     # Sachsen
        'ST': None,                   # Sachsen-Anhalt
        'SH': 'DOP20',               # Schleswig-Holstein (dedicated metadata service)
        'TH': 'th_dop_info',         # Thüringen
    }
    
    # States with dedicated metadata WMS services (different URL than image service)
    METADATA_SERVICES = {
        'BE': {
            'url': 'https://isk.geobasis-bb.de/ows/aktualitaeten_wms?',
            'layer': 'bb_dop_info',
            'description': 'Berlin dedicated metadata service with orthophoto info (shared with Brandenburg)',
            'extra_params': {},
            'info_format': 'text/plain',
        },
        'BB': {
            'url': 'https://isk.geobasis-bb.de/ows/aktualitaeten_wms?',
            'layer': 'bb_dop_info',
            'description': 'Brandenburg dedicated metadata service with orthophoto info (shared with Berlin)',
            'extra_params': {},
            'info_format': 'text/plain',
        },
        'BW': {
            'url': 'https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_DOP_20_Bildflugkacheln_Aktualitaet?',
            'layer': 'verm:v_dop_20_bildflugkacheln',
            'description': 'Baden-Württemberg dedicated metadata service with flight info',
            'extra_params': {'FORMAT': 'image/png'},  # Required by BW WMS
        },
        'HE': {
            'url': 'https://www.gds-srv.hessen.de/cgi-bin/lika-services/ogc-free-images.ows?language=ger&',
            'layer': 'wms_he_dop',
            'description': 'Dedicated Hessen metadata service with detailed acquisition info',
            'extra_params': {},
        },
        'NI': {
            'url': 'https://opendata.lgln.niedersachsen.de/doorman/noauth/dop_wms?language=ger&',
            'layer': 'ni_dop20_info',
            'description': 'Niedersachsen metadata service returning HTML',
            'extra_params': {'FORMAT': 'image/png', 'STYLES': ''},  # Required by NI WMS
            'info_format': 'text/html',  # Returns HTML instead of text/plain
        },
        'SH': {
            'url': 'https://service.gdi-sh.de/WMS_SH_MD_DOP?',
            'layer': 'DOP20',
            'description': 'Schleswig-Holstein dedicated metadata WMS service',
            'extra_params': {},
        },
        'SL': {
            'url': 'https://geoportal.saarland.de/freewms/truedop?',
            'layer': 'sl_dop_info',
            'description': 'Saarland metadata service',
            'extra_params': {'STYLES': ''},  # Required by SL WMS
            'info_format': 'text/html',  # Returns HTML instead of text/plain
        },
        'ST': {
            'url': 'https://www.geodatenportal.sachsen-anhalt.de/wss/service/ST_LVermGeo_DOP_WMS_Kacheluebersicht/guest?',
            'layer': 'Aktualität_der_Orthophotos41668',
            'description': 'Sachsen-Anhalt metadata service',
            'extra_params': {},
            'info_format': 'text/html',  # Returns HTML instead of text/plain
        },
        # Add more states here as they are discovered
    }
    
    def __init__(self, wms_url: str, state_code: str):
        """
        Initialize metadata extractor.
        
        Args:
            wms_url: Base URL of the WMS service
            state_code: Two-letter state code (e.g., 'BY', 'NW')
        """
        self.wms_url = wms_url
        self.state_code = state_code
        self.metadata_layer = self.METADATA_LAYERS.get(state_code)
        
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
        # Query if state has a metadata layer OR has a dedicated metadata service
        has_metadata_source = self.metadata_layer is not None or self.state_code in self.METADATA_SERVICES
        if has_metadata_source:
            try:
                wms_metadata = self._query_wms_metadata(center_x, center_y, crs)
                metadata.update(wms_metadata)
            except Exception as e:
                logger.warning(f"Failed to query WMS metadata: {e}")
                metadata['wms_error'] = str(e)
        else:
            metadata['wms_metadata'] = 'Not available for this state'
        
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
        
        Args:
            center_x: X coordinate of query point
            center_y: Y coordinate of query point
            crs: Coordinate reference system
            
        Returns:
            Dictionary with acquisition date and quality info
        """
        # Check if this state has a dedicated metadata service
        wms_url = self.wms_url
        layer = self.metadata_layer
        info_format = 'text/plain'
        extra_params = {}
        
        if self.state_code in self.METADATA_SERVICES:
            metadata_service = self.METADATA_SERVICES[self.state_code]
            wms_url = metadata_service['url']
            layer = metadata_service['layer']
            info_format = metadata_service.get('info_format', 'text/plain')
            extra_params = metadata_service.get('extra_params', {})
            logger.debug(f"Using dedicated metadata service for {self.state_code}")
        
        # Create bounding box around center point (1000m x 1000m)
        buffer = 500
        bbox = [
            center_x - buffer,
            center_y - buffer,
            center_x + buffer,
            center_y + buffer
        ]
        
        # Build GetFeatureInfo request
        # Try WMS 1.1.1 first (more widely supported for metadata), or 1.3.0 if needed
        wms_version = '1.3.0' if self.state_code in ['NI', 'SH', 'MV', 'BE', 'BB'] else '1.1.1'
        
        if wms_version == '1.1.1':
            params = {
                'SERVICE': 'WMS',
                'REQUEST': 'GetFeatureInfo',
                'VERSION': '1.1.1',
                'LAYERS': layer,
                'QUERY_LAYERS': layer,
                'SRS': crs,  # WMS 1.1.1 uses SRS instead of CRS
                'BBOX': ','.join(map(str, bbox)),
                'WIDTH': 256,
                'HEIGHT': 256,
                'X': 128,  # WMS 1.1.1 uses X/Y instead of I/J
                'Y': 128,
                'INFO_FORMAT': info_format,
            }
        else:  # WMS 1.3.0
            params = {
                'SERVICE': 'WMS',
                'REQUEST': 'GetFeatureInfo',
                'VERSION': '1.3.0',
                'LAYERS': layer,
                'QUERY_LAYERS': layer,
                'CRS': crs,
                'BBOX': ','.join(map(str, bbox)),
                'WIDTH': 256,
                'HEIGHT': 256,
                'I': 128,
                'J': 128,
                'INFO_FORMAT': info_format,
                'STYLES': '',  # Required by some services (e.g., MV)
            }
        
        # Add any state-specific extra parameters
        params.update(extra_params)
        
        try:
            response = requests.get(wms_url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse response
            return self._parse_wms_response(response.text)
            
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
    
    def _parse_wms_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse WMS GetFeatureInfo response to extract date and quality.
        
        Different states return different formats, so we try multiple parsing strategies.
        Dates are converted to ISO format (YYYY-MM-DD).
        Handles both plain text and HTML responses.
        """
        import re
        from datetime import datetime
        
        metadata = {}
        
        # Check if response is HTML (Niedersachsen returns HTML)
        if '<html' in response_text.lower() or '<table' in response_text.lower():
            return self._parse_html_response(response_text)
        
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

"""
File-based orthophoto downloader

Downloads orthophoto tiles directly from file servers instead of WMS.
Provides better quality (no compression) and faster bulk downloads.
"""

import logging
import math
import re
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from urllib.parse import parse_qs, urlparse, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
from shapely.geometry import Polygon, box
from shapely.strtree import STRtree
from shapely.ops import transform
import geopandas as gpd
from pyproj import Transformer

from orthophotos_downloader.data_scraping.image_download import (
    ImageDownloader,
    AreaDataset,
    Image
)
from orthophotos_downloader.wms_catalog.catalog_manager import WMSService
from orthophotos_downloader.metadata.stac_generator import STACItemGenerator

logger = logging.getLogger(__name__)


class FileServiceDownloader:
    """
    Download orthophoto tiles directly from file servers.
    
    This downloader:
    - Calculates which tiles are needed based on area and grid size
    - Downloads files directly via HTTP
    - Handles CRS transformations if file CRS differs from target
    - Provides parallel downloads for efficiency
    
    Example:
        >>> service = catalog.get_service_by_id('NW_RGB_DOP20_1951')
        >>> downloader = FileServiceDownloader(service, grid_spacing=1000)
        >>> result = downloader.download_images_from_polygon(
        ...     area_polygon=area,
        ...     out_path=Path('output')
        ... )
    """

    _ATOM_NAMESPACES = {
        'atom': 'http://www.w3.org/2005/Atom',
        'georss': 'http://www.georss.org/georss',
        'inspire': 'http://inspire.ec.europa.eu/schemas/inspire_dls/1.0',
    }
    _atom_feed_cache: Dict[str, Dict[str, object]] = {}
    _atom_tile_cache: Dict[str, Dict[str, str]] = {}
    _transformer_4326_to_25832 = Transformer.from_crs(
        'EPSG:4326',
        'EPSG:25832',
        always_xy=True
    )
    
    def __init__(
        self,
        service: WMSService,
        grid_spacing: int,
        extract_metadata: bool = False,
        max_workers: int = 4,
        verify_coverage: bool = False,
        coverage_cache = None
    ):
        """
        Initialize file downloader.
        
        Args:
            service: WMSService object with files configuration
            grid_spacing: Grid spacing in meters (for reference, files come as-is)
            extract_metadata: Whether to extract metadata (not yet implemented for files)
            max_workers: Number of parallel download threads
            verify_coverage: Whether to verify actual coverage before downloading
            coverage_cache: Optional ServiceCoverageCache for coverage verification
        """
        if not service.has_files():
            raise ValueError(
                f"Service {service.id} does not support file delivery. "
                f"Available methods: {service.get_delivery_methods()}"
            )
        
        self.service = service
        self.grid_spacing = grid_spacing
        self.extract_metadata = extract_metadata
        self.max_workers = max_workers
        self.verify_coverage = verify_coverage
        self.coverage_cache = coverage_cache
        self._atom_extra_metadata: Dict[Path, Dict[str, object]] = {}
        self.files_wcs_max_pixels = (
            service.files_wcs_max_pixels
            if service.files_wcs_max_pixels is not None
            else 4000
        )
        
        # Initialize STAC generator if metadata extraction is enabled
        self.stac_generator = None
        if extract_metadata:
            self.stac_generator = STACItemGenerator()
        
        # Metadata cache (will be loaded on first use)
        self._metadata_csv = None
        
        # CRS transformer (from file CRS to target CRS EPSG:25832)
        self.transformer = None
        if service.files_crs and service.files_crs != 'EPSG:25832':
            self.transformer = Transformer.from_crs(
                'EPSG:25832',
                service.files_crs,
                always_xy=True
            )
        
        # Determine grid size info for logging
        grid_info = f"{service.files_grid_size}m" if service.files_grid_size else "GeoJSON-indexed"
        index_type = f", index={service.files_index_type}" if service.files_index_type else ""
        
        logger.info(
            f"Initialized FileServiceDownloader for {service.id}: "
            f"grid={grid_info}, crs={service.files_crs}{index_type}, "
            f"coverage_verification={verify_coverage}"
        )
    
    def _load_metadata_csv(self) -> Optional[dict]:
        """
        Load and parse the metadata CSV file if configured.
        
        Returns:
            Dictionary mapping tile names to metadata dicts, or None if not available
        """
        if self._metadata_csv is not None:
            return self._metadata_csv
        
        # Check if metadata is configured
        if not self.service.files_metadata or 'url' not in self.service.files_metadata:
            logger.debug(f"No metadata configured for service {self.service.id}")
            return None
        
        try:
            import io
            import zipfile
            import csv
            
            metadata_url = self.service.files_metadata['url']
            logger.info(f"Downloading metadata from {metadata_url}")
            
            # Download metadata file (may be ZIP or CSV)
            response = requests.get(metadata_url, timeout=60)
            response.raise_for_status()
            
            # Parse based on format
            csv_content = None
            if metadata_url.endswith('.zip'):
                # Extract CSV from ZIP
                with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                    # Find CSV file in ZIP
                    csv_files = [name for name in zf.namelist() if name.endswith('.csv')]
                    if csv_files:
                        csv_content = zf.read(csv_files[0]).decode(
                            self.service.files_metadata.get('encoding', 'utf-8')
                        )
                    else:
                        logger.warning(f"No CSV file found in metadata ZIP")
                        return None
            else:
                # Direct CSV
                csv_content = response.text
            
            if not csv_content:
                return None
            
            # Parse CSV
            delimiter = self.service.files_metadata.get('delimiter', ';')
            tile_column = self.service.files_metadata.get('tile_column', 'Kachelname')
            
            # Skip header lines (first 6 lines for NRW format)
            lines = csv_content.strip().split('\n')
            header_line_idx = None
            for i, line in enumerate(lines):
                if tile_column in line:
                    header_line_idx = i
                    break
            
            if header_line_idx is None:
                logger.warning(f"Could not find header line with '{tile_column}'")
                return None
            
            # Parse CSV starting from header
            csv_data = '\n'.join(lines[header_line_idx:])
            reader = csv.DictReader(io.StringIO(csv_data), delimiter=delimiter)
            
            # Build metadata dictionary
            metadata_dict = {}
            for row in reader:
                tile_name = row.get(tile_column)
                if tile_name:
                    metadata_dict[tile_name] = row
            
            logger.info(f"Loaded metadata for {len(metadata_dict)} tiles")
            self._metadata_csv = metadata_dict
            return self._metadata_csv
            
        except Exception as e:
            logger.warning(f"Failed to load metadata CSV: {e}")
            return None
    
    @classmethod
    def _normalize_geometry(cls, geometry: Polygon) -> Polygon:
        """
        Ensure tile geometry uses EPSG:25832 for intersection operations.
        Converts from geographic coordinates if necessary.
        """
        minx, miny, maxx, maxy = geometry.bounds
        if (
            -180.0 <= minx <= 180.0
            and -180.0 <= maxx <= 180.0
            and -90.0 <= miny <= 90.0
            and -90.0 <= maxy <= 90.0
        ):
            geometry = transform(cls._transformer_4326_to_25832.transform, geometry)
        return geometry
    
    @staticmethod
    def _parse_atom_feed(feed_xml: bytes) -> List[Dict[str, object]]:
        """
        Parse an Atom feed describing orthophoto tiles.
        
        Args:
            feed_xml: Raw Atom feed data in bytes.
        
        Returns:
            List of dictionaries with geometry and metadata for each entry.
        """
        entries: List[Dict[str, object]] = []
        try:
            root = ET.fromstring(feed_xml)
        except ET.ParseError as exc:
            logger.error(f"Failed to parse Atom feed: {exc}")
            return entries
        
        ns = FileServiceDownloader._ATOM_NAMESPACES
        
        for entry_elem in root.findall('atom:entry', ns):
            polygon_text = entry_elem.findtext('georss:polygon', default='', namespaces=ns)
            if not polygon_text:
                continue
            coords = polygon_text.strip().split()
            if len(coords) % 2 != 0:
                logger.warning("Skipping Atom entry with invalid polygon coordinates")
                continue
            
            points = []
            for idx in range(0, len(coords), 2):
                try:
                    northing = float(coords[idx])
                    easting = float(coords[idx + 1])
                except ValueError:
                    points = []
                    break
                points.append((easting, northing))
            if len(points) < 4:
                continue
            
            polygon = Polygon(points)
            polygon = FileServiceDownloader._normalize_geometry(polygon)
            code = entry_elem.findtext('inspire:spatial_dataset_identifier_code', default='', namespaces=ns)
            year = None
            if code:
                parts = code.split('_')
                for part in reversed(parts):
                    if part.isdigit() and len(part) == 4:
                        year = part
                        break
            product = code.split('_')[0] if code else None
            tile_key = FileServiceDownloader._tile_key_from_code(code)
            
            tile_feed_url = None
            for link_elem in entry_elem.findall('atom:link', ns):
                if link_elem.get('rel') == 'alternate':
                    tile_feed_url = link_elem.get('href')
                    break
            
            summary_text = entry_elem.findtext('atom:summary', default='', namespaces=ns)
            acquisition_date = None
            if summary_text:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', summary_text)
                if date_match:
                    acquisition_date = date_match.group(1)
            
            tile_feed_url = None
            direct_download = None
            for link_elem in entry_elem.findall('atom:link', ns):
                rel = link_elem.get('rel')
                href = link_elem.get('href')
                if rel == 'alternate' and href:
                    tile_feed_url = href
                elif rel in ['enclosure', 'related'] and href and direct_download is None:
                    direct_download = href
            entries.append(
                {
                    'geometry': polygon,
                    'code': code,
                    'year': year,
                    'product': product,
                    'tile_key': tile_key,
                    'tile_feed_url': tile_feed_url,
                    'summary': summary_text,
                    'acquisition_date': acquisition_date,
                    'title': entry_elem.findtext('atom:title', default='', namespaces=ns),
                    'updated': entry_elem.findtext('atom:updated', default='', namespaces=ns),
                    'download_url': direct_download,
                }
            )
        
        # Some feeds (e.g., MV) expose tiles using <link rel="section"> elements
        for link_elem in root.findall('.//atom:link', ns):
            if link_elem.get('rel') != 'section':
                continue
            href = link_elem.get('href')
            if not href:
                continue
            bbox_attr = link_elem.get('bbox') or link_elem.get('{http://www.georss.org/georss}box')
            if not bbox_attr:
                continue
            try:
                bbox_values = [float(v) for v in bbox_attr.replace(',', ' ').split() if v]
            except ValueError:
                logger.debug("Skipping Atom section with invalid bbox")
                continue
            if len(bbox_values) != 4:
                continue
            min_lat, min_lon, max_lat, max_lon = bbox_values
            polygon = box(min_lon, min_lat, max_lon, max_lat)
            polygon = FileServiceDownloader._normalize_geometry(polygon)
            parsed_href = urlparse(href)
            params = parse_qs(parsed_href.query)
            file_name = params.get('file', [Path(parsed_href.path).name])
            file_name = file_name[0]
            if not file_name:
                continue
            code = Path(file_name).stem
            product = code.split('_')[0] if '_' in code else None
            tile_key = FileServiceDownloader._tile_key_from_code(code)
            summary_text = link_elem.get('title') or ''
            entry = {
                'geometry': polygon,
                'code': code,
                'year': None,
                'product': product,
                'tile_key': tile_key,
                'tile_feed_url': None,
                'summary': summary_text,
                'acquisition_date': None,
                'title': summary_text,
                'updated': None,
                'download_url': href,
            }
            entries.append(entry)
        
        # Adjust entries pointing to GML tile descriptions (download link inside GML)
        for entry in entries:
            href = entry.get('download_url') or entry.get('tile_feed_url')
            if href and href.lower().endswith('.gml'):
                entry['tile_feed_url'] = href
                entry['download_url'] = None
        
        return entries
    
    @staticmethod
    def _tile_key_from_code(code: Optional[str]) -> Optional[str]:
        """Return code without trailing year to group tiles across years."""
        if not code:
            return None
        parts = code.split('_')
        if len(parts) <= 1:
            return code
        return '_'.join(parts[:-1])
    
    @staticmethod
    def _parse_atom_tile_feed(tile_xml: bytes) -> Dict[str, str]:
        """Parse a tile feed (Atom or GML) and extract a download URL."""
        try:
            root = ET.fromstring(tile_xml)
        except ET.ParseError as exc:
            raise ValueError(f"Failed to parse tile Atom feed: {exc}") from exc

        ns = FileServiceDownloader._ATOM_NAMESPACES
        entry_elem = root.find('atom:entry', ns)
        if entry_elem is not None:
            download_href = None
            for link_elem in entry_elem.findall('atom:link', ns):
                if link_elem.get('rel') == 'alternate':
                    download_href = link_elem.get('href')
                    break
            if not download_href:
                raise ValueError("Tile Atom feed missing alternate download link")

            parsed = urlparse(download_href)
            params = parse_qs(parsed.query)
            wcs_url = params.get('WCSUrl', [download_href])[0]
            wcs_url = unquote(wcs_url)

            return {
                'download_url': wcs_url,
                'title': entry_elem.findtext('atom:title', default='', namespaces=ns) or '',
            }

        # Non-Atom (e.g., GML coverage description)
        file_url = None
        file_reference = root.find('.//{*}fileReference')
        if file_reference is not None and file_reference.text:
            file_url = file_reference.text.strip()
        if not file_url:
            range_params = root.find(".//{*}rangeParameters")
            if range_params is not None:
                file_url = range_params.attrib.get('{http://www.w3.org/1999/xlink}href')
        if not file_url:
            raise ValueError("Tile feed does not contain a downloadable resource")

        identifier = root.find('.//{*}localId')
        title = identifier.text if identifier is not None else ''

        return {
            'download_url': file_url,
            'title': title,
        }
    
    @classmethod
    def _get_atom_feed_data(cls, feed_url: str) -> Dict[str, object]:
        """
        Retrieve cached parsing results for an Atom feed.
        """
        cached = cls._atom_feed_cache.get(feed_url)
        if cached:
            return cached
        
        logger.info(f"Fetching Atom feed: {feed_url}")
        response = requests.get(feed_url, timeout=120)
        response.raise_for_status()
        entries = cls._parse_atom_feed(response.content)
        
        polygons = [entry['geometry'] for entry in entries]
        tree = STRtree(polygons) if polygons else None
        cached = {'entries': entries, 'polygons': polygons, 'tree': tree}
        cls._atom_feed_cache[feed_url] = cached
        return cached
    
    @classmethod
    def _resolve_atom_tile(cls, tile_feed_url: str) -> Dict[str, str]:
        """
        Fetch and cache metadata for a specific tile feed.
        """
        cached = cls._atom_tile_cache.get(tile_feed_url)
        if cached:
            return cached
        
        logger.debug(f"Fetching tile feed: {tile_feed_url}")
        response = requests.get(tile_feed_url, timeout=60)
        response.raise_for_status()
        details = cls._parse_atom_tile_feed(response.content)
        cls._atom_tile_cache[tile_feed_url] = details
        return details
    
    def _adjust_wcs_resolution(self, wcs_url: str) -> str:
        """
        Ensure the WCS request uses the service resolution (e.g., 0.2m for DOP20).
        """
        try:
            parsed = urlparse(wcs_url)
            query = parse_qs(parsed.query, keep_blank_values=True)
            bbox_values = query.get('BBOX') or query.get('bbox')
            if not bbox_values:
                return wcs_url
            
            bbox_parts = bbox_values[0].split(',')
            if len(bbox_parts) != 4:
                return wcs_url
            minx, miny, maxx, maxy = map(float, bbox_parts)
            width_m = maxx - minx
            height_m = maxy - miny
            if width_m <= 0 or height_m <= 0:
                return wcs_url
            
            target_res = float(self.service.resolution or 0.2)
            width_px = int(round(width_m / target_res))
            height_px = int(round(height_m / target_res))
            if width_px <= 0 or height_px <= 0:
                return wcs_url
            
            max_dim = self.files_wcs_max_pixels or 4000
            if width_px > max_dim or height_px > max_dim:
                scale = max(width_px, height_px) / max_dim
                width_px = max(1, int(round(width_px / scale)))
                height_px = max(1, int(round(height_px / scale)))
                # Update effective resolution information so downstream users are aware
                effective_res_x = width_m / width_px
                effective_res_y = height_m / height_px
                query['RESX'] = [f"{effective_res_x:.6f}"]
                query['RESY'] = [f"{effective_res_y:.6f}"]
            else:
                query.pop('RESX', None)
                query.pop('RESY', None)
            
            query['WIDTH'] = [str(width_px)]
            query['HEIGHT'] = [str(height_px)]
            
            new_query = '&'.join(
                f"{key}={value}"
                for key, values in query.items()
                for value in values
            )
            return parsed._replace(query=new_query).geturl()
        except Exception:
            return wcs_url
    
    def calculate_required_tiles(self, area_polygon: Polygon) -> List[Tuple[int, int]]:
        """
        Calculate which tile coordinates are needed to cover the area.
        
        Args:
            area_polygon: Area of interest in EPSG:25832
            
        Returns:
            List of (x, y) tile coordinates in the file's CRS grid
        """
        # Transform area to file CRS if needed
        if self.transformer:
            # Get bounds in EPSG:25832
            minx, miny, maxx, maxy = area_polygon.bounds
            
            # Transform corners to file CRS
            corners = [
                self.transformer.transform(minx, miny),
                self.transformer.transform(maxx, miny),
                self.transformer.transform(minx, maxy),
                self.transformer.transform(maxx, maxy)
            ]
            
            # Get bounds in file CRS
            file_minx = min(c[0] for c in corners)
            file_miny = min(c[1] for c in corners)
            file_maxx = max(c[0] for c in corners)
            file_maxy = max(c[1] for c in corners)
        else:
            # Already in correct CRS
            file_minx, file_miny, file_maxx, file_maxy = area_polygon.bounds
        
        # Calculate tile indices
        grid_size = self.service.files_grid_size
        
        # Check if grid_size is None (e.g., for GeoJSON-indexed services)
        if grid_size is None:
            logger.error(
                f"Service {self.service.id} has no grid_size defined. "
                f"This may be a GeoJSON-indexed service which requires different handling."
            )
            raise ValueError(
                f"Cannot calculate grid tiles for service {self.service.id}: "
                f"files_grid_size is not defined. Use GeoJSON-based download instead."
            )
        
        # Tiles are named by their lower-left corner in km
        # Round down to grid size, then convert to km
        tile_x_start = int(file_minx // grid_size) * (grid_size // 1000)
        tile_x_end = int(file_maxx // grid_size) * (grid_size // 1000)
        tile_y_start = int(file_miny // grid_size) * (grid_size // 1000)
        tile_y_end = int(file_maxy // grid_size) * (grid_size // 1000)
        
        # Generate list of tiles
        tiles = []
        x = tile_x_start
        while x <= tile_x_end:
            y = tile_y_start
            while y <= tile_y_end:
                tiles.append((x, y))
                y += (grid_size // 1000)
            x += (grid_size // 1000)
        
        logger.info(
            f"Calculated {len(tiles)} tiles needed: "
            f"X: {tile_x_start}-{tile_x_end}, Y: {tile_y_start}-{tile_y_end}"
        )
        
        return tiles
    
    def get_tiles_from_geojson_index(self, area_polygon: Polygon, target_year: Optional[str] = None) -> List[dict]:
        """
        Get tiles that intersect with area using GeoJSON index.
        
        Args:
            area_polygon: Area of interest in EPSG:25832
            target_year: Optional specific year to filter for (e.g., '2015')
                        If None, returns most recent tiles
            
        Returns:
            List of tile info dictionaries with download URLs and metadata
        """
        if not self.service.files_geojson_url:
            raise ValueError(
                f"Service {self.service.id} has no GeoJSON index URL defined"
            )
        
        logger.info(f"Loading GeoJSON index from {self.service.files_geojson_url}")
        
        try:
            import json
            
            # Download GeoJSON index
            response = requests.get(self.service.files_geojson_url, timeout=60)
            response.raise_for_status()
            geojson_data = response.json()
            
            # Load into GeoDataFrame for spatial operations
            gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
            
            # Ensure it's in the correct CRS (EPSG:25832)
            if gdf.crs is None:
                gdf.set_crs('EPSG:25832', inplace=True)
            elif gdf.crs != 'EPSG:25832':
                gdf = gdf.to_crs('EPSG:25832')
            
            # Filter by year if specified
            if target_year:
                logger.info(f"Filtering GeoJSON index for year {target_year}")
                if 'Aktualitaet' in gdf.columns:
                    # Extract year from Aktualitaet column (format: "2015-04-20 00:00:00")
                    gdf['year'] = gdf['Aktualitaet'].str.split('-').str[0]
                    gdf = gdf[gdf['year'] == str(target_year)]
                    logger.info(f"Found {len(gdf)} tiles from year {target_year}")
                else:
                    logger.warning(f"No date column found for year filtering. Using all tiles.")
            
            # Find tiles that intersect with area
            intersecting = gdf[gdf.intersects(area_polygon)]
            
            logger.info(
                f"Found {len(intersecting)} tiles intersecting with area "
                f"(out of {len(gdf)} total tiles in {'year ' + str(target_year) if target_year else 'index'})"
            )
            
            # Group by tile location and keep only the most recent year (or single year if target_year specified)
            # Many GeoJSON indices have multiple entries for the same tile (different years)
            # Skip deduplication if we already filtered to a specific year
            if not target_year and ('tile_id' in intersecting.columns or 'KACHEL' in intersecting.columns):
                # Group by tile identifier
                tile_id_col = 'tile_id' if 'tile_id' in intersecting.columns else 'KACHEL'
                
                # Try to identify date/year column for sorting
                # Common column names: Aktualitaet (German for "currentness"), date, year, etc.
                date_cols = [c for c in intersecting.columns 
                           if any(x in c.lower() for x in ['date', 'jahr', 'year', 'aktualitaet', 'datum'])]
                
                if date_cols:
                    # Sort by date and keep most recent per tile
                    date_col = date_cols[0]
                    intersecting = intersecting.sort_values(date_col, ascending=False)
                    intersecting = intersecting.drop_duplicates(subset=[tile_id_col], keep='first')
                    logger.info(f"Filtered to {len(intersecting)} unique tiles (most recent year per location)")
                else:
                    logger.warning(f"No date column found for deduplication. Available columns: {intersecting.columns.tolist()}")
            
            # Extract tile information
            tiles = []
            for idx, row in intersecting.iterrows():
                tile_info = {
                    'geometry': row['geometry'],
                    'properties': row.to_dict()
                }
                # Remove geometry from properties to avoid duplication
                if 'geometry' in tile_info['properties']:
                    del tile_info['properties']['geometry']
                
                tiles.append(tile_info)
            
            return tiles
            
        except Exception as e:
            logger.error(f"Failed to load GeoJSON index: {e}")
            raise

    def get_tiles_from_atom_feed(
        self,
        area_polygon: Polygon,
        target_year: Optional[str] = None
    ) -> List[Dict[str, object]]:
        """
        Get tiles that intersect the area using an Atom feed index.
        
        Args:
            area_polygon: Area of interest in EPSG:25832
            target_year: Optional year filter (e.g., '2022'). If None, selects latest per tile.
        
        Returns:
            List of tile metadata dictionaries.
        """
        if not self.service.files_atom_feed_url:
            raise ValueError(
                f"Service {self.service.id} has no Atom feed URL defined"
            )
        
        feed_data = self._get_atom_feed_data(self.service.files_atom_feed_url)
        entries = feed_data['entries']
        tree = feed_data['tree']
        
        if not entries:
            logger.warning(f"No entries found in Atom feed for {self.service.id}")
            return []
        
        target_year_str = str(target_year) if target_year else None
        product_code = self.service.files_product_code
        
        # Candidate indices using spatial index if available
        if tree is not None:
            candidate_indices = tree.query(area_polygon)
        else:
            candidate_indices = range(len(entries))
        
        filtered: List[Dict[str, object]] = []
        for idx in candidate_indices:
            entry = entries[int(idx)]
            geometry: Polygon = entry['geometry']
            if not geometry.intersects(area_polygon):
                continue
            if product_code and entry.get('product') and entry['product'] != product_code:
                continue
            if target_year_str and entry.get('year') != target_year_str:
                continue
            filtered.append(entry)
        
        if target_year_str:
            return filtered
        
        # For 'latest', pick the newest year per tile key
        filtered.sort(
            key=lambda e: (
                e.get('year') or '',
                e.get('updated') or ''
            ),
            reverse=True
        )
        latest: Dict[str, Dict[str, object]] = {}
        for entry in filtered:
            key = entry.get('tile_key')
            if key and key not in latest:
                latest[key] = entry
        return list(latest.values())
    
    def verify_area_coverage(self, area_polygon: Polygon) -> dict:
        """
        Verify if the area has actual data coverage using WMS sampling.
        
        Uses the WMS service (if available) to test sample points for data availability.
        This is the same method used by ServiceDiscovery for coverage verification.
        
        Args:
            area_polygon: Area of interest in EPSG:25832
            
        Returns:
            Dict with coverage information:
            {
                'has_coverage': bool,
                'coverage_ratio': float,
                'coverage_category': str,  # 'full', 'high', 'partial', 'minimal'
                'tested_points': int
            }
        """
        if not self.service.has_wms():
            logger.warning(
                f"Service {self.service.id} has no WMS endpoint for coverage verification. "
                f"Assuming full coverage."
            )
            return {
                'has_coverage': True,
                'coverage_ratio': 1.0,
                'coverage_category': 'full',
                'tested_points': 0,
                'reason': 'No WMS available for verification'
            }
        
        # Check cache first if available
        if self.coverage_cache:
            cached = self.coverage_cache.get_coverage(self.service.id, area_polygon)
            if cached:
                logger.debug(f"Using cached coverage result for {self.service.id}")
                return cached
        
        # Import here to avoid circular dependency
        from orthophotos_downloader.wms_catalog.service_discovery import ServiceDiscovery
        
        # Use ServiceDiscovery's verification logic
        discovery = ServiceDiscovery(use_cache=False)  # We're managing cache ourselves
        
        result = discovery._verify_service_coverage(
            service=self.service,
            area_polygon=area_polygon
        )
        
        # Cache the result if we have a cache
        if self.coverage_cache:
            self.coverage_cache.set_coverage(self.service.id, area_polygon, result)
        
        logger.info(
            f"Coverage verification: {result['coverage_category']} "
            f"({result['coverage_ratio']:.1%}, {result['tested_points']} points)"
        )
        
        return result
    
    def build_tile_url(self, tile_x: int, tile_y: int) -> str:
        """
        Build download URL for a specific tile.
        
        Args:
            tile_x: Tile X coordinate in km
            tile_y: Tile Y coordinate in km
            
        Returns:
            Full URL to download the tile
        """
        filename = self.service.files_pattern.format(x=tile_x, y=tile_y)
        url = self.service.files_url.rstrip('/') + '/' + filename
        return url
    
    def _extract_zip_file(self, zip_file: Path, out_path: Path) -> Optional[Path]:
        """
        Extract a ZIP file and return the path to the extracted image file.
        Also parses HTML metadata files if present (Brandenburg format).
        
        Args:
            zip_file: Path to the ZIP file
            out_path: Directory to extract to
            
        Returns:
            Path to the extracted image file, or None if extraction failed
        """
        import zipfile
        import re
        from datetime import datetime
        
        try:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                # Find image files in the ZIP (prioritize TIF/TIFF, then JP2)
                image_extensions = {'.tif', '.tiff', '.jp2', '.jpg', '.jpeg', '.png'}
                image_files = [
                    name for name in zf.namelist() 
                    if Path(name).suffix.lower() in image_extensions
                ]
                
                if not image_files:
                    logger.warning(f"No image files found in ZIP: {zip_file.name}")
                    return None
                
                # Look for HTML metadata files (Brandenburg format)
                html_metadata = None
                for name in zf.namelist():
                    if name.lower().endswith('.html'):
                        try:
                            html_content = zf.read(name).decode('utf-8')
                            # Parse Brandenburg HTML metadata
                            # Look for "Bildflugdatum:" (flight date) and "Veröffentlichung:" (publication)
                            flight_date_match = re.search(r'Bildflugdatum:</td><td>\s*(\d{4}-\d{2}-\d{2})', html_content)
                            pub_date_match = re.search(r'Ver.*?ffentlichung:</td><td>\s*(\d{4}-\d{2}-\d{2})', html_content)
                            
                            if flight_date_match:
                                html_metadata = {
                                    'acquisition_date': flight_date_match.group(1),
                                    'publication_date': pub_date_match.group(1) if pub_date_match else None
                                }
                                logger.debug(f"Parsed HTML metadata: acquisition={html_metadata['acquisition_date']}")
                        except Exception as e:
                            logger.debug(f"Could not parse HTML metadata: {e}")
                
                # Extract all files
                extracted_paths = []
                for name in zf.namelist():
                    # Extract to the same directory as the ZIP file
                    extracted_path = out_path / Path(name).name
                    with open(extracted_path, 'wb') as f:
                        f.write(zf.read(name))
                    
                    # Track image files
                    if Path(name).suffix.lower() in image_extensions:
                        extracted_paths.append(extracted_path)
                
                # Store HTML metadata for later use in metadata extraction
                if html_metadata and extracted_paths:
                    # Store metadata temporarily indexed by filename
                    if not hasattr(self, '_html_metadata_cache'):
                        self._html_metadata_cache = {}
                    for img_path in extracted_paths:
                        self._html_metadata_cache[img_path.stem] = html_metadata
                
                # Delete the ZIP file after successful extraction
                zip_file.unlink()
                
                # Return the first image file (usually there's only one)
                if extracted_paths:
                    logger.debug(f"Extracted {len(extracted_paths)} file(s) from {zip_file.name}")
                    return extracted_paths[0]
                else:
                    logger.warning(f"No image files extracted from {zip_file.name}")
                    return None
                    
        except zipfile.BadZipFile:
            logger.error(f"Corrupted ZIP file: {zip_file.name}")
            return None
        except Exception as e:
            logger.error(f"Error extracting ZIP file {zip_file.name}: {e}")
            return None
    
    def download_tile(
        self,
        tile_x: int,
        tile_y: int,
        out_path: Path
    ) -> Optional[Path]:
        """
        Download a single tile.
        
        Args:
            tile_x: Tile X coordinate in km
            tile_y: Tile Y coordinate in km
            out_path: Output directory
            
        Returns:
            Path to downloaded file, or None if download failed
        """
        filename = self.service.files_pattern.format(x=tile_x, y=tile_y)
        
        # Handle wildcards in filename pattern (e.g., year wildcards)
        if '*' in filename:
            # Need to list directory and find matching file
            return self._download_tile_with_wildcard(tile_x, tile_y, out_path, filename)
        
        # Direct download without wildcards
        url = self.build_tile_url(tile_x, tile_y)
        output_file = out_path / filename
        
        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Write file
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.debug(f"Downloaded: {filename}")
            
            # Extract ZIP files if needed
            extracted_file = output_file
            if output_file.suffix.lower() == '.zip':
                extracted_file = self._extract_zip_file(output_file, out_path)
                if extracted_file is None:
                    logger.warning(f"Failed to extract ZIP file: {output_file}")
                    return None
            
            # Extract metadata if enabled
            if self.extract_metadata:
                self._extract_image_metadata(extracted_file)
            
            return extracted_file
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"Tile not available: {filename}")
            else:
                logger.warning(f"HTTP error downloading {filename}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading {filename}: {e}")
            return None
    
    def _download_tile_with_wildcard(
        self,
        tile_x: int,
        tile_y: int,
        out_path: Path,
        pattern: str
    ) -> Optional[Path]:
        """
        Download a tile when the filename contains wildcards.
        
        This method lists the directory and finds files matching the pattern.
        Supports both XML directory listings (OpenGeoData NRW) and HTML listings.
        
        Args:
            tile_x: Tile X coordinate in km
            tile_y: Tile Y coordinate in km
            out_path: Output directory
            pattern: Filename pattern with wildcards
            
        Returns:
            Path to downloaded file, or None if not found
        """
        import re
        import xml.etree.ElementTree as ET
        
        # Convert glob pattern to regex
        # Escape special chars except *, then replace * with .*
        regex_pattern = re.escape(pattern).replace(r'\*', '.*')
        regex = re.compile(regex_pattern)
        
        base_url = self.service.files_url.rstrip('/')
        
        try:
            # List directory contents
            response = requests.get(base_url + '/', timeout=30)
            response.raise_for_status()
            
            filenames = []
            
            # Try parsing as XML first (OpenGeoData NRW format)
            if response.text.strip().startswith('<?xml'):
                try:
                    root = ET.fromstring(response.text)
                    # Find all <file name="..." /> elements
                    for file_elem in root.findall('.//file'):
                        name = file_elem.get('name')
                        if name:
                            filenames.append(name)
                    logger.debug(f"Parsed XML directory listing: found {len(filenames)} files")
                except ET.ParseError as e:
                    logger.warning(f"Failed to parse XML directory listing: {e}")
            
            # Fallback to HTML parsing if no files found or not XML
            if not filenames:
                # Extract filenames from HTML using regex
                # Look for href="filename" patterns
                href_pattern = re.compile(r'href=["\']([^"\']+)["\']')
                for match in href_pattern.finditer(response.text):
                    href = match.group(1)
                    # Skip parent directory links and absolute URLs
                    if not href.startswith(('..', '/', 'http://', 'https://', '?')):
                        filenames.append(href)
                logger.debug(f"Parsed HTML directory listing: found {len(filenames)} potential files")
            
            # Find matching files
            for filename in filenames:
                if regex.match(filename):
                    # Found matching file
                    file_url = base_url + '/' + filename
                    output_file = out_path / filename
                    
                    # Download the file
                    try:
                        file_response = requests.get(file_url, timeout=30, stream=True)
                        file_response.raise_for_status()
                        
                        with open(output_file, 'wb') as f:
                            for chunk in file_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        logger.debug(f"Downloaded: {filename} (matched pattern: {pattern})")
                        
                        # Extract ZIP files if needed
                        extracted_file = output_file
                        if output_file.suffix.lower() == '.zip':
                            extracted_file = self._extract_zip_file(output_file, out_path)
                            if extracted_file is None:
                                logger.warning(f"Failed to extract ZIP file: {output_file}")
                                continue
                        
                        # Extract metadata if enabled
                        if self.extract_metadata:
                            self._extract_image_metadata(extracted_file)
                        
                        return extracted_file
                    except Exception as e:
                        logger.warning(f"Error downloading {filename}: {e}")
                        continue
            
            # No matching file found
            logger.debug(f"No file matching pattern: {pattern}")
            return None
            
        except Exception as e:
            logger.error(f"Error listing directory for pattern {pattern}: {e}")
            return None
    
    def download_tile_from_geojson(
        self,
        tile_info: dict,
        out_path: Path
    ) -> Optional[Path]:
        """
        Download a single tile using information from GeoJSON index.
        
        Args:
            tile_info: Tile information dict from GeoJSON with 'properties' containing URL
            out_path: Output directory
            
        Returns:
            Path to downloaded file, or None if download failed
        """
        try:
            properties = tile_info['properties']
            
            # Try to find the download URL in properties
            # Common property names: 'rgb', 'rgbi', 'url', 'download_url', etc.
            url = None
            url_candidates = ['rgb', 'rgbi', 'url', 'download_url', 'file_url', 'href']
            
            for key in url_candidates:
                if key in properties and properties[key]:
                    url = properties[key]
                    break
            
            if not url:
                logger.warning(f"No download URL found in tile properties: {list(properties.keys())}")
                return None
            
            # Extract filename from URL
            filename = url.split('/')[-1]
            output_file = out_path / filename
            
            # Skip if already downloaded
            if output_file.exists():
                logger.debug(f"File already exists: {filename}")
                return output_file
            
            # Download the file
            logger.debug(f"Downloading: {url}")
            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()
            
            # Write file
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
                logger.debug(f"Downloaded: {filename}")
            return output_file
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"Tile not available: {url}")
            else:
                logger.warning(f"HTTP error downloading from {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading tile: {e}")
            return None
    
    def download_tile_from_atom(
        self,
        tile_info: Dict[str, object],
        out_path: Path
    ) -> Optional[Path]:
        """
        Download a single tile using Atom feed metadata.
        
        Args:
            tile_info: Tile metadata dictionary returned by get_tiles_from_atom_feed
            out_path: Output directory
        
        Returns:
            Path to the downloaded file, or None if download failed.
        """
        tile_feed_url = tile_info.get('tile_feed_url')
        tile_meta: Dict[str, str] = {}
        download_url = tile_info.get('download_url')
        if not download_url:
            if not tile_feed_url:
                logger.warning("Atom tile entry missing download information")
                return None
            try:
                tile_meta = self._resolve_atom_tile(tile_feed_url)
                download_url = tile_meta.get('download_url')
            except Exception as exc:
                logger.error(f"Failed to resolve Atom tile feed {tile_feed_url}: {exc}")
                return None
        
        if not download_url:
            logger.warning("Atom tile resolution returned no download URL")
            return None
        
        download_url = self._adjust_wcs_resolution(download_url)
        
        filename_base = tile_info.get('code') or tile_meta.get('title') or 'tile'
        extension = self.service.files_default_extension or 'tif'
        if extension and not extension.startswith('.'):
            extension = f'.{extension}'
        if extension and not filename_base.lower().endswith(extension.lower()):
            filename = f"{filename_base}{extension}"
        else:
            filename = filename_base
        
        output_file = out_path / filename
        if output_file.exists():
            logger.debug(f"File already exists: {filename}")
            return output_file
        
        logger.debug(f"Downloading Atom tile: {download_url}")
        try:
            response = requests.get(download_url, stream=True, timeout=180)
            response.raise_for_status()
            with open(output_file, 'wb') as dst:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        dst.write(chunk)
            logger.debug(f"Downloaded Atom tile: {filename}")
            
            extra_metadata: Dict[str, object] = {}
            acquisition_date = tile_info.get('acquisition_date')
            if acquisition_date:
                extra_metadata['acquisition_date'] = acquisition_date
                extra_metadata['date_source'] = 'atom_feed_summary'
            if tile_info.get('summary'):
                extra_metadata['atom_summary'] = tile_info['summary']
            effective_title = tile_meta.get('title') if tile_meta else tile_info.get('title')
            if effective_title:
                extra_metadata['atom_title'] = effective_title
            if extra_metadata and self.extract_metadata:
                self._atom_extra_metadata[output_file.resolve()] = extra_metadata
            
            return output_file
        except Exception as exc:
            logger.error(f"Error downloading Atom tile {download_url}: {exc}")
            if output_file.exists():
                output_file.unlink(missing_ok=True)
            return None

    def download_tile_from_wcs(
        self,
        tile_x: int,
        tile_y: int,
        out_path: Path
    ) -> Optional[Path]:
        """Download a single tile using WCS GetCoverage."""
        if not self.service.files_wcs_url or not self.service.files_wcs_coverage:
            raise ValueError(
                f"Service {self.service.id} is missing WCS configuration"
            )

        grid_size = self.service.files_grid_size or self.grid_spacing
        minx = tile_x * 1000
        miny = tile_y * 1000
        maxx = minx + grid_size
        maxy = miny + grid_size

        resolution = self.service.resolution or (grid_size / 2500)
        width_px = int(round(grid_size / resolution))
        height_px = int(round(grid_size / resolution))
        max_px = self.files_wcs_max_pixels or 4000

        extension = self.service.files_default_extension or 'tif'
        if extension.startswith('.'):
            extension = extension[1:]
        filename = f"{self.service.id}_{tile_x}_{tile_y}.{extension}"
        output_file = out_path / filename
        if output_file.exists():
            logger.debug(f"WCS file already exists: {filename}")
            return output_file

        bbox = (minx, miny, maxx, maxy)

        if width_px <= max_px and height_px <= max_px:
            return self._download_wcs_request(bbox, width_px, height_px, output_file)

        splits_x = math.ceil(width_px / max_px)
        splits_y = math.ceil(height_px / max_px)
        sub_width_m = grid_size / splits_x
        sub_height_m = grid_size / splits_y
        sub_width_px = int(round(sub_width_m / resolution))
        sub_height_px = int(round(sub_height_m / resolution))

        subfiles = []
        try:
            for ix in range(splits_x):
                for iy in range(splits_y):
                    sub_minx = minx + ix * sub_width_m
                    sub_maxx = min(sub_minx + sub_width_m, maxx)
                    sub_miny = miny + iy * sub_height_m
                    sub_maxy = min(sub_miny + sub_height_m, maxy)
                    sub_bbox = (sub_minx, sub_miny, sub_maxx, sub_maxy)
                    sub_path = output_file.with_name(
                        f"{output_file.stem}_sub_{ix}_{iy}.{extension}"
                    )
                    result = self._download_wcs_request(
                        sub_bbox,
                        sub_width_px,
                        sub_height_px,
                        sub_path
                    )
                    if not result:
                        logger.error(
                            f"Failed to download WCS subtile ({ix}, {iy}) for {self.service.id}"
                        )
                        raise RuntimeError("Missing WCS subtile")
                    subfiles.append(sub_path)

            if not subfiles:
                return None

            if len(subfiles) == 1:
                subfiles[0].rename(output_file)
            else:
                import rasterio
                from rasterio.merge import merge

                datasets = [rasterio.open(path) for path in subfiles]
                try:
                    mosaic, transform = merge(datasets)
                    profile = datasets[0].profile
                    profile.update(
                        height=mosaic.shape[1],
                        width=mosaic.shape[2],
                        transform=transform,
                    )
                    with rasterio.open(output_file, "w", **profile) as dst:
                        dst.write(mosaic)
                finally:
                    for ds in datasets:
                        ds.close()
                for path in subfiles:
                    path.unlink(missing_ok=True)

            return output_file
        except Exception as exc:
            logger.error(f"Error mosaicking WCS tiles for {self.service.id}: {exc}")
            if output_file.exists():
                output_file.unlink(missing_ok=True)
            for path in subfiles:
                path.unlink(missing_ok=True)
            return None

    def _download_wcs_request(
        self,
        bbox: Tuple[float, float, float, float],
        width_px: int,
        height_px: int,
        dest_path: Path
    ) -> Optional[Path]:
        """Download a single WCS request for the given bbox."""
        if not self.service.files_wcs_url or not self.service.files_wcs_coverage:
            return None

        minx, miny, maxx, maxy = bbox
        base_url = self.service.files_wcs_url.rstrip('?')
        query_params = (
            f"SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage"
            f"&COVERAGE={self.service.files_wcs_coverage}"
            f"&FORMAT={self.service.files_wcs_format}"
            f"&BBOX={minx},{miny},{maxx},{maxy}"
            f"&WIDTH={width_px}&HEIGHT={height_px}"
            f"&CRS={self.service.files_crs}"
        )

        wcs_url = f"{base_url}?{query_params}"
        wcs_url = self._adjust_wcs_resolution(wcs_url)

        logger.debug(f"Downloading WCS tile: {wcs_url}")
        try:
            response = requests.get(wcs_url, stream=True, timeout=180)
            response.raise_for_status()
            with open(dest_path, 'wb') as dst:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        dst.write(chunk)
            return dest_path
        except Exception as exc:
            logger.error(f"Error downloading WCS tile {wcs_url}: {exc}")
            if dest_path.exists():
                dest_path.unlink(missing_ok=True)
            return None

    def download_images_from_polygon(
        self,
        area_name: str,
        area_polygon,
        out_path: Path,
        filename_prefix: Optional[str] = None,
        mask=None,
        buffer_size: int = 0
    ) -> AreaDataset:
        """
        Download all tiles covering the given polygon.
        
        Args:
            area_name: Name for this area
            area_polygon: GeoSeries or Polygon defining area
            out_path: Output directory
            filename_prefix: Prefix for output files (not used, files keep original names)
            mask: Optional mask (not yet implemented)
            buffer_size: Buffer around area (not yet implemented)
            
        Returns:
            AreaDataset with downloaded images
        """
        # Convert GeoSeries to Polygon if needed
        if hasattr(area_polygon, 'unary_union'):
            polygon = area_polygon.unary_union
        elif hasattr(area_polygon, 'iloc'):
            polygon = area_polygon.iloc[0]
        else:
            polygon = area_polygon
        
        # Ensure output directory exists
        out_path = Path(out_path)
        out_path.mkdir(parents=True, exist_ok=True)
        
        # Verify coverage if requested
        if self.verify_coverage:
            logger.info(f"Verifying coverage for {area_name}...")
            coverage_result = self.verify_area_coverage(polygon)
            
            if not coverage_result['has_coverage']:
                logger.warning(
                    f"Area {area_name} has insufficient coverage "
                    f"({coverage_result['coverage_ratio']:.1%}). Skipping download."
                )
                # Return empty dataset
                result = AreaDataset(area_name, polygon, buffer_size, out_path)
                result.images = []
                return result
            
            logger.info(
                f"Coverage verified: {coverage_result['coverage_category']} "
                f"({coverage_result['coverage_ratio']:.1%})"
            )
        
        # Extract year from service for historic downloads
        # Service year can be: 'latest', 'current', '2015', '2012-2025', etc.
        target_year: Optional[str] = None
        if self.service.year and self.service.year not in ['latest', 'current']:
            year_str = str(self.service.year)
            if '-' not in year_str and year_str.isdigit():
                target_year = year_str
        
        # Determine download method based on service type
        if self.service.files_index_type == 'geojson':
            # Use GeoJSON-based download
            logger.info(f"Using GeoJSON-based tile discovery for {self.service.id}")
            if target_year:
                logger.info(f"Filtering GeoJSON for specific year: {target_year}")
            
            tiles = self.get_tiles_from_geojson_index(polygon, target_year=target_year)
            
            logger.info(f"Downloading {len(tiles)} tiles for {area_name}...")
            
            # Download tiles in parallel
            downloaded_files = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.download_tile_from_geojson, tile_info, out_path): i
                    for i, tile_info in enumerate(tiles)
                }
                
                for future in as_completed(futures):
                    tile_idx = futures[future]
                    try:
                        result = future.result()
                        if result:
                            downloaded_files.append(result)
                    except Exception as e:
                        logger.error(f"Error processing tile {tile_idx}: {e}")
        elif self.service.files_index_type == 'atom':
            logger.info(f"Using Atom feed tile discovery for {self.service.id}")
            if target_year:
                logger.info(f"Filtering Atom feed for specific year: {target_year}")
            
            tiles = self.get_tiles_from_atom_feed(polygon, target_year=target_year)
            
            if not tiles and target_year:
                logger.info("No tiles found for requested year, trying without year filter")
                tiles = self.get_tiles_from_atom_feed(polygon, target_year=None)
            
            logger.info(f"Downloading {len(tiles)} tiles for {area_name}...")
            
            downloaded_files = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.download_tile_from_atom, tile_info, out_path): i
                    for i, tile_info in enumerate(tiles)
                }
                
                for future in as_completed(futures):
                    tile_idx = futures[future]
                    try:
                        result = future.result()
                        if result:
                            downloaded_files.append(result)
                    except Exception as e:
                        logger.error(f"Error processing Atom tile {tile_idx}: {e}")
        elif self.service.files_index_type == 'wcs':
            logger.info(f"Using WCS-based tile downloading for {self.service.id}")
            tiles = self.calculate_required_tiles(polygon)
            logger.info(f"Downloading {len(tiles)} tiles for {area_name}...")

            downloaded_files = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.download_tile_from_wcs, tile_x, tile_y, out_path): (tile_x, tile_y)
                    for tile_x, tile_y in tiles
                }

                for future in as_completed(futures):
                    tile_x, tile_y = futures[future]
                    try:
                        result = future.result()
                        if result:
                            downloaded_files.append(result)
                    except Exception as e:
                        logger.error(f"Error processing WCS tile ({tile_x}, {tile_y}): {e}")
        else:
            # Use grid-based download
            logger.info(f"Using grid-based tile discovery for {self.service.id}")
            tiles = self.calculate_required_tiles(polygon)
            
            logger.info(f"Downloading {len(tiles)} tiles for {area_name}...")
            
            # Download tiles in parallel
            downloaded_files = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.download_tile, tile_x, tile_y, out_path): (tile_x, tile_y)
                    for tile_x, tile_y in tiles
                }
                
                for future in as_completed(futures):
                    tile_x, tile_y = futures[future]
                try:
                    result = future.result()
                    if result:
                        downloaded_files.append(result)
                except Exception as e:
                    logger.error(f"Error processing tile ({tile_x}, {tile_y}): {e}")
        
        logger.info(f"Downloaded {len(downloaded_files)}/{len(tiles)} tiles successfully")
        
        # Create AreaDataset using positional args: (name, polygon, buffer_size, out_path)
        result = AreaDataset(area_name, polygon, buffer_size, out_path)
        
        # Add images with metadata extraction if enabled
        result.images = []
        for file_path in downloaded_files:
            if self.extract_metadata:
                # Extract metadata from the downloaded file
                extra_metadata = None
                if self.service.files_index_type == 'atom':
                    extra_metadata = self._atom_extra_metadata.pop(file_path.resolve(), None)
                image = self._extract_image_metadata(file_path, extra_metadata=extra_metadata)
            else:
                # Create simple Image instance with minimal metadata
                # For GeoJSON-indexed services, grid_size might be None
                grid_size = self.service.files_grid_size if self.service.files_grid_size else 0
                image = Image(
                    image_path=file_path,
                    mask_path=None,
                    upper_left_x=0.0,
                    upper_left_y=0.0,
                    download_time=0.0,
                    width_m=grid_size,
                    height_m=grid_size,
                    width_px=0,
                    height_px=0,
                    resolution_m=self.service.resolution,
                    crs=self.service.files_crs
                )
            result.images.append(image)
        
        return result
    
    def _extract_image_metadata(
        self,
        file_path: Path,
        extra_metadata: Optional[Dict[str, object]] = None
    ) -> Image:
        """
        Extract metadata from a downloaded image file.
        
        Args:
            file_path: Path to the downloaded image file
            extra_metadata: Optional metadata to merge (e.g., from Atom feeds)
            
        Returns:
            Image object with extracted metadata
        """
        try:
            import rasterio
            
            with rasterio.open(file_path) as src:
                # Get spatial information
                bounds = src.bounds
                transform = src.transform
                
                # Get pixel dimensions
                width_px = src.width
                height_px = src.height
                
                # Get CRS
                crs = str(src.crs) if src.crs else self.service.files_crs
                
                # Calculate upper left corner
                upper_left_x = transform.c
                upper_left_y = transform.f
                
                # Calculate width and height in meters
                width_m = abs(bounds.right - bounds.left)
                height_m = abs(bounds.top - bounds.bottom)
                
                # Calculate resolution
                resolution_m = abs(transform.a)  # Pixel width in meters
                
                # Create STAC metadata if generator is available
                if self.stac_generator:
                    try:
                        # Check for HTML metadata from ZIP extraction (Brandenburg)
                        html_metadata = None
                        if hasattr(self, '_html_metadata_cache'):
                            html_metadata = self._html_metadata_cache.get(file_path.stem)
                        
                        # Load official metadata if available
                        metadata_csv = self._load_metadata_csv()
                        official_metadata = None
                        
                        if metadata_csv:
                            # Extract tile name from filename (without extension)
                            tile_name = file_path.stem
                            official_metadata = metadata_csv.get(tile_name)
                        
                        # Determine acquisition date
                        acquisition_date = None
                        
                        # Priority 1: HTML metadata from ZIP (Brandenburg)
                        if html_metadata and html_metadata.get('acquisition_date'):
                            acquisition_date = html_metadata['acquisition_date']
                            logger.debug(f"Using HTML acquisition date: {acquisition_date}")
                        # Priority 2: CSV metadata
                        elif official_metadata and self.service.files_metadata.get('date_column'):
                            # Use official acquisition date from metadata
                            date_str = official_metadata.get(self.service.files_metadata['date_column'])
                            if date_str:
                                try:
                                    # Parse date and format as YYYY-MM-DD
                                    from datetime import datetime
                                    parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                                    acquisition_date = date_str  # Already in correct format
                                    logger.debug(f"Using official acquisition date: {date_str}")
                                except ValueError:
                                    logger.warning(f"Could not parse date '{date_str}' from metadata")
                        
                        # Fallback: extract from filename or use service year
                        if not acquisition_date:
                            if self.service.year and self.service.year not in ['latest', 'current']:
                                # Use the service year for acquisition date
                                acquisition_date = f"{self.service.year}-01-01"
                            else:
                                # For 'latest' or 'current', try to extract year from filename
                                # Filename pattern: dop10rgbi_32_350_5641_1_nw_2023.jp2
                                import re
                                year_match = re.search(r'_(\d{4})\.', file_path.name)
                                if year_match:
                                    acquisition_date = f"{year_match.group(1)}-01-01"
                                else:
                                    # Default to None, will be handled by STAC generator
                                    acquisition_date = None
                        
                        # Prepare metadata dict for STAC generation
                        metadata = {
                            'bounds': bounds,
                            'crs': crs,
                            'resolution': resolution_m,
                            'width_px': width_px,
                            'height_px': height_px,
                            'service_id': self.service.id,
                            'service_type': self.service.type,
                            'year': self.service.year,
                            'state_code': self.service.state_code,
                            'state_name': self.service.state_name,
                            'acquisition_date': acquisition_date,
                        }
                        
                        # Add official metadata fields if available
                        if official_metadata:
                            if self.service.files_metadata.get('flight_column'):
                                flight_num = official_metadata.get(self.service.files_metadata['flight_column'])
                                if flight_num:
                                    metadata['flight_number'] = flight_num
                            
                            if self.service.files_metadata.get('sensor_column'):
                                sensor = official_metadata.get(self.service.files_metadata['sensor_column'])
                                if sensor:
                                    metadata['sensor'] = sensor
                            
                            if self.service.files_metadata.get('vegetation_column'):
                                vegetation = official_metadata.get(self.service.files_metadata['vegetation_column'])
                                if vegetation:
                                    metadata['vegetation_state'] = vegetation
                        
                        # Generate item ID from filename
                        item_id = file_path.stem
                        
                        if extra_metadata:
                            for key, value in extra_metadata.items():
                                if value is not None:
                                    metadata[key] = value
                        
                        # Create and save STAC item
                        self.stac_generator.create_and_save_stac_item(
                            tile_path=file_path,
                            metadata=metadata,
                            item_id=item_id
                        )
                        logger.debug(f"Created STAC item for {file_path.name}")
                    except Exception as e:
                        logger.warning(f"Failed to create STAC item for {file_path}: {e}")
                
                return Image(
                    image_path=file_path,
                    mask_path=None,
                    upper_left_x=upper_left_x,
                    upper_left_y=upper_left_y,
                    download_time=0.0,
                    width_m=width_m,
                    height_m=height_m,
                    width_px=width_px,
                    height_px=height_px,
                    resolution_m=resolution_m,
                    crs=crs
                )
        except Exception as e:
            logger.warning(f"Failed to extract metadata from {file_path}: {e}")
            # Fallback to basic metadata
            return Image(
                image_path=file_path,
                mask_path=None,
                upper_left_x=0.0,
                upper_left_y=0.0,
                download_time=0.0,
                width_m=self.service.files_grid_size,
                height_m=self.service.files_grid_size,
                width_px=0,
                height_px=0,
                resolution_m=self.service.resolution,
                crs=self.service.files_crs
            )

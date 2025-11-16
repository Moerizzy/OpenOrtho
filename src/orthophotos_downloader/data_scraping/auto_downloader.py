"""
Automatic WMS downloader that detects which services are needed for a given area
and orchestrates downloads across multiple WMS services.

Uses the centralized WMS catalog (wms_services.yaml) and generic WMSServiceDownloader.
"""

import geopandas as gpd
import logging
from typing import List, Dict, Optional, Union, Tuple
from pathlib import Path
from shapely.geometry import Polygon
from geopandas import GeoDataFrame, GeoSeries

from orthophotos_downloader.data_scraping.image_download import (
    ImageDownloader,
    AreaDataset,
)
from orthophotos_downloader.data_scraping.generic_downloader import WMSServiceDownloader
from orthophotos_downloader.data_scraping.file_downloader import FileServiceDownloader
from orthophotos_downloader.wms_catalog import WMSCatalogManager
from orthophotos_downloader.wms_catalog.catalog_manager import WMSService

logger = logging.getLogger(__name__)


class AutoOrthophotoDownloader:
    """
    Automatically detects which WMS services are needed for a given area
    and downloads orthophotos from all relevant services.
    
    Uses the centralized WMS catalog for service discovery.
    """

    def __init__(
        self,
        grid_spacing: int,
        german_states_url: Optional[str] = None,
        extract_metadata: bool = False,
        year: Union[str, int, None] = None,
        delivery_method: str = 'auto',
        max_workers: int = 4
    ):
        """
        Initialize the automatic orthophoto downloader.

        Args:
            grid_spacing: The grid spacing in meters for image downloads.
            german_states_url: URL to German federal states GeoJSON. If None, uses default.
            extract_metadata: Whether to extract metadata and create STAC items for downloaded tiles.
            year: Specific year to download (e.g., 2023, '2021', 'latest'). If None, uses 'latest'.
            delivery_method: How to download data:
                - 'auto': Prefer files if available, fallback to WMS
                - 'files': Force direct file downloads (error if not available)
                - 'wms': Force WMS downloads (error if not available)
            max_workers: Maximum number of parallel download threads (default: 4).
                Higher values can speed up downloads but may overload the server.
        """
        self.grid_spacing = grid_spacing
        self.german_states_url = (
            german_states_url
            or "https://raw.githubusercontent.com/isellsoap/deutschlandGeoJSON/main/2_bundeslaender/4_niedrig.geo.json"
        )
        self.extract_metadata = extract_metadata
        self.year = str(year) if year is not None else 'latest'
        self.delivery_method = delivery_method
        self.max_workers = max_workers
        self._states_gdf = None
        self._catalog = WMSCatalogManager()  # Initialize WMS catalog
        
        # Validate delivery method
        if delivery_method not in ['auto', 'files', 'wms']:
            raise ValueError(
                f"Invalid delivery_method '{delivery_method}'. "
                f"Must be 'auto', 'files', or 'wms'"
            )

    def _load_german_states(self) -> GeoDataFrame:
        """Load German federal states geometry data."""
        if self._states_gdf is None:
            logger.info(f"Loading German federal states from {self.german_states_url}")
            self._states_gdf = gpd.read_file(self.german_states_url).to_crs(
                "EPSG:25832"
            )
        return self._states_gdf

    def detect_intersecting_states(
        self, area_polygon: Union[GeoSeries, GeoDataFrame, Polygon]
    ) -> List[Tuple[str, str, Polygon]]:
        """
        Detect which German federal states intersect with the given area.

        Args:
            area_polygon: The area of interest as GeoSeries, GeoDataFrame, or Shapely Polygon.

        Returns:
            List of tuples containing (state_name, state_code, intersection_geometry)
        """
        # Convert input to GeoDataFrame if needed
        if isinstance(area_polygon, Polygon):
            area_gdf = gpd.GeoDataFrame([1], geometry=[area_polygon], crs="EPSG:25832")
        elif isinstance(area_polygon, GeoSeries):
            area_gdf = gpd.GeoDataFrame(
                [1], geometry=[area_polygon.unary_union], crs=area_polygon.crs
            )
        elif isinstance(area_polygon, GeoDataFrame):
            area_gdf = area_polygon.copy()
        else:
            raise ValueError(
                "area_polygon must be a Polygon, GeoSeries, or GeoDataFrame"
            )

        # Ensure CRS compatibility
        if area_gdf.crs != "EPSG:25832":
            area_gdf = area_gdf.to_crs("EPSG:25832")

        # Load German states
        states_gdf = self._load_german_states()

        # Find intersecting states
        intersecting_states = []
        area_geom = area_gdf.unary_union

        for _, state_row in states_gdf.iterrows():
            state_geom = state_row.geometry
            if area_geom.intersects(state_geom):
                intersection = area_geom.intersection(state_geom)
                if not intersection.is_empty:
                    state_name = state_row["name"]
                    state_code = state_row["id"].split("-")[
                        -1
                    ]  # Extract code like "BY" from "DE-BY"
                    intersecting_states.append((state_name, state_code, intersection))

        logger.info(
            f"Found {len(intersecting_states)} intersecting states: {[s[0] for s in intersecting_states]}"
        )
        return intersecting_states

    def _get_downloader_class(self, state_code: str, image_type: str) -> Tuple[type, WMSService]:
        """
        Get the appropriate downloader class and service for a state and image type.

        Args:
            state_code: The federal state code (e.g., "BY", "BW")
            image_type: "RGB", "CIR", or "RGBI"

        Returns:
            Tuple of (downloader class, service)
        """
        if image_type not in ["RGB", "CIR", "RGBI"]:
            raise ValueError("image_type must be 'RGB', 'CIR', or 'RGBI'")

        # Query catalog for matching service with year filter
        services = self._catalog.filter_services(
            state_code=state_code,
            image_type=image_type,
            year=self.year
        )
        
        if not services:
            raise ValueError(
                f"No {image_type} service available for state {state_code}, year {self.year} in catalog.\n"
                f"  • Try using year='latest' for current orthophotos\n"
                f"  • Use ServiceDiscovery.get_available_years() to check available years\n"
                f"  • Run: python scripts/discover_services.py --bbox 'minx,miny,maxx,maxy' --list-years"
            )
        
        # Reorder services based on desired delivery method
        preferred_services = services
        if self.delivery_method == 'files':
            file_services = [s for s in services if s.has_files()]
            if file_services:
                preferred_services = file_services
        elif self.delivery_method == 'wms':
            wms_services = [s for s in services if s.has_wms()]
            if wms_services:
                preferred_services = wms_services
        else:  # auto
            file_services = [s for s in services if s.has_files()]
            if file_services:
                preferred_services = file_services
        
        # Use the first matching service after preference ordering
        service = preferred_services[0]
        
        logger.info(f"Using service: {service.id} (year: {service.year}, layer: {service.layer_name})")
        
        # Determine which downloader to use based on delivery_method
        downloader_class = self._choose_downloader_class(service)
        
        return downloader_class, service
    
    def _choose_downloader_class(self, service: WMSService) -> type:
        """
        Choose the appropriate downloader class based on delivery_method and service capabilities.
        
        Args:
            service: WMSService object
            
        Returns:
            Downloader class (WMSServiceDownloader or FileServiceDownloader)
        """
        if self.delivery_method == 'files':
            # Force file delivery
            if not service.has_files():
                raise ValueError(
                    f"Service {service.id} does not support file delivery.\n"
                    f"  Available methods: {service.get_delivery_methods()}\n"
                    f"  Try delivery_method='wms' or 'auto'"
                )
            logger.info(f"Using FileServiceDownloader for {service.id}")
            return FileServiceDownloader
            
        elif self.delivery_method == 'wms':
            # Force WMS delivery
            if not service.has_wms():
                raise ValueError(
                    f"Service {service.id} does not support WMS delivery.\n"
                    f"  Available methods: {service.get_delivery_methods()}\n"
                    f"  Try delivery_method='files' or 'auto'"
                )
            logger.info(f"Using WMSServiceDownloader for {service.id}")
            return WMSServiceDownloader
            
        else:  # 'auto'
            # Prefer files if available, fallback to WMS
            if service.has_files():
                logger.info(f"Auto-selecting FileServiceDownloader for {service.id} (files available)")
                return FileServiceDownloader
            elif service.has_wms():
                logger.info(f"Auto-selecting WMSServiceDownloader for {service.id} (WMS only)")
                return WMSServiceDownloader
            else:
                raise ValueError(
                    f"Service {service.id} has no delivery methods available!\n"
                    f"  This is a catalog configuration error."
                )

    def _instantiate_downloader(
        self,
        downloader_class: type,
        service: WMSService,
        layer_override: Optional[str] = None
    ):
        """
        Instantiate a downloader with consistent parameters, including max_workers support.

        Args:
            downloader_class: Downloader class to instantiate.
            service: Service configuration to bind to the downloader.
            layer_override: Optional override for the service's layer name.

        Returns:
            An initialized downloader instance.
        """
        if downloader_class == WMSServiceDownloader:
            return downloader_class(
                service=service,
                grid_spacing=self.grid_spacing,
                extract_metadata=self.extract_metadata,
                layer_name_override=layer_override,
                max_workers=self.max_workers
            )
        elif downloader_class == FileServiceDownloader:
            return downloader_class(
                service=service,
                grid_spacing=self.grid_spacing,
                extract_metadata=self.extract_metadata,
                max_workers=self.max_workers
            )
        else:
            # Fallback for custom downloaders that follow the same signature
            return downloader_class(
                service=service,
                grid_spacing=self.grid_spacing,
                extract_metadata=self.extract_metadata,
                max_workers=self.max_workers
            )

    def download_images_auto(
        self,
        area_name: str,
        area_polygon: Union[GeoSeries, GeoDataFrame, Polygon],
        out_path: Path,
        image_type: str = "RGB",
        filename_prefix: Optional[str] = None,
        mask: Optional[Union[GeoSeries, GeoDataFrame]] = None,
        buffer_size: int = 0,
    ) -> Dict[str, AreaDataset]:
        """
        Automatically download orthophotos for an area that may span multiple federal states.

        Args:
            area_name: Name of the area for identification
            area_polygon: The area of interest
            out_path: Output path where images will be saved
            image_type: "RGB" or "CIR"
            filename_prefix: Optional prefix for filenames
            mask: Optional mask to limit downloads to specific areas
            buffer_size: Buffer size around the area

        Returns:
            Dictionary mapping state names to their AreaDataset results
        """
        # Detect intersecting states
        intersecting_states = self.detect_intersecting_states(area_polygon)

        if not intersecting_states:
            raise ValueError("No German federal states intersect with the given area")

        results = {}

        for state_name, state_code, intersection_geom in intersecting_states:
            logger.info(f"Processing {state_name} ({state_code})...")

            try:
                # Get the appropriate downloader class and service info
                downloader_class, service = self._get_downloader_class(state_code, image_type)

                # Determine layer name override for historic or fixed-year services
                layer_override = (
                    service.layer_name
                    if service.year not in ['latest', 'current']
                    else None
                )
                if layer_override:
                    logger.info(f"Using layer {layer_override} for year {service.year}")

                # Instantiate the downloader with consistent parameters
                downloader = self._instantiate_downloader(
                    downloader_class=downloader_class,
                    service=service,
                    layer_override=layer_override
                )

                # Create GeoSeries for the intersection
                intersection_gs = gpd.GeoSeries([intersection_geom], crs="EPSG:25832")

                # Create state-specific output directory
                state_out_path = out_path / f"{state_name.replace('/', '_')}"
                state_out_path.mkdir(parents=True, exist_ok=True)

                # Download images for this state's portion
                # Use the filename_prefix if provided, otherwise use image_type with year
                if filename_prefix:
                    file_prefix = filename_prefix
                else:
                    file_prefix = f"{image_type}_{service.year}"

                result = downloader.download_images_from_polygon(
                    area_name=f"{area_name}_{state_name}",
                    area_polygon=intersection_gs,
                    out_path=state_out_path,
                    filename_prefix=file_prefix,
                    mask=mask,
                    buffer_size=buffer_size,
                )

                results[state_name] = result
                logger.info(f"✅ {state_name}: {len(result.images)} images downloaded")

            except Exception as e:
                logger.error(
                    f"❌ Failed to download from {state_name} ({state_code}): {e}"
                )
                continue

        return results

    def download_rgb_images_auto(
        self,
        area_name: str,
        area_polygon: Union[GeoSeries, GeoDataFrame, Polygon],
        out_path: Path,
        filename_prefix: Optional[str] = None,
        mask: Optional[Union[GeoSeries, GeoDataFrame]] = None,
        buffer_size: int = 0,
    ) -> Dict[str, AreaDataset]:
        """
        Automatically download RGB orthophotos for an area that may span multiple federal states.
        """
        return self.download_images_auto(
            area_name=area_name,
            area_polygon=area_polygon,
            out_path=out_path,
            image_type="RGB",
            filename_prefix=filename_prefix,
            mask=mask,
            buffer_size=buffer_size,
        )

    def download_cir_images_auto(
        self,
        area_name: str,
        area_polygon: Union[GeoSeries, GeoDataFrame, Polygon],
        out_path: Path,
        filename_prefix: Optional[str] = None,
        mask: Optional[Union[GeoSeries, GeoDataFrame]] = None,
        buffer_size: int = 0,
    ) -> Dict[str, AreaDataset]:
        """
        Automatically download CIR orthophotos for an area that may span multiple federal states.
        """
        return self.download_images_auto(
            area_name=area_name,
            area_polygon=area_polygon,
            out_path=out_path,
            image_type="CIR",
            filename_prefix=filename_prefix,
            mask=mask,
            buffer_size=buffer_size,
        )

    def download_rgbi_images_auto(
        self,
        area_name: str,
        area_polygon: Union[GeoSeries, GeoDataFrame, Polygon],
        out_path: Path,
        mask: Optional[Union[GeoSeries, GeoDataFrame]] = None,
        buffer_size: int = 0,
    ) -> Dict[str, AreaDataset]:
        """
        Automatically download and merge RGBI orthophotos for an area that may span multiple federal states.

        This function will download both RGB and CIR images for each intersecting state,
        then merge them into RGBI images using the RGBIImageDownloader.
        """
        # Import here to avoid circular imports
        from orthophotos_downloader.data_scraping.image_download import (
            RGBIImageDownloader,
        )

        # Detect intersecting states
        intersecting_states = self.detect_intersecting_states(area_polygon)

        if not intersecting_states:
            raise ValueError("No German federal states intersect with the given area")

        results = {}

        for state_name, state_code, intersection_geom in intersecting_states:
            logger.info(f"Processing RGBI for {state_name} ({state_code})...")

            try:
                # Try direct RGBI service first (prefer file downloads when available)
                rgbi_services = self._catalog.filter_services(
                    state_code=state_code,
                    image_type="RGBI",
                    year=self.year
                )

                rgbi_service = rgbi_services[0] if rgbi_services else None

                if rgbi_service and self.delivery_method in ['auto', 'files'] and rgbi_service.has_files():
                    logger.info(
                        "Using file delivery for RGBI in %s (%s) via service %s",
                        state_name,
                        state_code,
                        rgbi_service.id
                    )

                    rgbi_downloader = self._instantiate_downloader(
                        downloader_class=FileServiceDownloader,
                        service=rgbi_service
                    )

                    intersection_gs = gpd.GeoSeries([intersection_geom], crs="EPSG:25832")
                    state_out_path = out_path / f"{state_name.replace('/', '_')}"
                    state_out_path.mkdir(parents=True, exist_ok=True)

                    result = rgbi_downloader.download_images_from_polygon(
                        area_name=f"{area_name}_{state_name}",
                        area_polygon=intersection_gs,
                        out_path=state_out_path,
                        filename_prefix=f"RGBI_{rgbi_service.year}"
                    )

                    results[state_name] = result
                    logger.info(
                        f"✅ {state_name}: {len(result.images)} RGBI images downloaded via file service"
                    )
                    continue

                if self.delivery_method == 'files':
                    raise ValueError(
                        f"RGBI file delivery not available for {state_name} ({state_code}) in year {self.year}.\n"
                        f"  Available delivery methods: {rgbi_service.get_delivery_methods()}"
                        if rgbi_service else
                        f"No RGBI service found for {state_name} ({state_code}) in year {self.year}."
                    )

                # Fallback to WMS composition using RGB + CIR services
                rgb_services = self._catalog.filter_services(
                    state_code=state_code,
                    image_type="RGB",
                    year=self.year
                )
                cir_services = self._catalog.filter_services(
                    state_code=state_code,
                    image_type="CIR",
                    year=self.year
                )

                if not rgb_services or not cir_services:
                    raise ValueError(
                        f"Cannot build RGBI imagery for {state_name} ({state_code}) in year {self.year}:\n"
                        f"  RGB services found: {len(rgb_services)}\n"
                        f"  CIR services found: {len(cir_services)}"
                    )

                rgb_service = rgb_services[0]
                cir_service = cir_services[0]

                if not rgb_service.has_wms() or not cir_service.has_wms():
                    raise ValueError(
                        f"RGBI WMS composition requires RGB and CIR WMS endpoints.\n"
                        f"  RGB has WMS: {rgb_service.has_wms()}\n"
                        f"  CIR has WMS: {cir_service.has_wms()}"
                    )

                rgb_layer_override = (
                    rgb_service.layer_name
                    if rgb_service.year not in ['latest', 'current']
                    else None
                )
                cir_layer_override = (
                    cir_service.layer_name
                    if cir_service.year not in ['latest', 'current']
                    else None
                )

                rgb_downloader = self._instantiate_downloader(
                    downloader_class=WMSServiceDownloader,
                    service=rgb_service,
                    layer_override=rgb_layer_override
                )
                cir_downloader = self._instantiate_downloader(
                    downloader_class=WMSServiceDownloader,
                    service=cir_service,
                    layer_override=cir_layer_override
                )

                # Create RGBI downloader for WMS composition
                rgbi_downloader = RGBIImageDownloader(rgb_downloader, cir_downloader)

                # Create GeoSeries for the intersection
                intersection_gs = gpd.GeoSeries([intersection_geom], crs="EPSG:25832")

                # Create state-specific output directory
                state_out_path = out_path / f"{state_name.replace('/', '_')}"
                state_out_path.mkdir(parents=True, exist_ok=True)

                # Download RGBI images for this state's portion
                result = rgbi_downloader.download_rgbi_images_from_polygon(
                    area_name=f"{area_name}_{state_name}",
                    area_polygon=intersection_gs,
                    out_path=state_out_path,
                    mask=mask,
                    buffer_size=buffer_size,
                )

                results[state_name] = result
                logger.info(
                    f"✅ {state_name}: {len(result.images)} RGBI images downloaded"
                )

            except Exception as e:
                logger.error(
                    f"❌ Failed to download RGBI from {state_name} ({state_code}): {e}"
                )
                continue

        return results


def auto_download_orthophotos(
    area_name: str,
    area_polygon: Union[GeoSeries, GeoDataFrame, Polygon],
    out_path: Path,
    grid_spacing: int = 1000,
    image_type: str = "RGB",
    filename_prefix: Optional[str] = None,
    mask: Optional[Union[GeoSeries, GeoDataFrame]] = None,
    buffer_size: int = 0,
    extract_metadata: bool = True,
) -> Dict[str, AreaDataset]:
    """
    Convenience function to automatically download orthophotos.

    This function automatically detects which WMS services are needed for the given area
    and downloads orthophotos from all relevant services.

    Args:
        area_name: Name of the area for identification
        area_polygon: The area of interest (GeoSeries, GeoDataFrame, or Shapely Polygon)
        out_path: Output path where images will be saved
        grid_spacing: The grid spacing in meters for the image download (default: 1000)
        image_type: "RGB", "CIR", or "RGBI" (default: "RGB")
        filename_prefix: Optional prefix for filenames
        mask: Optional mask to limit downloads to specific areas
        buffer_size: Buffer size around the area (default: 0)
        extract_metadata: Whether to extract metadata and create STAC items for downloaded tiles (default: True)

    Returns:
        Dictionary mapping state names to their AreaDataset results

    Example:
        >>> import geopandas as gpd
        >>> from pathlib import Path
        >>> from orthophotos_downloader.data_scraping.auto_downloader import auto_download_orthophotos
        >>>
        >>> # Load your area of interest
        >>> area = gpd.read_file('my_area.geojson')
        >>>
        >>> # Automatically download RGB orthophotos with metadata
        >>> results = auto_download_orthophotos(
        ...     area_name="my_area",
        ...     area_polygon=area.geometry,
        ...     out_path=Path("./downloads"),
        ...     grid_spacing=1000,
        ...     image_type="RGB",
        ...     extract_metadata=True
        ... )
    """
    auto_downloader = AutoOrthophotoDownloader(grid_spacing=grid_spacing, extract_metadata=extract_metadata)

    if image_type == "RGB":
        return auto_downloader.download_rgb_images_auto(
            area_name=area_name,
            area_polygon=area_polygon,
            out_path=out_path,
            filename_prefix=filename_prefix,
            mask=mask,
            buffer_size=buffer_size,
        )
    elif image_type == "CIR":
        return auto_downloader.download_cir_images_auto(
            area_name=area_name,
            area_polygon=area_polygon,
            out_path=out_path,
            filename_prefix=filename_prefix,
            mask=mask,
            buffer_size=buffer_size,
        )
    elif image_type == "RGBI":
        return auto_downloader.download_rgbi_images_auto(
            area_name=area_name,
            area_polygon=area_polygon,
            out_path=out_path,
            mask=mask,
            buffer_size=buffer_size,
        )
    else:
        raise ValueError("image_type must be 'RGB', 'CIR', or 'RGBI'")

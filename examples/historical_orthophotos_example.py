#!/usr/bin/env python3
"""
Example: Working with Historical Orthophotos

This example demonstrates how to:
1. Query available historical orthophoto services
2. Compare imagery from different years
3. Download specific years
4. Setup multi-year download workflows
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import logging
import geopandas as gpd
from shapely.geometry import box

from orthophotos_downloader.wms_catalog import WMSCatalogManager, WMSDiscovery
from orthophotos_downloader import AutoOrthophotoDownloader
from orthophotos_downloader.data_scraping.image_download import (
    ImageDownloader,
    ExtendedWebMapService
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example1_query_available_years():
    """Example 1: Query which years of imagery are available"""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Query Available Years")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    discovery = WMSDiscovery()
    
    # Get temporal options for Bayern
    print("\n📅 Available years for Bayern (RGB):")
    temporal = discovery.get_temporal_options('BY', image_type='RGB')
    
    print(f"\nTotal years available: {len(temporal)}")
    for year in sorted(temporal.keys(), reverse=True):
        services = temporal[year]
        print(f"\n  Year {year}:")
        for s in services:
            print(f"    • Resolution: {s.resolution}m")
            print(f"      Temporal coverage: {s.temporal_coverage}")
            print(f"      Source: {s.source}")


def example2_compare_years():
    """Example 2: Compare available options across years"""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Compare Years and Resolutions")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    
    print("\n📊 Bayern DOP20 RGB - Available years:\n")
    
    # Get all years for DOP20
    services = catalog.filter_services(
        state_code='BY',
        image_type='RGB',
        resolution=0.2
    )
    
    years = sorted(set(str(s.year) for s in services))
    print(f"Years: {years}")
    
    print("\nBreakdown by year:")
    for year in sorted(years, reverse=True):
        year_services = [s for s in services if str(s.year) == year]
        for s in year_services:
            print(f"  {year}: {s.temporal_coverage}")


def example3_state_by_state_historical():
    """Example 3: Check historical availability by state"""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Historical Coverage by State")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    
    states_to_check = ['BY', 'NW', 'NI', 'BW', 'HE']
    
    print("\n🗺️  Historical coverage summary:\n")
    
    for state_code in states_to_check:
        services = catalog.filter_services(state_code=state_code)
        years = sorted(set(str(s.year) for s in services))
        
        rgb_years = sorted(set(str(s.year) for s in services if s.type == 'RGB'))
        cir_years = sorted(set(str(s.year) for s in services if s.type == 'CIR'))
        
        print(f"{state_code}:")
        print(f"  RGB years: {rgb_years}")
        print(f"  CIR years: {cir_years}")
        print()


def example4_download_single_year():
    """Example 4: Download orthophotos from a specific year"""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Download Specific Year (Simulation)")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    
    print("\n📥 To download orthophotos from 2020:\n")
    
    # Find 2020 services
    services_2020 = catalog.filter_services(
        state_code='BY',
        image_type='RGB',
        year='2020'
    )
    
    if services_2020:
        service = services_2020[0]
        print(f"Service found: {service.id}")
        print(f"Description: {service.description}")
        print(f"Temporal coverage: {service.temporal_coverage}")
        print(f"Resolution: {service.resolution}m")
        print(f"\nTo download:")
        print("""
    from orthophotos_downloader.data_scraping.image_download import (
        ImageDownloader,
        ExtendedWebMapService
    )
    
    # Create WMS configuration
    wms = ExtendedWebMapService(
        url="{url}",
        version="{version}",
        resolution={resolution},
        layer_name="{layer}",
        crs="{crs}",
        format="{format}"
    )
    
    # Create downloader
    downloader = ImageDownloader(wms=wms, grid_spacing=1000)
    
    # Download images
    result = downloader.download_images_from_polygon(
        area_name="my_area_2020",
        area_polygon=area_gdf,
        out_path="./downloads/2020"
    )
        """.format(
            url=service.url,
            version=service.version,
            resolution=service.resolution,
            layer=service.layer_name,
            crs=service.crs,
            format=service.format
        ))
    else:
        print("⚠️  No 2020 services found for Bayern RGB")


def example5_multi_year_setup():
    """Example 5: Setup structure for multi-year comparison"""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Multi-Year Comparison Setup")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    
    print("\n🔄 Multi-year comparison strategy:\n")
    
    # Get different years
    years_to_compare = ['latest', '2018', '2016', '2014']
    state = 'BY'
    
    print(f"State: {state}")
    print(f"Target years: {years_to_compare}")
    print()
    
    available_by_year = {}
    for year in years_to_compare:
        services = catalog.filter_services(
            state_code=state,
            image_type='RGB',
            year=year
        )
        
        if services:
            available_by_year[year] = services[0]
            print(f"✅ {year}: Available ({services[0].temporal_coverage})")
        else:
            print(f"❌ {year}: Not available")
    
    print("\n📋 Recommended workflow:")
    print("""
    1. Define your area of interest
    2. For each year:
       a. Create ImageDownloader with that year's WMS
       b. Download tiles to year-specific directory
       c. Store metadata with year label
    3. Post-processing:
       a. Mosaic tiles within each year
       b. Compare vegetation indices (if CIR available)
       c. Analyze changes over time
    """)


def example6_temporal_metadata():
    """Example 6: Understanding temporal coverage"""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Understanding Temporal Coverage")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    
    print("\n📆 What does 'temporal_coverage' mean?\n")
    
    print("Examples from catalog:")
    print()
    
    # Get some examples
    examples = [
        ('BY_RGB_DOP20_current', 'Current/Latest'),
        ('BW_RGB_DOP20_current', 'Baden-Württemberg'),
    ]
    
    for service_id, label in examples:
        service = catalog.get_service_by_id(service_id)
        if service:
            print(f"{label}:")
            print(f"  ID: {service.id}")
            print(f"  Year: {service.year}")
            print(f"  Temporal coverage: {service.temporal_coverage}")
            print(f"  Description: {service.description}")
            print()
    
    print("Key dates:")
    print("  • 'latest': Most recent available imagery")
    print("  • Specific year (e.g., '2020'): Imagery from that year")
    print("  • Range (e.g., '2020-current'): Imagery from start year to present")
    print("  • Range (e.g., '2018-2022'): Imagery within date range")


def example7_historical_availability_map():
    """Example 7: Create a map of historical availability"""
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Historical Availability Overview")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    
    print("\n📊 Historical orthophoto availability by state and year:\n")
    
    # Get all services
    all_services = catalog.get_all_services()
    
    # Build availability matrix
    states = sorted(catalog.get_states())
    years = sorted(set(str(s.year) for s in all_services if str(s.year) != 'latest'))
    
    print("State | Years Available")
    print("-" * 50)
    
    for state in states:
        state_services = catalog.filter_services(state_code=state)
        state_years = sorted(set(str(s.year) for s in state_services))
        
        # Count by type
        rgb = len([s for s in state_services if s.type == 'RGB'])
        cir = len([s for s in state_services if s.type == 'CIR'])
        
        year_str = str(state_years)[:40]  # Truncate for display
        print(f"{state:5} | RGB:{rgb:2}, CIR:{cir:2} | {year_str}")


def example8_resolution_over_time():
    """Example 8: Resolution improvement over time"""
    print("\n" + "=" * 80)
    print("EXAMPLE 8: Resolution Improvement Over Time")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    
    print("\n📈 Bayern DOP resolution evolution:\n")
    
    # Get all Bayern services
    services = catalog.filter_services(state_code='BY', image_type='RGB')
    
    # Group by resolution
    by_resolution = {}
    for s in services:
        res = s.resolution
        if res not in by_resolution:
            by_resolution[res] = []
        by_resolution[res].append(s)
    
    print("Resolution | Available Years")
    print("-" * 40)
    
    for res in sorted(by_resolution.keys()):
        dop = int(res * 100)
        years = sorted(set(str(s.year) for s in by_resolution[res]))
        print(f"DOP{dop} ({res}m) | {years}")


def example9_search_by_temporal_range():
    """Example 9: Search within a temporal range"""
    print("\n" + "=" * 80)
    print("EXAMPLE 9: Search by Temporal Range")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    
    print("\n🔍 Services from 2015-2020 period:\n")
    
    # In a real implementation, you'd add these to the catalog
    target_years = ['2015', '2016', '2017', '2018', '2019', '2020', 'latest']
    
    print("Searching for services...")
    found_count = 0
    
    for year in target_years:
        services = catalog.filter_services(
            state_code='BY',
            image_type='RGB',
            year=year
        )
        
        if services:
            print(f"  ✅ {year}: {len(services)} service(s)")
            found_count += len(services)
        else:
            print(f"  ⚠️  {year}: Not yet in catalog")
    
    print(f"\nTotal found: {found_count}")


def example10_adding_historical_to_catalog():
    """Example 10: How to add historical services"""
    print("\n" + "=" * 80)
    print("EXAMPLE 10: Adding Historical Services to Catalog")
    print("=" * 80)
    
    print("""
📝 To add historical orthophoto services:

1. Find the WMS URL for historical data
   Example: Bayern provides 2020 data at specific URL

2. Add entry to wms_services.yaml:
   
   - id: BY_RGB_DOP20_2020
     state_code: BY
     state_name: Bayern
     type: RGB
     resolution: 0.2
     year: 2020
     temporal_coverage: "2020"
     url: "https://geoservices.bayern.de/od/wms/dop/v1/dop20_2020?"
     version: "1.1.1"
     layer_name: by_dop20c_2020
     crs: EPSG:25832
     format: image/tiff
     availability: state-wide
     description: "Bayern DOP20 RGB - 2020 archive"
     direct_download: false
     source: "Bayerische Vermessungsverwaltung"

3. Test the new entry:
   
   catalog = WMSCatalogManager()
   service = catalog.get_service_by_id('BY_RGB_DOP20_2020')
   if service:
       print(f"✅ Service loaded: {service}")

4. Use in downloads:
   
   services = catalog.filter_services(
       state_code='BY',
       year='2020'
   )
    """)


def main():
    """Run all historical orthophoto examples"""
    examples = [
        example1_query_available_years,
        example2_compare_years,
        example3_state_by_state_historical,
        example4_download_single_year,
        example5_multi_year_setup,
        example6_temporal_metadata,
        example7_historical_availability_map,
        example8_resolution_over_time,
        example9_search_by_temporal_range,
        example10_adding_historical_to_catalog,
    ]
    
    print("\n" + "=" * 80)
    print("Historical Orthophoto Examples")
    print("=" * 80)
    
    for func in examples:
        try:
            func()
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
    
    print("\n" + "=" * 80)
    print("Historical Examples Complete!")
    print("=" * 80)
    print("""
💡 Next Steps:
  1. Identify which historical years you need
  2. Check if those WMS services exist for your area
  3. Add them to the catalog if not already present
  4. Use WMSDiscovery to query available options
  5. Download using specific year filters
  
📚 More information:
  • See WMS_DISCOVERY_GUIDE.md for detailed documentation
  • See wms_discovery_examples.py for more query examples
  • See wms_services.yaml for current catalog structure
    """)


if __name__ == "__main__":
    main()

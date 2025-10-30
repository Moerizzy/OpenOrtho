#!/usr/bin/env python3
"""
Example: WMS Service Discovery - Query Available Orthophotos

This example demonstrates how to:
1. Query the WMS catalog for available services
2. Filter by various criteria (state, type, resolution, year)
3. Discover services for specific geographic areas
4. Get recommendations for best available service
5. Compare available options before downloading
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import logging
from orthophotos_downloader.wms_catalog import WMSCatalogManager, WMSDiscovery

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def example1_explore_catalog():
    """Example 1: Explore the entire catalog"""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Explore WMS Catalog")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    catalog.print_summary()


def example2_find_services_for_state():
    """Example 2: Find all services for a specific state"""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Find Services for Bayern")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    
    # Get all Bayern services
    services = catalog.filter_services(state_code='BY')
    print(f"\nTotal Bayern services: {len(services)}")
    
    # Display them
    catalog.print_services_table(services)
    
    # Group by type
    rgb = [s for s in services if s.type == 'RGB']
    cir = [s for s in services if s.type == 'CIR']
    
    print(f"RGB services: {len(rgb)}")
    print(f"CIR services: {len(cir)}")


def example3_filter_by_criteria():
    """Example 3: Filter services by various criteria"""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Filter Services by Criteria")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    
    # Get only high-resolution RGB services
    print("\n1️⃣  High-resolution (0.2m) RGB services:")
    services = catalog.filter_services(
        image_type='RGB',
        resolution=0.2
    )
    print(f"Found {len(services)} services")
    for s in services[:5]:  # Show first 5
        print(f"  • {s.state_code}: {s.description}")
    
    # Get services without authentication
    print("\n2️⃣  Services without authentication required:")
    services = catalog.filter_services(requires_auth=False)
    print(f"Found {len(services)} services (total in catalog: {len(catalog.get_all_services())})")
    
    # Get services with direct download capability
    print("\n3️⃣  Services with direct download:")
    services = catalog.filter_services(direct_download=True)
    print(f"Found {len(services)} services")
    for s in services:
        print(f"  • {s.id}: {s.source}")
    
    # Get CIR services for specific states
    print("\n4️⃣  CIR services for NW and NI:")
    services = catalog.filter_services(
        state_code=['NW', 'NI'],
        image_type='CIR'
    )
    print(f"Found {len(services)} services")
    for s in services:
        print(f"  • {s.state_code}: {s.description}")


def example4_query_available_options():
    """Example 4: Query what options are available"""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Query Available Options")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    
    # Get all available states
    print("\n🗺️  States with orthophoto coverage:")
    states = catalog.get_states()
    print(f"Total states: {len(states)}")
    print(f"States: {', '.join(states)}\n")
    
    # For each state, show what's available
    print("Available options by state:")
    for state in sorted(states):
        years = catalog.get_years_for_state(state)
        types = catalog.get_image_types_for_state(state)
        resolutions = catalog.get_resolutions_for_state(state)
        
        print(f"\n  {state}:")
        print(f"    Years: {years}")
        print(f"    Types: {types}")
        print(f"    Resolutions: {resolutions} (meters)")


def example5_compare_resolution_options():
    """Example 5: Compare resolution options"""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Compare Resolution Options")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    
    # Bayern has multiple resolutions
    print("\n📊 Bayern available resolutions:\n")
    
    for resolution in [0.2, 0.4]:
        services = catalog.filter_services(
            state_code='BY',
            resolution=resolution
        )
        dop = int(resolution * 100)
        print(f"DOP{dop} ({resolution}m): {len(services)} service(s)")
        for s in services:
            print(f"  • {s.type}: {s.temporal_coverage}")


def example6_discover_for_area():
    """Example 6: Discover services for geographic area"""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Discover Services for Geographic Area")
    print("=" * 80)
    
    discovery = WMSDiscovery()
    
    # Munich area (UTM EPSG:25832)
    bbox = (4476000, 5327000, 4496000, 5347000)
    
    print(f"\nArea: Munich region")
    print(f"Bounding box: {bbox}")
    
    # Get available services
    services = discovery.get_available_services(
        bbox=bbox,
        image_type='RGB'
    )
    
    print(f"\nAvailable RGB services for area: {len(services)}")
    for s in services:
        print(f"  • {s.state_name} ({s.state_code}): {s.description}")


def example7_temporal_options():
    """Example 7: Query temporal (year) options"""
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Temporal Options (Available Years)")
    print("=" * 80)
    
    discovery = WMSDiscovery()
    
    print("\n📅 Available years for Bayern RGB:")
    temporal = discovery.get_temporal_options('BY', image_type='RGB')
    
    for year in sorted(temporal.keys()):
        services = temporal[year]
        print(f"\n  Year {year}: {len(services)} service(s)")
        for s in services:
            print(f"    • {s.resolution}m - {s.source}")


def example8_spectral_options():
    """Example 8: Query spectral (RGB/CIR) options"""
    print("\n" + "=" * 80)
    print("EXAMPLE 8: Spectral Options (RGB vs CIR)")
    print("=" * 80)
    
    discovery = WMSDiscovery()
    
    print("\n🌈 Available image types for Nordrhein-Westfalen:")
    spectral = discovery.get_spectral_options('NW')
    
    for img_type in sorted(spectral.keys()):
        services = spectral[img_type]
        print(f"\n  {img_type}: {len(services)} service(s)")
        for s in services:
            print(f"    • {s.resolution}m")


def example9_get_recommendations():
    """Example 9: Get service recommendations"""
    print("\n" + "=" * 80)
    print("EXAMPLE 9: Get Service Recommendations")
    print("=" * 80)
    
    discovery = WMSDiscovery()
    bbox = (4476000, 5327000, 4496000, 5347000)
    
    print(f"\nArea: Munich region (RG B)")
    
    # Find best service
    recommended = discovery.recommend_service(
        bbox=bbox,
        image_type='RGB',
        prefer_latest=True,
        prefer_high_res=True,
        prefer_direct=True
    )
    
    if recommended:
        print(f"\n✅ Recommended service:")
        print(f"   ID: {recommended.id}")
        print(f"   State: {recommended.state_name} ({recommended.state_code})")
        print(f"   Type: {recommended.type}")
        print(f"   Resolution: {recommended.resolution}m")
        print(f"   Year: {recommended.year}")
        print(f"   Direct download: {recommended.direct_download}")
        print(f"   Description: {recommended.description}")
        print(f"   URL: {recommended.url}")
    else:
        print("❌ No suitable service found")


def example10_discovery_summary():
    """Example 10: Print discovery summary for area"""
    print("\n" + "=" * 80)
    print("EXAMPLE 10: Discovery Summary for Area")
    print("=" * 80)
    
    discovery = WMSDiscovery()
    
    # Munich area
    bbox = (4476000, 5327000, 4496000, 5347000)
    discovery.print_discovery_summary(bbox=bbox)


def example11_specific_state():
    """Example 11: Deep dive into specific state"""
    print("\n" + "=" * 80)
    print("EXAMPLE 11: Deep Dive - Nordrhein-Westfalen")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    
    print("\n🏛️  Nordrhein-Westfalen (NW) Orthophoto Services:\n")
    
    # Get all NW services
    services = catalog.filter_services(state_code='NW')
    
    # Group by resolution
    by_resolution = {}
    for s in services:
        res = s.resolution
        if res not in by_resolution:
            by_resolution[res] = []
        by_resolution[res].append(s)
    
    for resolution in sorted(by_resolution.keys()):
        dop = int(resolution * 100)
        print(f"DOP{dop} ({resolution}m):")
        for s in by_resolution[resolution]:
            auth = "🔒" if s.requires_auth else "🔓"
            direct = "📥" if s.direct_download else "   "
            print(f"  {auth} {direct} {s.type}: {s.temporal_coverage}")


def example12_historical_comparison():
    """Example 12: Compare current vs historical"""
    print("\n" + "=" * 80)
    print("EXAMPLE 12: Current vs Historical Imagery")
    print("=" * 80)
    
    catalog = WMSCatalogManager()
    
    print("\n🕐 Bayern RGB - Current vs Historical:\n")
    
    # Current
    current = catalog.filter_services(
        state_code='BY',
        image_type='RGB',
        year='latest'
    )
    print(f"Current (latest):")
    for s in current:
        print(f"  • {s.resolution}m - {s.temporal_coverage}")
    
    # Note: Historical years would be added to catalog as they become available
    print(f"\nHistorical years available: (To be populated with historical services)")


def main():
    """Run all examples"""
    examples = [
        ("1: Explore Catalog", example1_explore_catalog),
        ("2: Find Services for State", example2_find_services_for_state),
        ("3: Filter by Criteria", example3_filter_by_criteria),
        ("4: Query Available Options", example4_query_available_options),
        ("5: Compare Resolution Options", example5_compare_resolution_options),
        ("6: Discover for Area", example6_discover_for_area),
        ("7: Temporal Options", example7_temporal_options),
        ("8: Spectral Options", example8_spectral_options),
        ("9: Get Recommendations", example9_get_recommendations),
        ("10: Discovery Summary", example10_discovery_summary),
        ("11: Deep Dive - NW", example11_specific_state),
        ("12: Current vs Historical", example12_historical_comparison),
    ]
    
    print("\n" + "=" * 80)
    print("WMS Service Discovery Examples")
    print("=" * 80)
    print(f"\nAvailable examples ({len(examples)} total):")
    for name, _ in examples:
        print(f"  • Example {name}")
    
    # Run all examples
    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("Examples Complete!")
    print("=" * 80)
    print("\n💡 Tips:")
    print("  • Use WMSCatalogManager for low-level catalog queries")
    print("  • Use WMSDiscovery for geographic area queries")
    print("  • Use AutoOrthophotoDownloader for automatic downloads")
    print("  • See WMS_DISCOVERY_GUIDE.md for detailed documentation")
    print()


if __name__ == "__main__":
    main()

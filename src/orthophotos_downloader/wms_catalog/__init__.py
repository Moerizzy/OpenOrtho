"""
WMS Catalog Module

This module provides functionality to manage, query, and discover WMS services
for orthophoto downloads. It supports filtering by state, year, resolution, 
and image type (RGB/CIR).
"""

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name == 'WMSCatalogManager':
        from orthophotos_downloader.wms_catalog.catalog_manager import WMSCatalogManager
        return WMSCatalogManager
    elif name == 'WMSDiscovery':
        from orthophotos_downloader.wms_catalog.wms_discovery import WMSDiscovery
        return WMSDiscovery
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ['WMSCatalogManager', 'WMSDiscovery']

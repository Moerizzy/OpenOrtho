"""
WMS Catalog Module

This module provides functionality to manage, query, and discover WMS services
for orthophoto downloads. It supports filtering by state, year, resolution, 
and image type (RGB/CIR).

Features:
- Catalog management with 417+ WMS services
- Service discovery with coverage verification
- Automatic service integration and monitoring
- Support for both WMS and direct file downloads
"""

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name == 'WMSCatalogManager':
        from orthophotos_downloader.wms_catalog.catalog_manager import WMSCatalogManager
        return WMSCatalogManager
    elif name == 'WMSDiscovery':
        from orthophotos_downloader.wms_catalog.wms_discovery import WMSDiscovery
        return WMSDiscovery
    elif name == 'ServiceDiscovery':
        from orthophotos_downloader.wms_catalog.service_discovery import ServiceDiscovery
        return ServiceDiscovery
    elif name == 'ServiceAutoIntegrator':
        from orthophotos_downloader.wms_catalog.auto_integrate import ServiceAutoIntegrator
        return ServiceAutoIntegrator
    elif name == 'ServiceMonitor':
        from orthophotos_downloader.wms_catalog.service_monitor import ServiceMonitor
        return ServiceMonitor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    'WMSCatalogManager', 
    'WMSDiscovery',
    'ServiceDiscovery',
    'ServiceAutoIntegrator',
    'ServiceMonitor'
]

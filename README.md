# OpenOrtho - German Orthophoto Downloader

Python library for downloading orthophotos from German WMS services with automatic state detection.

## Features

- **547 WMS services** across all 16 German federal states
- **517 historic orthophotos** dating back to 1937 (Bremerhaven)
- **Direct file downloads** available for 5 states (uncompressed, highest quality)
- Automatically detects which German state(s) your area falls into
- RGB, CIR (Color Infrared), and RGBI (4-band merged)
- 📊 Automatic STAC metadata generation with acquisition dates for each tile
- Supports both WMS streaming and direct file delivery

## Quick Start

```bash
# Clone and install
git clone https://github.com/ffe-munich/orthophotos-downloader.git
cd orthophotos-downloader
pip install .
```

## Usage

See the complete demo in [`examples/autodownloader_demo.ipynb`](examples/autodownloader_demo.ipynb)

```python
from orthophotos_downloader import AutoOrthophotoDownloader
import geopandas as gpd
from shapely.geometry import box

# Define area (EPSG:25832)
area = box(513000, 5538000, 514500, 5539500)
area_gdf = gpd.GeoDataFrame([1], geometry=[area], crs="EPSG:25832")

# Download RGB imagery
downloader = AutoOrthophotoDownloader(grid_spacing=1000)
downloader.download_rgb_images_auto(
    area_polygon=area_gdf,
    area_name="my_area",
    out_path="./downloads/rgb"
)
```

## Coverage by Federal State

| State                  | RGB | CIR | RGBI | Historic | File Downloads |
|------------------------|:---:|:---:|:----:|:--------:|:--------------:|
| Baden-Württemberg      | ✅  | ✅  | ✅   | ✅ (1960-2023) | ❌ |
| Bayern                 | ✅  | ✅  | ✅   | ✅ (2003-2024) | ✅ |
| Berlin                 | ✅  | ✅  | ✅   | ✅ (2004-2024) | ❌ |
| Brandenburg            | ✅  | ✅  | ✅   | ✅ (1953-2021) | ✅ |
| Bremen                 | ✅  | ❌  | ❌   | ✅ (1937-2025) | ❌ |
| Hamburg                | ✅  | ❌  | ❌   | ✅ (2005-2024) | ❌ |
| Hessen                 | ✅  | ✅  | ✅   | ✅ (2007-2024) | ❌ |
| Mecklenburg-Vorpommern | ✅  | ✅  | ✅   | ✅ (1953-2024) | ❌ |
| Niedersachsen          | ✅  | ❌  | ❌   | ✅ (2005-2022) | ✅ |
| Nordrhein-Westfalen    | ✅  | ✅  | ✅   | ✅ (1951-2023) | ✅ |
| Rheinland-Pfalz        | ✅  | ✅  | ✅   | ✅ (1994-2023) | ✅ |
| Saarland               | ✅  | ✅  | ✅   | ✅ (1999-2022) | ❌ |
| Sachsen                | ✅  | ✅  | ✅   | ✅ (1992-2022) | ❌ |
| Sachsen-Anhalt         | ✅  | ❌  | ❌   | ✅ (2014-2024) | ❌ |
| Schleswig-Holstein     | ✅  | ❌  | ❌   | ✅ (2018-2021) | ❌ |
| Thüringen              | ✅  | ✅  | ✅   | ✅ (1992-2023) | ❌ |

**File Downloads:** Uncompressed files via direct download (Brandenburg, Bayern, Niedersachsen, Nordrhein-Westfalen, Rheinland-Pfalz)

**Historic Services:** 517 historic orthophoto services dating back to 1937 (Bremerhaven), with automatic acquisition date extraction from metadata

**Metadata includes:** Acquisition date, tile number, flight information, ground resolution, and more (varies by state).

## Requirements

- Python >= 3.9
- geopandas
- rasterio
- shapely
- requests

## License

Distributed under Apache-2.0 license. See `LICENSE.txt` for more information. 
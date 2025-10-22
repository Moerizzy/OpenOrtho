# OpenOrtho - German Orthophoto Downloader

Python library for downloading orthophotos from German WMS services with automatic state detection.

## Features

- Automatically detects which German state(s) your area falls into
- RGB, CIR (Color Infrared), and RGBI (4-band merged)
- Supports all 16 German federal states

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

| Bundesland             | RGB | CIR |
|------------------------|:---:|:---:|
| Saarland               | ✅  | ✅  |
| Mecklenburg-Vorpommern | ✅  | ✅  |
| Rheinland-Pfalz        | ✅  | ✅  |
| Sachsen                | ✅  | ✅  |
| Thüringen              | ✅  | ✅  |
| Sachsen-Anhalt         | ✅  |     |
| Nordrhein-Westfalen    | ✅  | ✅  |
| Hessen                 | ✅  | ✅  |
| Hamburg                | ✅  | ✅  |
| Bremen                 | ✅  |     |
| Brandenburg            | ✅  | ✅  |
| Niedersachsen          | ✅  |     |
| Schleswig-Holstein     | ✅  |     |
| Bayern                 | ✅  | ✅  |

## Requirements

- Python >= 3.9
- geopandas
- rasterio
- shapely
- requests

## License

Distributed under Apache-2.0 license. See `LICENSE.txt` for more information. 
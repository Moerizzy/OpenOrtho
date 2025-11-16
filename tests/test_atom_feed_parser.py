import json
import math
from pathlib import Path

import numpy as np
import pytest
from rasterio.transform import from_origin
from shapely.geometry import Polygon, box
from shapely.strtree import STRtree

from orthophotos_downloader.data_scraping.file_downloader import FileServiceDownloader
from orthophotos_downloader.wms_catalog.catalog_manager import WMSService


SAMPLE_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:georss="http://www.georss.org/georss"
      xmlns:inspire_dls="http://inspire.ec.europa.eu/schemas/inspire_dls/1.0">
  <entry>
    <title>Digitales Orthophoto (DOP20) 32455-6083</title>
    <inspire_dls:spatial_dataset_identifier_code>dop20rgbi_32_455_6083_1_sh_2024</inspire_dls:spatial_dataset_identifier_code>
    <georss:polygon>6083000 455000 6084000 455000 6084000 456000 6083000 456000 6083000 455000</georss:polygon>
    <link rel="alternate" href="https://host.example/feeds/DOP20_dop20rgbi_32_455_6083_1_sh_2024.xml" />
    <summary>Das digitale Orthophoto 32455-6083 wurde am 2024-07-26 aufgenommen.</summary>
    <updated>2024-01-01T00:00:00+01:00</updated>
  </entry>
  <entry>
    <title>Digitales Orthophoto (DOP20) 32455-6084</title>
    <inspire_dls:spatial_dataset_identifier_code>dop20rgbi_32_455_6083_1_sh_2023</inspire_dls:spatial_dataset_identifier_code>
    <georss:polygon>6083000 455000 6084000 455000 6084000 456000 6083000 456000 6083000 455000</georss:polygon>
    <link rel="alternate" href="https://host.example/feeds/DOP20_dop20rgbi_32_455_6083_1_sh_2023.xml" />
    <summary>Historische Aufnahme mit Datum 2023-06-15 fuer interne Tests.</summary>
    <updated>2023-01-01T00:00:00+01:00</updated>
  </entry>
</feed>
"""


SAMPLE_TILE_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>dop20rgbi_32_455_6083_1_sh_2024</title>
    <link rel="alternate"
      href="https://udp.gdi-sh.de/fmedatastreaming/OpenAccess/WCSTileAssembler.fmw?Split=2&amp;WCSUrl=https://dienste.gdi-sh.de/WCS_SH_DOP20col_OpenGBD?SERVICE=WCS%26REQUEST=GetCoverage%26COVERAGE=3%26FORMAT=GeoTIFF%26BBOX=455000,6083000,456000,6084000%26WIDTH=2500%26HEIGHT=2500%26CRS=EPSG:25832" />
  </entry>
</feed>
"""


SAMPLE_SECTION_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <link rel="section"
        href="https://www.geodaten-mv.de/dienste/dop20_download?index=0&amp;dataset=demo&amp;file=dop20rgbi_33_214_5920_2_mv.tif"
        type="image/tiff"
        bbox="53.3527019 10.7303844 53.3717000 10.7621579"
        title="DOP20 RGBI M-V im CRS EPSG:25833" />
</feed>
"""


SAMPLE_GML_TILE = b"""<?xml version="1.0" encoding="UTF-8"?>
<gml:FeatureCollection xmlns:gml="http://www.opengis.net/gml/3.2">
  <gml:featureMember>
    <gml:GridCoverage>
      <rangeParameters xlink:href="https://download.example/12345.tif" xmlns:xlink="http://www.w3.org/1999/xlink"/>
      <fileReference>https://download.example/12345.tif</fileReference>
      <base:Identifier xmlns:base="http://inspire.ec.europa.eu/schemas/base2/2.0">
        <base:localId>12345.tif</base:localId>
      </base:Identifier>
    </gml:GridCoverage>
  </gml:featureMember>
</gml:FeatureCollection>
"""


def _build_downloader(tmp_path: Path, extract_metadata: bool = False) -> FileServiceDownloader:
    service = WMSService(
        id="SH_RGBI_DOP20_test",
        state_code="SH",
        state_name="Schleswig-Holstein",
        type="RGBI",
        resolution=0.2,
        crs="EPSG:25832",
        files={
            "index_type": "atom",
            "atom_feed_url": "https://example.com/feed.xml",
            "product_code": "dop20rgbi",
            "grid_size": 1000,
            "default_extension": "tif",
        },
    )
    downloader = FileServiceDownloader(
        service=service,
        grid_spacing=1000,
        extract_metadata=extract_metadata,
        max_workers=1,
    )
    # Ensure downloads go into tmp directory during tests
    downloader.service_output_path = tmp_path
    return downloader


def test_parse_atom_feed_extracts_entries():
    entries = FileServiceDownloader._parse_atom_feed(SAMPLE_FEED)
    assert len(entries) == 2
    first = entries[0]
    assert isinstance(first["geometry"], Polygon)
    assert math.isclose(first["geometry"].area, 1000000.0)
    assert first["product"] == "dop20rgbi"
    assert first["year"] == "2024"
    assert first["tile_key"] == "dop20rgbi_32_455_6083_1_sh"
    assert first["tile_feed_url"].endswith("sh_2024.xml")
    assert first["acquisition_date"] == "2024-07-26"
    assert "2024-07-26" in first["summary"]


def test_parse_atom_tile_feed_extracts_wcs_url():
    details = FileServiceDownloader._parse_atom_tile_feed(SAMPLE_TILE_FEED)
    assert details["download_url"].startswith("https://dienste.gdi-sh.de/WCS_SH_DOP20col_OpenGBD?SERVICE=WCS")


def test_parse_atom_tile_feed_handles_gml_tile():
    details = FileServiceDownloader._parse_atom_tile_feed(SAMPLE_GML_TILE)
    assert details["download_url"] == "https://download.example/12345.tif"
    assert details["title"] == "12345.tif"


def test_parse_atom_feed_section_links():
    entries = FileServiceDownloader._parse_atom_feed(SAMPLE_SECTION_FEED)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["download_url"].startswith("https://www.geodaten-mv.de/dienste/dop20_download")
    assert entry["product"] == "dop20rgbi"
    assert entry["tile_feed_url"] is None
    minx, miny, maxx, maxy = entry["geometry"].bounds
    assert maxx > minx
    assert maxy > miny


def test_get_tiles_from_atom_feed_filters_and_selects_latest(tmp_path):
    downloader = _build_downloader(tmp_path)
    entries = FileServiceDownloader._parse_atom_feed(SAMPLE_FEED)
    polygons = [entry["geometry"] for entry in entries]
    feed_cache = {
        "entries": entries,
        "polygons": polygons,
        "tree": STRtree(polygons),
    }
    area = box(455000, 6083000, 456000, 6084000)

    def fake_get_atom_feed_data(url: str):
        return feed_cache

    assert downloader.service.files_index_type == "atom"

    # Patch feed loading
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(FileServiceDownloader, "_get_atom_feed_data", staticmethod(fake_get_atom_feed_data))

    try:
        latest_tiles = downloader.get_tiles_from_atom_feed(area_polygon=area, target_year=None)
        assert len(latest_tiles) == 1
        assert latest_tiles[0]["year"] == "2024"
        assert latest_tiles[0]["acquisition_date"] == "2024-07-26"

        year_tiles = downloader.get_tiles_from_atom_feed(area_polygon=area, target_year="2023")
        assert len(year_tiles) == 1
        assert year_tiles[0]["year"] == "2023"
        assert year_tiles[0]["acquisition_date"] == "2023-06-15"
    finally:
        monkeypatch.undo()


def test_adjust_wcs_resolution_sets_width_and_height(tmp_path):
    downloader = _build_downloader(tmp_path)
    original_url = (
        "https://dienste.gdi-sh.de/WCS_SH_DOP20col_OpenGBD?"
        "SERVICE=WCS&REQUEST=GetCoverage&COVERAGE=3&FORMAT=GeoTIFF&"
        "BBOX=455000,6083000,456000,6084000&WIDTH=2500&HEIGHT=2500&CRS=EPSG:25832"
    )
    adjusted = downloader._adjust_wcs_resolution(original_url)
    assert "WIDTH=4000" in adjusted
    assert "HEIGHT=4000" in adjusted
    assert "RESX=" in adjusted
    assert "RESY=" in adjusted


def test_extract_image_metadata_merges_extra_metadata(tmp_path):
    downloader = _build_downloader(tmp_path, extract_metadata=True)
    tile_path = tmp_path / "dop20rgbi_32_455_6083_1_sh_2024.tif"

    import rasterio

    data = np.zeros((4, 2, 2), dtype="uint8")
    with rasterio.open(
        tile_path,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=4,
        dtype="uint8",
        crs="EPSG:25832",
        transform=from_origin(455000, 6084000, 0.2, 0.2),
    ) as dst:
        dst.write(data)

    extra_metadata = {
        "acquisition_date": "2024-07-26",
        "summary": "Das digitale Orthophoto 32455-6083 wurde am 2024-07-26 aufgenommen.",
        "date_source": "atom_feed_summary",
    }

    downloader._extract_image_metadata(tile_path, extra_metadata=extra_metadata)

    stac_path = tile_path.with_suffix(".json")
    assert stac_path.exists()

    stac = json.loads(stac_path.read_text())
    props = stac["properties"]
    assert props["ortho:acquisition_date"] == "2024-07-26"
    assert props["ortho:summary"].startswith("Das digitale Orthophoto")
    assert props["ortho:date_source"] == "atom_feed_summary"

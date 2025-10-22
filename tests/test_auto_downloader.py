"""
Unit tests for AutoOrthophotoDownloader functionality.
Tests automatic state detection and multi-state orchestration.
"""

import pytest
from shapely.geometry import box
import geopandas as gpd

from orthophotos_downloader import AutoOrthophotoDownloader


class TestAutoOrthophotoDownloader:
    """Test AutoOrthophotoDownloader class."""

    def test_initialization(self):
        """Test AutoOrthophotoDownloader initialization."""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)

        assert downloader.grid_spacing == 1000
        assert hasattr(downloader, "STATE_TO_RGB_DOWNLOADER")
        assert hasattr(downloader, "STATE_TO_CIR_DOWNLOADER")

    def test_state_mappings_exist(self):
        """Test that state mappings are properly defined."""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)

        # Check RGB mappings
        assert len(downloader.STATE_TO_RGB_DOWNLOADER) > 0
        assert "BY" in downloader.STATE_TO_RGB_DOWNLOADER
        assert "BW" in downloader.STATE_TO_RGB_DOWNLOADER

        # Check CIR mappings
        assert len(downloader.STATE_TO_CIR_DOWNLOADER) > 0
        assert "BY" in downloader.STATE_TO_CIR_DOWNLOADER

    def test_detect_intersecting_states_bavaria(self):
        """Test state detection for a location in Bavaria."""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)

        # Create a small area in Munich (Bavaria)
        bbox = box(691000, 5334000, 692000, 5335000)
        area = gpd.GeoDataFrame([1], geometry=[bbox], crs="EPSG:25832")

        states = downloader.detect_intersecting_states(area.geometry)

        assert len(states) > 0
        state_names = [s[0] for s in states]
        assert "Bayern" in state_names

    def test_detect_intersecting_states_with_polygon(self):
        """Test state detection with a Shapely polygon."""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)

        # Create a polygon directly
        bbox = box(691000, 5334000, 692000, 5335000)

        states = downloader.detect_intersecting_states(bbox)

        assert len(states) > 0

    def test_get_downloader_class_rgb(self):
        """Test getting RGB downloader class."""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)

        downloader_class = downloader._get_downloader_class("BY", "RGB")

        assert downloader_class is not None
        assert "BY_RGB" in downloader_class.__name__

    def test_get_downloader_class_cir(self):
        """Test getting CIR downloader class."""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)

        downloader_class = downloader._get_downloader_class("BY", "CIR")

        assert downloader_class is not None
        assert "BY_CIR" in downloader_class.__name__

    def test_get_downloader_class_invalid_type(self):
        """Test that invalid image type raises error."""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)

        with pytest.raises(ValueError, match="image_type must be"):
            downloader._get_downloader_class("BY", "INVALID")

    def test_get_downloader_class_unavailable_state(self):
        """Test that unavailable state code raises error."""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)

        with pytest.raises(ValueError, match="No .* downloader available"):
            downloader._get_downloader_class("XX", "RGB")


class TestAutoDownloaderIntegration:
    """Integration tests for AutoOrthophotoDownloader."""

    @pytest.mark.slow
    def test_small_area_detection(self):
        """Test detection for a very small area."""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)

        # 100m x 100m area in Munich
        bbox = box(691000, 5334000, 691100, 5334100)
        area = gpd.GeoDataFrame([1], geometry=[bbox], crs="EPSG:25832")

        states = downloader.detect_intersecting_states(area.geometry)

        assert len(states) >= 1
        assert all(len(s) == 3 for s in states)  # (name, code, intersection)

    @pytest.mark.slow
    def test_border_area_detection(self):
        """Test detection for an area near state borders."""
        downloader = AutoOrthophotoDownloader(grid_spacing=1000)

        # Area that might cross state boundaries
        # (coordinates would need to be on actual border)
        bbox = box(500000, 5500000, 505000, 5505000)
        area = gpd.GeoDataFrame([1], geometry=[bbox], crs="EPSG:25832")

        states = downloader.detect_intersecting_states(area.geometry)

        # Should detect at least one state
        assert len(states) >= 1

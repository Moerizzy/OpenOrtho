"""
Unit tests for core image download functionality.
Tests ImageDownloader, ExtendedWebMapService, and related classes.
"""

import pytest
import tempfile
from pathlib import Path
from shapely.geometry import box
import geopandas as gpd
from unittest.mock import Mock, patch

from orthophotos_downloader.data_scraping.image_download import (
    ImageDownloader,
    ExtendedWebMapService,
    AreaDataset,
    Image,
    RGBIImageDownloader,
    CentralWMSManager,
    MultiServiceDownloader,
)


class TestExtendedWebMapService:
    """Test ExtendedWebMapService class."""

    @patch("orthophotos_downloader.data_scraping.image_download.WebMapService")
    def test_initialization(self, mock_wms_class):
        """Test that ExtendedWebMapService can be initialized."""
        mock_wms_class.return_value = Mock()

        wms = ExtendedWebMapService(
            url="https://test.example.com/wms",
            version="1.1.1",
            resolution=0.2,
            layer_name="test_layer",
            crs="EPSG:25832",
            format="image/png",
        )

        assert wms.resolution == 0.2
        assert wms.layer_name == "test_layer"
        assert wms.crs == "EPSG:25832"
        assert wms.format == "image/png"

    @patch("orthophotos_downloader.data_scraping.image_download.WebMapService")
    def test_to_dict(self, mock_wms_class):
        """Test serialization to dictionary."""
        mock_wms_instance = Mock()
        mock_wms_instance.url = "https://test.example.com/wms"
        mock_wms_class.return_value = mock_wms_instance

        wms = ExtendedWebMapService(
            url="https://test.example.com/wms",
            version="1.1.1",
            resolution=0.2,
            layer_name="test_layer",
            crs="EPSG:25832",
            format="image/png",
        )

        wms_dict = wms.to_dict()
        assert isinstance(wms_dict, dict)
        assert "resolution" in wms_dict
        assert wms_dict["resolution"] == 0.2


class TestImageDownloader:
    """Test ImageDownloader class."""

    @pytest.fixture
    @patch("orthophotos_downloader.data_scraping.image_download.WebMapService")
    def mock_wms(self, mock_wms_class):
        """Create a mock WMS service for testing."""
        mock_wms_class.return_value = Mock()
        return ExtendedWebMapService(
            url="https://test.example.com/wms",
            version="1.1.1",
            resolution=0.2,
            layer_name="test_layer",
            crs="EPSG:25832",
            format="image/png",
        )

    def test_initialization(self, mock_wms):
        """Test that ImageDownloader can be initialized."""
        downloader = ImageDownloader(wms=mock_wms, grid_spacing=1000)

        assert downloader.wms == mock_wms
        assert downloader.grid_spacing == 1000
        assert downloader.width_px == 1000 / 0.2
        assert downloader.height_px == 1000 / 0.2

    def test_grid_spacing_calculation(self, mock_wms):
        """Test that grid spacing affects pixel dimensions correctly."""
        downloader = ImageDownloader(wms=mock_wms, grid_spacing=500)

        assert downloader.grid_spacing == 500
        assert downloader.width_px == 500 / 0.2  # 2500 pixels
        assert downloader.height_px == 500 / 0.2

    def test_to_dict(self, mock_wms):
        """Test serialization to dictionary."""
        downloader = ImageDownloader(wms=mock_wms, grid_spacing=1000)

        downloader_dict = downloader.to_dict()
        assert isinstance(downloader_dict, dict)
        assert "grid_spacing" in downloader_dict
        assert "wms" in downloader_dict


class TestAreaDataset:
    """Test AreaDataset class."""

    def test_initialization(self):
        """Test AreaDataset initialization."""
        polygon = box(0, 0, 1000, 1000)
        dataset = AreaDataset(
            name="test_area", polygon=polygon, buffer_size=0, out_path=Path("/tmp/test")
        )

        assert dataset.name == "test_area"
        assert dataset.polygon == polygon
        assert dataset.buffer_size == 0
        assert dataset.out_path == Path("/tmp/test")
        assert dataset.images is None


class TestImage:
    """Test Image dataclass."""

    def test_initialization(self):
        """Test Image initialization."""
        img = Image(
            image_path=Path("/tmp/test.tiff"),
            mask_path=None,
            upper_left_x=100,
            upper_left_y=200,
            download_time=5.5,
            width_m=1000,
            height_m=1000,
            width_px=5000,
            height_px=5000,
            resolution_m=0.2,
            crs="EPSG:25832",
        )

        assert img.image_path == Path("/tmp/test.tiff")
        assert img.upper_left_x == 100
        assert img.upper_left_y == 200
        assert img.download_time == 5.5
        assert img.width_m == 1000
        assert img.resolution_m == 0.2

    def test_to_dict(self):
        """Test Image serialization."""
        img = Image(
            image_path=Path("/tmp/test.tiff"),
            mask_path=None,
            upper_left_x=100,
            upper_left_y=200,
            download_time=5.5,
            width_m=1000,
            height_m=1000,
            width_px=5000,
            height_px=5000,
            resolution_m=0.2,
            crs="EPSG:25832",
        )

        img_dict = img.to_dict()
        assert isinstance(img_dict, dict)
        assert "upper_left_x" in img_dict
        assert img_dict["upper_left_x"] == 100


class TestRGBIImageDownloader:
    """Test RGBI image downloader functionality."""

    @pytest.fixture
    @patch("orthophotos_downloader.data_scraping.image_download.WebMapService")
    def mock_rgb_downloader(self, mock_wms_class):
        """Create a mock RGB downloader."""
        mock_wms_class.return_value = Mock()
        wms = ExtendedWebMapService(
            url="https://test.example.com/wms",
            version="1.1.1",
            resolution=0.2,
            layer_name="rgb_layer",
            crs="EPSG:25832",
            format="image/png",
        )
        return ImageDownloader(wms=wms, grid_spacing=1000)

    @pytest.fixture
    @patch("orthophotos_downloader.data_scraping.image_download.WebMapService")
    def mock_cir_downloader(self, mock_wms_class):
        """Create a mock CIR downloader."""
        mock_wms_class.return_value = Mock()
        wms = ExtendedWebMapService(
            url="https://test.example.com/wms",
            version="1.1.1",
            resolution=0.2,
            layer_name="cir_layer",
            crs="EPSG:25832",
            format="image/png",
        )
        return ImageDownloader(wms=wms, grid_spacing=1000)

    def test_initialization(self, mock_rgb_downloader, mock_cir_downloader):
        """Test RGBIImageDownloader initialization."""
        rgbi_downloader = RGBIImageDownloader(
            rgb_downloader=mock_rgb_downloader, cir_downloader=mock_cir_downloader
        )

        assert rgbi_downloader.rgb_downloader == mock_rgb_downloader
        assert rgbi_downloader.cir_downloader == mock_cir_downloader
        assert rgbi_downloader.grid_spacing == 1000

    @patch("orthophotos_downloader.data_scraping.image_download.WebMapService")
    def test_grid_spacing_mismatch(self, mock_wms_class, mock_rgb_downloader):
        """Test that mismatched grid spacing raises an error."""
        mock_wms_class.return_value = Mock()
        wms = ExtendedWebMapService(
            url="https://test.example.com/wms",
            version="1.1.1",
            resolution=0.2,
            layer_name="cir_layer",
            crs="EPSG:25832",
            format="image/png",
        )
        cir_downloader = ImageDownloader(wms=wms, grid_spacing=500)  # Different!

        with pytest.raises(AssertionError):
            RGBIImageDownloader(
                rgb_downloader=mock_rgb_downloader, cir_downloader=cir_downloader
            )


class TestCentralWMSManager:
    """Test CentralWMSManager functionality."""

    @pytest.fixture
    def sample_wms_metadata(self):
        """Create sample WMS metadata."""
        return [
            {
                "url": "https://test1.example.com/wms",
                "version": "1.1.1",
                "resolution": 0.2,
                "layer_name": "layer1",
                "crs": "EPSG:25832",
                "format": "image/png",
                "bounding_box": (690000, 5330000, 700000, 5340000),
            },
            {
                "url": "https://test2.example.com/wms",
                "version": "1.1.1",
                "resolution": 0.2,
                "layer_name": "layer2",
                "crs": "EPSG:25832",
                "format": "image/png",
                "bounding_box": (700000, 5330000, 710000, 5340000),
            },
        ]

    def test_initialization(self, sample_wms_metadata):
        """Test CentralWMSManager initialization."""
        manager = CentralWMSManager(wms_metadata=sample_wms_metadata)

        assert manager.wms_metadata == sample_wms_metadata
        assert manager.downloaders == []


class TestMultiServiceDownloader:
    """Test MultiServiceDownloader functionality."""

    @pytest.fixture
    def sample_wms_metadata(self):
        """Create sample WMS metadata."""
        return [
            {
                "url": "https://test1.example.com/wms",
                "version": "1.1.1",
                "resolution": 0.2,
                "layer_name": "layer1",
                "crs": "EPSG:25832",
                "format": "image/png",
                "bounding_box": (690000, 5330000, 700000, 5340000),
            }
        ]

    def test_initialization(self, sample_wms_metadata):
        """Test MultiServiceDownloader initialization."""
        downloader = MultiServiceDownloader(wms_metadata=sample_wms_metadata)

        assert downloader.wms_metadata == sample_wms_metadata
        assert downloader.downloaders == []

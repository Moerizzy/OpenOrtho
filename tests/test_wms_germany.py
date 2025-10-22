"""
Unit tests for German state WMS downloaders.
Tests all state-specific downloader classes.
"""

import pytest
from orthophotos_downloader.data_scraping import wms_germany


class TestStateDownloaders:
    """Test all German state downloader classes."""

    # List of all expected RGB downloaders
    RGB_DOWNLOADERS = [
        "BW_RGB_Dop20_ImageDownloader",
        "BY_RGB_Dop20_ImageDownloader",
        "BY_RGB_Dop40_ImageDownloader",
        "BE_RGB_Dop20_ImageDownloader",
        "BB_RGB_Dop20_ImageDownloader",
        "HB_RGB_Dop20_ImageDownloader",
        "BHV_RGB_Dop20_ImageDownloader",
        "HH_RGB_Dop20_ImageDownloader",
        "HE_RGB_Dop20_ImageDownloader",
        "MV_RGB_Dop20_ImageDownloader",
        "NI_RGB_Dop20_ImageDownloader",
        "NW_RGB_Dop20_ImageDownloader",
        "RP_RGB_Dop20_ImageDownloader",
        "SL_RGB_Dop20_ImageDownloader",
        "SN_RGB_Dop20_ImageDownloader",
        "ST_RGB_Dop20_ImageDownloader",
        "SH_RGB_Dop20_ImageDownloader",
        "TH_RGB_Dop20_ImageDownloader",
        "BKG_RGB_Dop20_ImageDownloader",
    ]

    # List of expected CIR downloaders
    CIR_DOWNLOADERS = [
        "BW_CIR_Dop20_ImageDownloader",
        "BY_CIR_Dop20_ImageDownloader",
        "BE_CIR_Dop20_ImageDownloader",
        "BB_CIR_Dop20_ImageDownloader",
        "HH_CIR_Dop20_ImageDownloader",
        "HE_CIR_Dop20_ImageDownloader",
        "MV_CIR_Dop20_ImageDownloader",
        "NW_CIR_Dop20_ImageDownloader",
        "RP_CIR_Dop20_ImageDownloader",
        "SL_CIR_Dop20_ImageDownloader",
        "SN_CIR_Dop20_ImageDownloader",
        "TH_CIR_Dop20_ImageDownloader",
    ]

    @pytest.mark.parametrize("downloader_name", RGB_DOWNLOADERS)
    def test_rgb_downloader_exists(self, downloader_name):
        """Test that all expected RGB downloaders exist."""
        assert hasattr(
            wms_germany, downloader_name
        ), f"RGB downloader {downloader_name} not found in wms_germany module"

    @pytest.mark.parametrize("downloader_name", CIR_DOWNLOADERS)
    def test_cir_downloader_exists(self, downloader_name):
        """Test that all expected CIR downloaders exist."""
        assert hasattr(
            wms_germany, downloader_name
        ), f"CIR downloader {downloader_name} not found in wms_germany module"

    @pytest.mark.parametrize("downloader_name", RGB_DOWNLOADERS)
    def test_rgb_downloader_instantiation(self, downloader_name):
        """Test that RGB downloaders can be instantiated."""
        # Skip known issues
        if downloader_name in [
            "HH_RGB_Dop20_ImageDownloader",
            "HE_RGB_Dop20_ImageDownloader",
        ]:
            pytest.skip(f"{downloader_name} WMS service has known issues")
        if downloader_name == "BKG_RGB_Dop20_ImageDownloader":
            pytest.skip("BKG downloader requires uuid parameter")

        downloader_class = getattr(wms_germany, downloader_name)
        downloader = downloader_class(grid_spacing=1000)

        assert downloader is not None
        assert downloader.grid_spacing == 1000
        assert hasattr(downloader, "wms")
        assert downloader.wms.resolution is not None

    @pytest.mark.parametrize("downloader_name", CIR_DOWNLOADERS)
    def test_cir_downloader_instantiation(self, downloader_name):
        """Test that CIR downloaders can be instantiated."""
        # Skip known issue
        if downloader_name == "HH_CIR_Dop20_ImageDownloader":
            pytest.skip("HH CIR WMS service has known 404 issue")

        downloader_class = getattr(wms_germany, downloader_name)
        downloader = downloader_class(grid_spacing=1000)

        assert downloader is not None
        assert downloader.grid_spacing == 1000
        assert hasattr(downloader, "wms")
        assert downloader.wms.resolution is not None

    def test_bavaria_rgb_configuration(self):
        """Test Bavaria RGB downloader configuration."""
        downloader = wms_germany.BY_RGB_Dop20_ImageDownloader(grid_spacing=1000)

        assert downloader.wms.resolution == 0.2
        assert downloader.wms.crs == "EPSG:25832"
        assert (
            "bayern" in downloader.wms.wms.url.lower()
            or "bay" in downloader.wms.wms.url.lower()
        )

    def test_bavaria_cir_configuration(self):
        """Test Bavaria CIR downloader configuration."""
        downloader = wms_germany.BY_CIR_Dop20_ImageDownloader(grid_spacing=1000)

        assert downloader.wms.resolution == 0.2
        assert downloader.wms.crs == "EPSG:25832"
        assert "cir" in downloader.wms.layer_name.lower()

    def test_all_downloaders_have_wms(self):
        """Test that all downloaders have a valid WMS configuration."""
        all_downloaders = [
            d
            for d in self.RGB_DOWNLOADERS + self.CIR_DOWNLOADERS
            if d
            not in [
                "HH_RGB_Dop20_ImageDownloader",
                "HH_CIR_Dop20_ImageDownloader",
                "HE_RGB_Dop20_ImageDownloader",
                "BKG_RGB_Dop20_ImageDownloader",
            ]
        ]

        for downloader_name in all_downloaders:
            downloader_class = getattr(wms_germany, downloader_name)
            downloader = downloader_class(grid_spacing=1000)

            # Check WMS attributes - ExtendedWebMapService has these attributes
            assert hasattr(downloader.wms, "wms"), f"{downloader_name} missing wms.wms"
            assert hasattr(
                downloader.wms.wms, "url"
            ), f"{downloader_name} missing wms.wms.url"
            assert hasattr(
                downloader.wms, "resolution"
            ), f"{downloader_name} missing wms.resolution"
            assert hasattr(
                downloader.wms, "layer_name"
            ), f"{downloader_name} missing wms.layer_name"
            assert hasattr(downloader.wms, "crs"), f"{downloader_name} missing wms.crs"
            assert hasattr(
                downloader.wms, "format"
            ), f"{downloader_name} missing wms.format"

            # Check values are not None - url is in wms.wms (the WebMapService object)
            assert (
                downloader.wms.wms.url is not None
            ), f"{downloader_name} wms.wms.url is None"
            assert (
                downloader.wms.resolution is not None
            ), f"{downloader_name} wms.resolution is None"
            assert (
                downloader.wms.layer_name is not None
            ), f"{downloader_name} wms.layer_name is None"
            assert downloader.wms.crs is not None, f"{downloader_name} wms.crs is None"
            assert downloader.wms.format is not None


class TestStateDownloaderPairs:
    """Test that states with CIR also have RGB."""

    def test_cir_states_have_rgb(self):
        """Test that every state with CIR also has RGB."""
        cir_states = [
            "BW",
            "BY",
            "BE",
            "BB",
            "HH",
            "HE",
            "MV",
            "NW",
            "RP",
            "SL",
            "SN",
            "TH",
        ]

        for state in cir_states:
            rgb_name = f"{state}_RGB_Dop20_ImageDownloader"
            cir_name = f"{state}_CIR_Dop20_ImageDownloader"

            assert hasattr(
                wms_germany, rgb_name
            ), f"State {state} has CIR but missing RGB downloader"
            assert hasattr(
                wms_germany, cir_name
            ), f"State {state} missing CIR downloader"

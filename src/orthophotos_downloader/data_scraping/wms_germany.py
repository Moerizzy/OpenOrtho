from orthophotos_downloader.data_scraping.image_download import (
    ImageDownloader,
    ExtendedWebMapService,
)


class BW_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the BW DOP20 WMS service.
    The WMS specifications are automatically set to the BW DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the BadenWuertembergRGBDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
            extract_metadata: Whether to extract metadata and create STAC items for downloaded tiles.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_DOP_20_C?",
            version="1.1.1",
            resolution=0.2,
            layer_name="IMAGES_DOP_20_RGB",
            crs="EPSG:25832",
            format="image/png",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='BW', extract_metadata=extract_metadata)


class BW_CIR_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the BW DOP20 WMS service.
    The WMS specifications are automatically set to the BW DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the BadenWuertembergRGBDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_DOP_20_CIR",
            version="1.1.1",
            resolution=0.2,
            layer_name="IMAGES_DOP_20_CIR",
            crs="EPSG:25832",
            format="image/png",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='BW', extract_metadata=extract_metadata)


class BY_RGB_Dop40_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Bayern DOP40 WMS service.
    The WMS specifications are automatically set to the Bayern DOP40 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the BayernDop40ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP40 WMS
        wms = ExtendedWebMapService(
            url="https://geoservices.bayern.de/od/wms/dop/v1/dop40?",
            version="1.1.1",
            resolution=0.4,
            layer_name="by_dop40c",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='BW', extract_metadata=extract_metadata)


class BY_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Bayern DOP20 WMS service.
    The WMS specifications are automatically set to the Bayern DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the BayernDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
            extract_metadata: Whether to extract metadata and create STAC items for downloaded tiles.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://geoservices.bayern.de/od/wms/dop/v1/dop20?",
            version="1.1.1",
            resolution=0.2,
            layer_name="by_dop20c",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='BY', extract_metadata=extract_metadata)


class BY_CIR_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Bayern DOP20 WMS service.
    The WMS specifications are automatically set to the Bayern DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the BayernDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://geoservices.bayern.de/od/wms/dop/v1/dop20?",
            version="1.1.1",
            resolution=0.2,
            layer_name="by_dop20cir",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='BY', extract_metadata=extract_metadata)


class BE_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Berlin DOP20 WMS service.
    The WMS specifications are automatically set to the Berlin DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the BE_RGB_Dop20_ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://isk.geobasis-bb.de/mapproxy/dop20c/service/wms",
            version="1.3.0",
            resolution=0.2,
            layer_name="bebb_dop20c",
            crs="EPSG:25832",
            format="image/png",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='BE', extract_metadata=extract_metadata)


class BE_CIR_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Berlin DOP CIR 20 WMS service.
    The WMS specifications are automatically set to the Berlin DOPCIR20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the BE_CIR_Dop20_ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://isk.geobasis-bb.de/mapproxy/dop20cir/service/wms",
            version="1.3.0",
            resolution=0.2,
            layer_name="bb_dop20cir",
            crs="EPSG:25832",
            format="image/png",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='BE', extract_metadata=extract_metadata)


class BB_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Brandenburg DOP20 WMS service.
    The WMS specifications are automatically set to the Brandenburg DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the BrandenburgDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://isk.geobasis-bb.de/mapproxy/dop20c/service/wms",
            version="1.3.0",
            resolution=0.2,
            layer_name="bebb_dop20c",
            crs="EPSG:25832",
            format="image/png",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='BB', extract_metadata=extract_metadata)


class BB_CIR_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Brandenburg DOP CIR 20 WMS service.
    The WMS specifications are automatically set to the Brandenburg DOPCIR20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the BrandenburgDopCIR20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://isk.geobasis-bb.de/mapproxy/dop20cir/service/wms",
            version="1.3.0",
            resolution=0.2,
            layer_name="bb_dop20cir",
            crs="EPSG:25832",
            format="image/png",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='BB', extract_metadata=extract_metadata)


class HB_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Bremen DOP20 WMS service.
    The WMS specifications are automatically set to the Bremen DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the BremenDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://geodienste.bremen.de/wms_dop20_2023?VERSION=1.3.0",
            version="1.3.0",
            resolution=0.2,
            layer_name="DOP20_2023_HB",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='BB', extract_metadata=extract_metadata)


# Bremerhaven and Bremen are implemented in diffrent WMS (same state)
class BHV_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Bremen DOP20 WMS service.
    The WMS specifications are automatically set to the Bremen DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the BremenDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://geodienste.bremen.de/wms_dop20_2023?VERSION=1.3.0",
            version="1.3.0",
            resolution=0.2,
            layer_name="DOP20_2023_BHV",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='HB', extract_metadata=extract_metadata)


class HH_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Hamburg DOP20 WMS service.
    The WMS specifications are automatically set to the Hamburg DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the HamburgDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://geodienste.hamburg.de/HH_WMS_DOP?language=ger&",
            version="1.3.0",
            resolution=0.2,
            layer_name="DOP",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='HH', extract_metadata=extract_metadata)


class HH_CIR_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Hamburg DOP20 WMS service.
    The WMS specifications are automatically set to the Hamburg DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the HamburgDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://geodienste.hamburg.de/HH_WMS_DOP?language=ger&",
            version="1.3.0",
            resolution=0.2,
            layer_name="CIR_DOP",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='HH', extract_metadata=extract_metadata)


class HE_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Hessen DOP20 WMS service.
    The WMS specifications are automatically set to the Hessen DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the HessenDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://www.gds-srv.hessen.de/cgi-bin/lika-services/ogc-free-images.ows?",
            version="1.3.0",
            resolution=0.2,
            layer_name="he_dop20_rgb",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='HE', extract_metadata=extract_metadata)


class HE_CIR_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Hessen DOP20 WMS service.
    The WMS specifications are automatically set to the Hessen DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the HessenDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://www.gds-srv.hessen.de/cgi-bin/lika-services/ogc-free-images.ows?",
            version="1.3.0",
            resolution=0.2,
            layer_name="he_dop20_cir",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='HE', extract_metadata=extract_metadata)


class MV_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Mecklenburg-Vorpommern DOP20 WMS service.
    The WMS specifications are automatically set to the Mecklenburg-Vorpommern DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    TODO: Watermarks in the right left corner of the image. Height 10px, width 100px.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the MecklenburgVorpommernDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="http://www.geodaten-mv.de/dienste/adv_dop",
            version="1.3.0",
            resolution=0.2,
            layer_name="mv_dop",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='MV', extract_metadata=extract_metadata)


class MV_CIR_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Mecklenburg-Vorpommern DOP20 WMS service.
    The WMS specifications are automatically set to the Mecklenburg-Vorpommern DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    TODO: Watermarks in the right left corner of the image. Height 10px, width 100px.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the MecklenburgVorpommernDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="http://www.geodaten-mv.de/dienste/gdimv_dopcir",
            version="1.3.0",
            resolution=0.2,
            layer_name="gdimv_dopcir",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='MV', extract_metadata=extract_metadata)


class NI_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Niedersachsen DOP20 WMS service.
    The WMS specifications are automatically set to the Niedersachsen DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the SchleswigHolsteinDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://opendata.lgln.niedersachsen.de/doorman/noauth/dop_wms?language=ger&version=1.3.0&sld_version=1.1.0&layer=WMS_NI_DOP20&STYLE=default",
            version="1.3.0",
            resolution=0.2,
            layer_name="ni_dop20",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='NI', extract_metadata=extract_metadata)


class NW_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the NRW DOP20 WMS service.
    The WMS specifications are automatically set to the NRW DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the NRWDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://www.wms.nrw.de/geobasis/wms_nw_dop",
            version="1.1.1",
            resolution=0.2,
            layer_name="nw_dop_rgb",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='NW', extract_metadata=extract_metadata)


class NW_CIR_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the NRW DOP20 WMS service.
    The WMS specifications are automatically set to the NRW DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the NRWDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://www.wms.nrw.de/geobasis/wms_nw_dop",
            version="1.1.1",
            resolution=0.2,
            layer_name="nw_dop_cir",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='NW', extract_metadata=extract_metadata)


class RP_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Rheinland-Pfalz DOP20 WMS service.
    The WMS specifications are automatically set to the Rheinland-Pfalz DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the RheinlandPfalzDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://geo4.service24.rlp.de/wms/rp_dop20.fcgi?VERSION=1.1.1",
            version="1.3.0",
            resolution=0.2,
            layer_name="rp_dop20",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='RP', extract_metadata=extract_metadata)


class RP_CIR_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Rheinland-Pfalz DOP20 WMS service.
    The WMS specifications are automatically set to the Rheinland-Pfalz DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the RheinlandPfalzDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://www.geoportal.rlp.de/mapbender/php/wms.php?inspire=1&layer_id=38922&withChilds=1",
            version="1.1.1",
            resolution=0.2,
            layer_name="rp_dopcir",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='RP', extract_metadata=extract_metadata)


class SL_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Saarland DOP20 WMS service.
    The WMS specifications are automatically set to the Saarland DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the SaarlandDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://geoportal.saarland.de/mapbender/php/wms.php?layer_id=46302&VERSION=1.1.1&withChilds=1",
            version="1.1.1",
            resolution=0.2,
            layer_name="sl_dop20_rgb",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='SL', extract_metadata=extract_metadata)


class SL_CIR_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Saarland DOP20 WMS service.
    The WMS specifications are automatically set to the Saarland DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the SaarlandDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://geoportal.saarland.de/mapbender/php/wms.php?layer_id=46302&VERSION=1.1.1&withChilds=1",
            version="1.1.1",
            resolution=0.2,
            layer_name="sl_dop20_cir",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='SL', extract_metadata=extract_metadata)


class ST_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Sachsen-Anhalt DOP20 WMS service.
    The WMS specifications are automatically set to the Sachsen-Anhalt DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the SachsenAnhaltDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://www.geodatenportal.sachsen-anhalt.de/wss/service/ST_LVermGeo_DOP_WMS_OpenData/guest",
            version="1.1.1",
            resolution=0.2,
            layer_name="lsa_lvermgeo_dop20_2",
            crs="EPSG:25832",
            format="image/png",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='ST', extract_metadata=extract_metadata)


class SN_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Sachsen DOP20 WMS service.
    The WMS specifications are automatically set to the Sachsen DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the SachsenDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://geodienste.sachsen.de/wms_geosn_dop-rgb/guest",
            version="1.3.0",
            resolution=0.2,
            layer_name="sn_dop_020",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='SN', extract_metadata=extract_metadata)


class SN_CIR_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Sachsen DOP20 WMS service.
    The WMS specifications are automatically set to the Sachsen DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the SachsenDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://geodienste.sachsen.de/wms_geosn_dop-cir/guest",
            version="1.3.0",
            resolution=0.2,
            layer_name="sn_dop_020_cir",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='SN', extract_metadata=extract_metadata)


class SH_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Schleswig-Holstein DOP20 WMS service.
    The WMS specifications are automatically set to the Schleswig-Holstein DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the SchleswigHolsteinDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://dienste.gdi-sh.de/WMS_SH_DOP20col_OpenGBD?",
            version="1.1.1",
            resolution=0.2,
            layer_name="sh_dop20_rgb",
            crs="EPSG:25832",
            format="image/png",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='SH', extract_metadata=extract_metadata)


class TH_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Thueringen DOP20 WMS service.
    The WMS specifications are automatically set to the Thueringen DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the ThueringenDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://www.geoproxy.geoportal-th.de/geoproxy/services/DOP20",
            version="1.1.1",
            resolution=0.2,
            layer_name="th_dop",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='TH', extract_metadata=extract_metadata)


class TH_CIR_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the Thueringen DOP20 WMS service.
    The WMS specifications are automatically set to the Thueringen DOP20 service.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, extract_metadata: bool = True):
        """
        Initialize the ThueringenDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url="https://www.geoproxy.geoportal-th.de/geoproxy/services/DOP20",
            version="1.1.1",
            resolution=0.2,
            layer_name="th_dop20cir",
            crs="EPSG:25832",
            format="image/png",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing, state_code='TH', extract_metadata=extract_metadata)


class BKG_RGB_Dop20_ImageDownloader(ImageDownloader):
    """
    A class for downloading images from the BKG DOP20 WMS service.
    The WMS specifications are automatically set to the BKG DOP20 service.
    Can Only be used with an UUID access that you can buy from thew BKG.
    Attributes:
        grid_spacing: The grid spacing in meters for the image download.
    """

    def __init__(self, grid_spacing: int, uuid: str):
        """
        Initialize the BkgDop20ImageDownloader.
        Args:
            grid_spacing: The grid spacing in meters for the image download.
            uuid: The UUID is used for authentication.
        """
        # Define the parameters specific for the DOP20 WMS
        wms = ExtendedWebMapService(
            url=f"https://sg.geodatenzentrum.de/wms_dop__{uuid}?",
            version="1.1.1",
            resolution=0.2,
            layer_name="rgb",
            crs="EPSG:25832",
            format="image/tiff",
        )

        super().__init__(wms=wms, grid_spacing=grid_spacing)

    def to_dict(self) -> dict:
        """Return a serializable dictionary representation of the BkgDop20ImageDownloader object."""
        r = super().to_dict()
        # replace the uuid with a placeholder to avoid exposing the secret
        r["wms"]["url"] = self.wms.wms.url.split("__")[0] + "__<secret_uuid>?"
        return r
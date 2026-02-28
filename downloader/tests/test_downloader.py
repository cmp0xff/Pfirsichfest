import os
from unittest.mock import patch

from downloader.controller import DownloaderManager


def test_downloader_initialization():
    """Test DownloaderManager initialization loads environment variables correctly."""
    with (
        patch.dict(
            os.environ,
            {
                "GOOGLE_CLOUD_PROJECT": "test-project-custom",
                "MAGNET_LINK": "magnet:?xt=urn:btih:123",
                "DOWNLOAD_ID": "dl123",
                "ENABLE_VPN": "true",
            },
        ),
        patch.object(DownloaderManager, "_get_secret", return_value="dummy_token"),
    ):
        manager = DownloaderManager()
        assert manager.project_id == "test-project-custom"
        assert manager.magnet_link == "magnet:?xt=urn:btih:123"
        assert manager.download_id == "dl123"
        assert manager.enable_vpn is True
        assert manager.bucket_name == "test-project-custom-pfirsichfest-archive"
        assert manager.bot_token == "dummy_token"

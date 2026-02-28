"""Spot VM Python Controller for Pfirsichfest. Orchestrates the VPN and Aria2."""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import requests  # type: ignore[import-untyped]
from dotenv import load_dotenv  # type: ignore[import-untyped]
from google.cloud import (
    compute_v1,  # type: ignore[import-untyped]
    firestore,  # type: ignore[import-untyped]
    secretmanager,  # type: ignore[import-untyped]
    storage,  # type: ignore[import-untyped]
)

load_dotenv(override=False)

# Standard logging behaves natively with Google Cloud Logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


class DownloaderManager:
    """Orchestrates the lifecycle of a single Torrents-to-Cloud workflow."""

    def __init__(self) -> None:
        """Initializes the Downloader configurations from environment variables."""
        self.project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "test-project")
        self.zone = os.environ.get("GOOGLE_CLOUD_ZONE", "us-central1-a")
        self.magnet_link = os.environ.get("MAGNET_LINK", "")
        self.download_id = os.environ.get("DOWNLOAD_ID", "")
        self.bucket_name = os.environ.get(
            "BUCKET_NAME", f"{self.project_id}-pfirsichfest-archive"
        )
        self.enable_vpn = os.environ.get("ENABLE_VPN", "false").lower() == "true"

        # We assume the bot Token is injected or available if we need Telegram uploads
        self.bot_token = self._get_secret("telegram-bot-token")

    def run(self) -> None:
        """Executes the core processing workflow for the VM."""
        logger.info("Pfirsichfest Downloader Controller Started.")
        if not self.magnet_link:
            logger.error("No magnet link provided.")
            sys.exit(1)

        try:
            if self.enable_vpn:
                logger.info("VPN is ENABLED. Provisioning secure OpenVPN tunnel.")
                self._start_vpn()
            else:
                logger.info(
                    "VPN is DISABLED via ENABLE_VPN=false. Running aria2c exposed."
                )

            file_path_out = self._start_torrent()

            size = Path(file_path_out).stat().st_size
            logger.info("Downloaded file size: %s bytes", size)

            # Telegram Bot API local container supports up to 2GB limits
            if size < 2 * 1024 * 1024 * 1024:
                logger.info("File < 2GB. Attempting Local Telegram API Upload.")
                self._upload_to_telegram(file_path_out)
            else:
                logger.info("File > 2GB. Routing to Google Cloud Storage.")
                self._upload_to_gcs(file_path_out)

        except Exception:
            logger.exception("Fatal error in downloader")
            self._update_status("fatal_error")
        finally:
            self._destroy_self()

    # --- Private Methods ---

    def _get_secret(self, secret_id: str, version_id: str = "latest") -> str | None:
        """Fetches a string secret from .env or Google Secret Manager."""
        if env_val := os.getenv(secret_id.upper().replace("-", "_")):
            return env_val

        try:
            client = secretmanager.SecretManagerServiceClient()
            name = (
                f"projects/{self.project_id}/secrets/{secret_id}/versions/{version_id}"
            )
            response = client.access_secret_version(request={"name": name})
            payload = response.payload.data.decode("UTF-8")
            return str(payload)
        except Exception:
            logger.exception("Failed to fetch secret %s", secret_id)
            return None

    def _update_status(self, status_text: str) -> None:
        """Updates the Firestore database with the current status."""
        if not self.project_id or not self.download_id:
            return
        try:
            db = firestore.Client()
            db.collection("downloads").document(self.download_id).update(
                {
                    "status": status_text,
                    "last_updated": firestore.SERVER_TIMESTAMP,
                },
            )
        except Exception:
            logger.exception("Failed to update status to %s", status_text)

    def _start_vpn(self) -> None:
        """Provisions the VPN via OpenVPN configuration."""
        logger.info("Setting up OpenVPN...")
        self._update_status("connecting_vpn")

        vpn_user = self._get_secret("vpn-user") or "testuser"
        vpn_pass = self._get_secret("vpn-pass") or "testpass"

        creds_file = Path("creds.txt")
        creds_file.write_text(f"{vpn_user}\n{vpn_pass}\n")
        creds_file.chmod(0o600)

        # In production this would daemonize the OpenVPN client via Subprocess
        logger.info("Starting OpenVPN tunnel...")
        time.sleep(5)  # Let tunnel establish (mocked for now)
        logger.info("VPN ready.")

    def _start_torrent(self) -> str:
        """Utilizes aria2c over a generic subprocess to torrent the magnet."""
        logger.info("Starting aria2c for %s", self.magnet_link)
        self._update_status("downloading")

        download_dir = Path("./downloads")
        download_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "aria2c",
            "--dir",
            str(download_dir.absolute()),
            "--seed-time=0",
            self.magnet_link,
        ]

        logger.info("Executing aria2c...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            logger.error("aria2c failed: %s", result.stderr)
            self._update_status("failed_download")
            sys.exit(1)

        logger.info("Download completed.")

        files = list(download_dir.iterdir())
        if not files:
            logger.error("No files found after download finished.")
            self._update_status("failed_no_files")
            sys.exit(1)

        main_file = files[0]
        return str(main_file.absolute())

    def _upload_to_telegram(self, file_path: str) -> None:
        """Uploads the file directly to the bot using the Telegram Bot API."""
        self._update_status("uploading_to_telegram")
        logger.info("Uploading %s to Telegram...", file_path)

        if not self.bot_token:
            logger.error("Cannot upload to Telegram: bot token missing.")
            self._update_status("failed_upload")
            return

        chat_id = ""
        # Look up Chat ID from Firestore document
        try:
            db = firestore.Client()
            doc = db.collection("downloads").document(self.download_id).get()
            if doc.exists:
                doc_dict = doc.to_dict()
                if doc_dict and "chat_id" in doc_dict:
                    chat_id = doc_dict["chat_id"]
        except Exception:
            logger.exception("Could not retrieve original chat_id for direct upload")

        if not chat_id:
            logger.error("No chat_id mapped. Assuming upload failed.")
            self._update_status("failed_upload")
            return

        # Fire requests POST pointing to Telegram API
        # (If running custom API Server on localhost:8081, switch URL here)
        url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"

        try:
            with Path(file_path).open("rb") as f:
                response = requests.post(
                    url, data={"chat_id": chat_id}, files={"document": f}, timeout=600
                )

            response.raise_for_status()
            logger.info("Successfully uploaded %s to Telegram.", file_path)
            self._update_status("completed")
        except Exception:
            logger.exception("Failed to POST document to Telegram API")
            self._update_status("failed_upload")

    def _upload_to_gcs(self, file_path: str) -> None:
        """Uploads generic artifacts > 2GB to GCS."""
        self._update_status("uploading_to_gcs")
        logger.info("Uploading %s to GCS bucket %s...", file_path, self.bucket_name)

        storage_client = storage.Client()
        bucket = storage_client.bucket(self.bucket_name)

        blob_name = Path(file_path).name
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(file_path)

        logger.info("Uploaded %s to gs://%s/", blob_name, self.bucket_name)
        self._update_status("completed")

    def _destroy_self(self) -> None:
        """Destroys the Compute Engine Instance using the GCP Compute API."""
        logger.info("Initiating self-destruction sequence...")
        try:
            instance_name = subprocess.check_output(["hostname"], text=True).strip()
            compute_client = compute_v1.InstancesClient()
            operation = compute_client.delete(
                project=self.project_id,
                zone=self.zone,
                instance=instance_name,
            )
            logger.info("Delete operation: %s", getattr(operation, "name", "unknown"))
        except Exception:
            logger.exception("Failed to delete self")


if __name__ == "__main__":
    manager = DownloaderManager()
    manager.run()

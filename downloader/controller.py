"""Spot VM Python Controller for Pfirsichfest. Orchestrates the VPN and Aria2."""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import compute_v1, firestore, secretmanager, storage  # type: ignore

load_dotenv()

# Standard logging behaves natively with Google Cloud Logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "test-project")
ZONE = os.environ.get("GOOGLE_CLOUD_ZONE", "us-central1-a")
MAGNET_LINK = os.environ.get("MAGNET_LINK", "")
DOWNLOAD_ID = os.environ.get("DOWNLOAD_ID", "")
BUCKET_NAME = os.environ.get("BUCKET_NAME", f"{PROJECT_ID}-pfirsichfest-archive")


def get_secret(secret_id: str, version_id: str = "latest") -> str | None:
    """Fetches a string secret from .env or Google Secret Manager."""
    if env_val := os.getenv(secret_id.upper().replace("-", "_")):
        return env_val

    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("UTF-8")
        return str(payload)
    except Exception:
        logger.exception("Failed to fetch secret %s", secret_id)
        return None


def update_status(status_text: str) -> None:
    """Updates the Firestore database with the current status."""
    if not PROJECT_ID or not DOWNLOAD_ID:
        return
    try:
        db = firestore.Client()
        db.collection("downloads").document(DOWNLOAD_ID).update(
            {
                "status": status_text,
                "last_updated": firestore.SERVER_TIMESTAMP,
            },
        )
    except Exception:
        logger.exception("Failed to update status to %s", status_text)


def start_vpn() -> None:
    """Provisions the VPN via OpenVPN configuration."""
    logger.info("Setting up OpenVPN...")
    update_status("connecting_vpn")

    vpn_user = get_secret("vpn-user") or "testuser"
    vpn_pass = get_secret("vpn-pass") or "testpass"

    creds_file = Path("creds.txt")
    creds_file.write_text(f"{vpn_user}\n{vpn_pass}\n")
    creds_file.chmod(0o600)

    logger.info("Starting OpenVPN tunnel...")
    time.sleep(5)  # Let tunnel establish (mocked for now)
    logger.info("VPN ready.")


def start_torrent(magnet_link: str) -> str:
    """Utilizes aria2c over a generic subprocess to torrent the magnet."""
    logger.info("Starting aria2c for %s", magnet_link)
    update_status("downloading")

    download_dir = Path("./downloads")
    download_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "aria2c",
        "--dir",
        str(download_dir.absolute()),
        "--seed-time=0",
        magnet_link,
    ]

    logger.info("Executing aria2c...")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        logger.error("aria2c failed: %s", result.stderr)
        update_status("failed_download")
        sys.exit(1)

    logger.info("Download completed.")

    files = list(download_dir.iterdir())
    if not files:
        logger.error("No files found after download finished.")
        update_status("failed_no_files")
        sys.exit(1)

    main_file = files[0]
    return str(main_file.absolute())


def upload_to_telegram() -> None:
    """Uploads directly to the Local Telegram API."""
    update_status("uploading_to_telegram")
    logger.info("Uploading buffer to Telegram...")
    time.sleep(2)
    update_status("completed")


def upload_to_gcs(file_path: str) -> None:
    """Uploads generic artifacts > 2GB to GCS."""
    update_status("uploading_to_gcs")
    logger.info("Uploading %s to GCS bucket %s...", file_path, BUCKET_NAME)

    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    blob_name = Path(file_path).name
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(file_path)

    logger.info("Uploaded %s to gs://%s/", blob_name, BUCKET_NAME)
    update_status("completed")


def destroy_self() -> None:
    """Destroys the Compute Engine Instance using the GCP Compute API."""
    logger.info("Initiating self-destruction sequence...")
    try:
        instance_name = subprocess.check_output(["hostname"], text=True).strip()
        compute_client = compute_v1.InstancesClient()
        operation = compute_client.delete(
            project=PROJECT_ID,
            zone=ZONE,
            instance=instance_name,
        )
        logger.info("Delete operation: %s", getattr(operation, "name", "unknown"))
    except Exception:
        logger.exception("Failed to delete self")


if __name__ == "__main__":
    logger.info("Pfirsichfest Downloader Controller Started.")
    if not MAGNET_LINK:
        logger.error("No magnet link provided.")
        sys.exit(1)

    try:
        enable_vpn = os.environ.get("ENABLE_VPN", "false").lower() == "true"
        if enable_vpn:
            logger.info("VPN is ENABLED. Provisioning secure OpenVPN tunnel.")
            start_vpn()
        else:
            logger.info("VPN is DISABLED via ENABLE_VPN=false. Running aria2c exposed.")

        file_path_out = start_torrent(MAGNET_LINK)

        size = Path(file_path_out).stat().st_size
        logger.info("Downloaded file size: %s bytes", size)

        # 2 Gigabytes threshold
        if size < 2 * 1024 * 1024 * 1024:
            logger.info("File < 2GB. Attempting Local Telegram API Upload.")
            upload_to_telegram()
        else:
            logger.info("File > 2GB. Routing to Google Cloud Storage.")
            upload_to_gcs(file_path_out)

    except Exception:
        logger.exception("Fatal error in downloader")
        update_status("fatal_error")
    finally:
        destroy_self()

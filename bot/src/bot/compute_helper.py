import logging
import os

from google.cloud import (
    compute_v1,  # type: ignore[import-untyped]
)

logger = logging.getLogger(__name__)


class SpotVMProvisioner:
    """Provisions ephemeral Spot VMs on Google Compute Engine for download operations."""

    def __init__(self, download_id: str, magnet_link: str) -> None:
        """Initializes the provisioner with task details."""
        self.download_id = download_id
        self.magnet_link = magnet_link
        self.project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        self.zone = os.environ.get("GOOGLE_CLOUD_ZONE", "us-central1-a")
        self.instance_name = f"pfirsichfest-vm-{self.download_id}"
        self.client = compute_v1.InstancesClient()

    def provision(self) -> str:
        """Executes the Google Cloud API call to spin up the Spot VM."""
        logger.info("Creating Spot VM: %s in %s", self.instance_name, self.zone)

        try:
            instance_resource = self._build_instance_resource()
            operation = self.client.insert(
                project=self.project_id,
                zone=self.zone,
                instance_resource=instance_resource,
            )
            logger.info(
                "VM Creation Operation Name: %s", getattr(operation, "name", "unknown")
            )
        except Exception as e:
            logger.exception("Failed to create VM %s", self.instance_name)
            msg = f"GCP VM Provisioning failed: {e}"
            raise RuntimeError(msg) from e

        return self.instance_name

    def _build_metadata(self) -> compute_v1.Metadata:
        """Constructs the VM metadata payload with the download targets."""
        metadata = compute_v1.Metadata()
        metadata.items = [
            compute_v1.Items(key="MAGNET_LINK", value=self.magnet_link),
            compute_v1.Items(key="DOWNLOAD_ID", value=self.download_id),
        ]
        return metadata

    def _build_disk(self) -> compute_v1.AttachedDisk:
        """Constructs the ephemeral boot disk configuration."""
        return compute_v1.AttachedDisk(
            auto_delete=True,
            boot=True,
            initialize_params=compute_v1.AttachedDiskInitializeParams(
                source_image="global/images/family/ubuntu-2204-lts",
                disk_size_gb=50,
            ),
        )

    def _build_network(self) -> compute_v1.NetworkInterface:
        """Constructs the network interface pointing to the external internet."""
        return compute_v1.NetworkInterface(
            access_configs=[
                compute_v1.AccessConfig(name="External NAT", type_="ONE_TO_ONE_NAT")
            ],
        )

    def _build_instance_resource(self) -> compute_v1.Instance:
        """Assembles the final Compute Engine Instance layout."""
        return compute_v1.Instance(
            name=self.instance_name,
            machine_type=f"zones/{self.zone}/machineTypes/e2-micro",
            disks=[self._build_disk()],
            network_interfaces=[self._build_network()],
            scheduling=compute_v1.Scheduling(
                provisioning_model="SPOT",
                preemptible=True,
            ),
            metadata=self._build_metadata(),
        )

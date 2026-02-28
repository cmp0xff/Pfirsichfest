import logging
import os

from google.cloud import compute_v1  # type: ignore

logger = logging.getLogger(__name__)


def trigger_spot_vm(download_id: str, magnet_link: str) -> str:
    """Provisions an ephemeral Spot VM on Google Compute Engine to handle the download."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    zone = os.environ.get("GOOGLE_CLOUD_ZONE", "us-central1-a")
    source_image = "global/images/family/ubuntu-2204-lts"

    machine_type = f"zones/{zone}/machineTypes/e2-micro"
    instance_name = f"pfirsichfest-vm-{download_id}"

    compute_client = compute_v1.InstancesClient()

    metadata = compute_v1.Metadata()
    metadata.items = [
        compute_v1.Items(key="MAGNET_LINK", value=magnet_link),
        compute_v1.Items(key="DOWNLOAD_ID", value=download_id),
    ]

    scheduling = compute_v1.Scheduling(
        provisioning_model="SPOT",
        preemptible=True,
    )

    disk = compute_v1.AttachedDisk(
        auto_delete=True,
        boot=True,
        initialize_params=compute_v1.AttachedDiskInitializeParams(
            source_image=source_image,
            disk_size_gb=50,
        ),
    )

    network_interface = compute_v1.NetworkInterface(
        access_configs=[
            compute_v1.AccessConfig(name="External NAT", type_="ONE_TO_ONE_NAT")
        ],
    )

    instance = compute_v1.Instance(
        name=instance_name,
        machine_type=machine_type,
        disks=[disk],
        network_interfaces=[network_interface],
        scheduling=scheduling,
        metadata=metadata,
    )

    logger.info("Creating Spot VM: %s in %s", instance_name, zone)

    try:
        operation = compute_client.insert(
            project=project_id,
            zone=zone,
            instance_resource=instance,
        )
        logger.info(
            "VM Creation Operation Name: %s", getattr(operation, "name", "unknown")
        )
    except Exception:
        logger.exception("Failed to create VM %s", instance_name)
        raise

    return instance_name

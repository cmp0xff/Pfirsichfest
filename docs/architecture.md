# Architecture Proposal: Pfirsichfest

This plan defines the architecture for the "Pfirsichfest" project, a Python-based serverless torrent downloading pipeline managed via a Telegram bot, integrating a VPN and sending artifacts directly via Telegram (or GCS for files > 2GB).

## Architecture Highlights
- **Language:** Python 3 (FastAPI/aiogram for the bot, standard scripts for the downloader).
- **Structure:** Monorepo (`Pfirsichfest`) containing the Bot, Downloader, and Infrastructure code.
- **Compute:** Cloud Run for the Bot API, Ephemeral Spot VMs (Compute Engine) for the Downloader.

## Key Architectural Decisions

### 1. The Local Telegram Bot API Server
Because the Downloader VM is already an ephemeral environment, we run the official Telegram Bot API Server Docker container **on the Downloader VM itself** alongside the torrent client. This allows bypassing the standard 50 MB Telegram upload limit (up to 2GB) without paying for a constantly running custom server.

### 2. VPN & Serverless Compute
- **Decision:** Google Compute Engine (Spot VM) for the Downloader.
- **Why:** VPNs use standard protocols (OpenVPN) requiring OS-level privileges. Spinning up an `e2-micro` Spot VM dynamically gives us these privileges for pennies, deleting itself when finished.

### 3. Secrets Management
- **Decision:** Google Secret Manager. Stores API tokens and VPN passwords.

### 4. Infrastructure as Code (OpenTofu)
- **Decision:** Yes, we will use **OpenTofu**.
- **Why it's necessary:** Deploying Cloud Run, setting up IAM permissions to allow the Bot to spawn a VM, creating Storage Buckets, and configuring Secret Manager by clicking around the GCP Console is highly error-prone and hard to reproduce. Having a single `tofu apply` command makes it trivial to deploy (or redeploy if you lose the GCP project). We will define the OpenTofu code in the `/infra` folder.

### 5. Environments (dev, uat, prod)
- **Decision:** Single Environment (Prod).
- **Why:** For a personal utility project, maintaining multi-environment separation introduces unnecessary overhead and costs. A single "production" branch is sufficient. You can test locally using Docker before pushing. 

### 6. Status Queries During Download
- **Decision:** Yes, supported via `/status` command and asynchronous updates.
- **How it works:**
  - When the Bot generates the VM, it assigns it a unique ID (e.g., in a lightweight Firestore DB).
  - The Downloader Python script occasionally queries the Torrent client (aria2) for progress.
  - The Downloader script periodically sends HTTP updates to the Bot, OR the script updates the original Telegram message (e.g., "Downloading: 45% (2.1 MB/s)").
  - You can also proactively message `/status` to the bot, which queries the active instances.

---

## Proposed System Architecture

### 1. Telegram Bot Service (Cloud Run API)
- Python Webhook (using a framework like `aiogram`).
- Uses GCP Compute API to provision the Downloader VM.
- Reads `/status` commands from you.

### 2. Downloader Service (Ephemeral Spot VM)
- Created on-demand by the Bot.
- **Boot Sequence:**
  1. Starts OpenVPN container.
  2. Starts local Telegram Bot API server.
  3. Starts Python Controller + aria2.
  4. Downloads the file, periodically sending progress to Telegram either via the Bot Service or directly querying the API.
  5. Upon finish, uploads file (either directly to Telegram if <2GB, or to GCS if >2GB).
  6. Deletes itself via GCP API.

## Next Steps
- Begin creating the `Pfirsichfest` monorepo structure.
- Draft the OpenTofu infrastructure code to deploy the Bot.

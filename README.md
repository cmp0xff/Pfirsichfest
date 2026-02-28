# Pfirsichfest

A serverless, private torrent downloading pipeline managed via a Telegram bot, integrating a VPN and Google Cloud Storage.

## Architecture Highlights
- **Language:** Python 3
- **Bot:** Google Cloud Run (FastAPI/aiogram) serving as a webhook for Telegram.
- **Downloader:** Google Compute Engine (Spot VMs) spawned dynamically by the Bot to route torrent traffic through a VPN.
- **Storage:** Google Cloud Storage for archiving files larger than 2GB. 
- **Infrastructure as Code:** OpenTofu (`/infra`).

## Project Structure
- `bot/` - The Cloud Run Telegram webhook service.
- `downloader/` - The Dockerfile, OpenVPN templates, and runtime Python controller for the Spot VM.
- `infra/` - OpenTofu configuration to deploy everything securely.
- `docs/` - Project documentation.

## Legal & Usage Disclaimer
This project is provided as an open-source, educational example of serverless infrastructure automation and Telegram bot integration. The authors do not condone piracy or copyright infringement.

**End-users are strictly responsible** for how they deploy and use this pipeline, and for ensuring they have the legal right to download and share the content they request.

> [!WARNING]
> Running BitTorrent clients on public cloud providers (like Google Cloud) may expose your ephemeral VM's IP address to the torrent swarm. Users must ensure that their use of this software complies with all applicable laws and their cloud provider's Terms of Service. Downloading or distributing copyrighted materials without authorization may result in the suspension or termination of your cloud project or billing account by the provider.

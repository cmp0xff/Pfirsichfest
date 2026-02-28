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

# Downloader Service (`/downloader`)

This module contains the `Dockerfile`, OpenVPN templates, and python orchestration logic designed to run inside a highly ephemeral **Google Compute Engine Spot VM**.

## Overview
Because cloud-native platforms like *Cloud Run* strictly block low-level networking changes (like `CAP_NET_ADMIN` needed for a VPN interface), the Bot service spins up this container directly on a cheap E2-Micro VM.

When the container executes `downloader.controller`:
1. Fetches Private VPN credentials from Google Secret Manager.
2. Initializes an `OpenVPN` tunnel.
3. Triggers `aria2` to perform the actual P2P download over the VPN.
4. If the artifact is under 2GB, it attempts to leverage the Telegram Local API upload boundary.
5. If the artifact is over 2GB, it archives the file to Google Cloud Storage.
6. The container instructs the GCP Compute Engine API to **destroy** its own VM.

## Setup
It relies on Conda for dependencies (`environment.yml`), plus standard apt-get packages (`openvpn`, `aria2`). 

Required Secrets in Google Secret Manager to function:
- `vpn-user`
- `vpn-pass`

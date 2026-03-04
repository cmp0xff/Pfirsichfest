# Bot Service (`/bot`)

This module contains the Telegram Bot API Webhook service. It is designed to be deployed to **Google Cloud Run** where it scales to zero.

## Overview
1.  **Framework:** Uses `FastAPI` to expose the HTTP POST webhook endpoint `/webhook`.
2.  **Telegram Client:** Uses `aiogram` to handle structured commands (`/download`, `/status`).
3.  **State Management:** Stores temporary request metadata into Google `firestore`.
4.  **Compute Integrations:** Contains `bot.compute_helper` which dynamically invokes the Google Cloud Compute engine API to spin up the downstream Ephemeral Spot VMs defined in `/downloader`.

## Setup
It relies on Conda for dependencies (`environment.yml`). 
Required Secrets in Google Secret Manager to function:
- `telegram-bot-token`

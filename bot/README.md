# Bot Service (`/bot`)

This module contains the Telegram Bot API Webhook service. It is designed to be deployed to **Google Cloud Run** where it scales to zero.

## Overview
1.  **Framework:** Uses `FastAPI` to expose the HTTP POST webhook endpoint `/webhook`.
2.  **Telegram Client:** Uses `aiogram` to handle structured commands (`/download`, `/status`).
3.  **State Management:** Stores temporary request metadata into Google `firestore`.
4.  **Compute Integrations:** Contains `compute_helper.py` which dynamically invokes the Google Cloud Compute engine API to spin up the downstream Ephemeral Spot VMs defined in `/downloader`.

## Local Development

When running locally without a valid `GOOGLE_CLOUD_PROJECT`, the bot
automatically uses an **in-memory database mock** instead of Google
Firestore. This allows all database-dependent features (`/status`,
`/download` tracking) to work out of the box, with no GCP credentials
required.

The mock is implemented via a `DatabaseClient` protocol in
`database.py`, with an `InMemoryDatabaseClient` backed by a plain
Python `dict`. Data is held in memory and lost on restart, which is
fine for development and testing.

## Setup
It relies on Conda for dependencies (`environment.yml`). 
Required Secrets in Google Secret Manager to function:
- `telegram-bot-token`

## Testing

Run the test suite from the repository root:

```bash
python -m pytest bot/tests/ -v
```

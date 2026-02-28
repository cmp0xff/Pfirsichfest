# Local Webhook Execution (`run_bot_locally.sh`)

This document explains the usage and internal workings of the `bin/run_bot_locally.sh` script.

## Overview
The `run_bot_locally.sh` script is designed to spin up the FastAPI webhook directly on your local machine for testing and development, removing the need to immediately deploy changes to Google Cloud Run.

## What it does
1. **Environment Configuration:** It loads variables from your `.env` file. If `.env` is missing, it will remind you to copy `.env.example`.
2. **Prerequisite Checks:** It verifies that Conda is installed and available in your `PATH`.
3. **Environment Creation:** It ensures that the `pfirsichfest-bot` Conda environment exists. If it does not, it will automatically setup the dependencies.
4. **Server Startup:** It starts the Uvicorn ASGI server with hot-reloading enabled, hosting the Bot locally on `http://localhost:8080`.

## Example Snippet
Here is the core command executed by the script to spin up the server:
```bash
conda run -n pfirsichfest-bot uvicorn bot.main:app --host 0.0.0.0 --port 8080 --reload
```

## Considerations
* **Telegram Webhook HTTPS Requirement:** Telegram strictly requires a public HTTPS URL for webhooks. To receive real Telegram messages locally, you must use a reverse tunneling proxy (like `ngrok http 8080`) and register your temporary HTTPS URL via the Telegram `setWebhook` API.

### How to receive Telegram messages locally using ngrok
**Note:** `ngrok` is a separate third-party tool used to expose your local server to the internet. If you do not have it installed, you can download it from the [official ngrok website](https://ngrok.com/download) and refer to the [ngrok documentation](https://ngrok.com/docs) for setup instructions.

If `ngrok` is installed and available in your `PATH`, the `run_bot_locally.sh` script will automatically:
1. Start an `ngrok` tunnel to your local `8080` port in the background.
2. Query the temporary `ngrok` forwarding URL.
3. Automatically configure your Telegram bot's webhook to use this new URL.
4. Cleanly kill the `ngrok` process and restore state when you exit the script.

If `ngrok` is **not** installed, you will need to perform these steps manually:
1. Start `ngrok` in a separate terminal: `ngrok http 8080`.
2. Copy the temporary HTTPS URL provided.
3. Call `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_NGROK_URL>/webhook` to set the webhook.

> **Warning:** When you are done testing, you will need to manually reverse the webhook back to your production URL (e.g., your Google Cloud Run URL) using the `setWebhook` API method.

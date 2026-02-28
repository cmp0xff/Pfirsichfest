# Google Cloud Platform (GCP) Setup Guide

This document outlines the requisite steps to configure a brand new Google Cloud Project environment for Pfirsichfest.

Because allocating paid infrastructure inherently requires a pre-existing billing account and authenticated CLI mapping, **the `main` GitHub Action pipelines rely on developers configuring this GCP environment manually beforehand.**

We highly recommend maintaining your active experimentation within the `dev` branch. Only merge to `main` when the `gcloud` logic below is completed.

## 1. Install Google Cloud SDK

You will need the `gcloud` CLI tool installed on your local computer to authenticate the deployment.
- Download it here: [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)

Once installed, authenticate your terminal:
```bash
gcloud auth login
gcloud auth application-default login
```

## 2. Automated Project Instantiation

Instead of manually creating projects, linking billing platforms, and tracking terraform variables by hand, utilize the provided initialization pipeline!

First, ensure your `.env` contains the required `TELEGRAM_BOT_TOKEN`, `AUTHORIZED_USER_ID`, and specifically the `GOOGLE_CLOUD_PROJECT` identifier you'd like to reserve.

Then simply run:
```bash
./bin/setup_gcp.sh
```

This script will automatically:
1. Verify you have an active billing account mapped for Spot VM access.
2. Formally lock your GCP Project.
3. Automatically execute OpenTofu (`infra/main.tf`) binding your `.env` tokens into Google Secret Manager natively!

After this point, merging configurations into `main` will successfully interact with the deployed Bot interface.


## 3. Local Webhook Development

You do not need to constantly push to GCP to test your Python changes!
To run the bot locally alongside a hot-reloading ASGI server:

```bash
./bin/run_bot_locally.sh
```
*Note: Because Telegram's Webhook API strictly requires public HTTPS addresses to push updates, you MUST proxy your local `8080` port using an ingress tool like `ngrok http 8080`, and register that temporary URL with the BotFather.*

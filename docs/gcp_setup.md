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
This script will automatically verify billing, formally lock the project, and apply the OpenTofu logic natively.
Here is the core command executed by the script:
```bash
tofu apply -var="..." -auto-approve
```

### Manual Configuration (Alternative)
If you prefer setting up the components by hand, or modifying variables heavily:

Ensure you are authenticated:
```bash
gcloud auth login
gcloud auth application-default login
```

Create and target the core project:
```bash
gcloud projects create "your-pfirsichfest-project-id"
gcloud config set project "your-pfirsichfest-project-id"
```

Because serverless spot VMs require billing infrastructure, link it:
```bash
gcloud alpha billing projects link "your-pfirsichfest-project-id" --billing-account="YOUR-BILLING-ID"
```

Finally, mount your variables and provision the Terraform modules directly.
Here are the core commands executed:
```bash
cd infra/
tofu init
tofu apply -var="telegram_bot_token=YOUR_TOKEN" \
           -var="authorized_user_id=YOUR_TELEGRAM_ID" \
           -var="enable_vpn=false"
```

After either process completes, merging configurations into `main` will successfully interact with the deployed Bot interface!


## 3. Local Webhook Development

You do not need to constantly push to GCP to test your Python changes!
For full instructions on how to run the bot locally alongside a hot-reloading ASGI server, please refer to [run_bot_locally.md](./run_bot_locally.md).

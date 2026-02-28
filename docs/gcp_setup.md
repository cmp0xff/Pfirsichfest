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

## 2. Initialize the Project

Create the overarching project to hold your infrastructure:
```bash
gcloud projects create "your-pfirsichfest-project-id"
gcloud config set project "your-pfirsichfest-project-id"
```

## 3. Link Billing Account

Serverless components cost pennies, but GCP strictly requires an active billing account linked:
```bash
gcloud alpha billing projects link "your-pfirsichfest-project-id" --billing-account="YOUR-BILLING-ID"
```

## 4. Prepare OpenTofu

Ensure your `.env` contains the newly created `GOOGLE_CLOUD_PROJECT` id.
Navigate to the `infra/` folder and initialize the Google Cloud foundations:

```bash
cd infra/
tofu init
tofu apply
```

This ensures the Google Secret Manager buckets, Cloud Run IAM APIs, and Spot VM instantiation permissions are securely locked and generated! After this point, merging configurations into `main` will successfully interact with the deployed Bot interface.

#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Change to project root directory
cd "$(dirname "$0")/.."

echo "🍑 Starting Pfirsichfest GCP Initialization 🍑"

# 1. Load configuration from .env
if [ -f .env ]; then
    echo "Loading configuration from .env..."
    export $(grep -v '^#' .env | xargs)
else
    echo "❌ Error: .env file not found."
    echo "Please copy .env.example to .env and fill in the details first!"
    exit 1
fi

if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "❌ Error: GOOGLE_CLOUD_PROJECT is not set in .env."
    exit 1
fi

PROJECT_ID=$GOOGLE_CLOUD_PROJECT

# 2. Authenticate
echo "Ensuring GCP authentication..."
# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed. Please install from https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# We don't force login if already authenticated, but ensure application-default exists for Tofu
if ! gcloud auth print-access-token &> /dev/null; then
    gcloud auth login
fi

if [ ! -f ~/.config/gcloud/application_default_credentials.json ]; then
    echo "Setting up application default credentials for OpenTofu..."
    gcloud auth application-default login
fi

# 3. Create or Select Project
# Check if project exists and we have access
if ! gcloud projects describe "$PROJECT_ID" &> /dev/null; then
    echo "Project $PROJECT_ID does not exist or you lack permissions. Creating..."
    gcloud projects create "$PROJECT_ID"
else
    echo "Project $PROJECT_ID exists."
fi

gcloud config set project "$PROJECT_ID"

# 4. Billing Account (Required for Cloud Run and Spot VMs)
echo "Checking billing status..."
BILLING_ENABLED=$(gcloud beta billing projects describe "$PROJECT_ID" --format="value(billingEnabled)")

if [ "$BILLING_ENABLED" != "True" ]; then
    echo "⚠️  Project $PROJECT_ID does not have an active billing account attached."
    echo "Billing is strictly required to provision Serverless and Compute resources."
    
    # List available billing accounts
    ACCOUNTS=$(gcloud beta billing accounts list --format="value(name)")
    if [ -z "$ACCOUNTS" ]; then
        echo "❌ Error: No billing accounts found. Please set one up in the Google Cloud Console."
        exit 1
    fi
    
    # For simplicity, if they only have one, we grab it.
    # Otherwise prompt them.
    BILLING_ID=$(echo "$ACCOUNTS" | head -n 1 | awk -F'/' '{print $2}')
    echo "Linking billing account: $BILLING_ID to project $PROJECT_ID..."
    gcloud beta billing projects link "$PROJECT_ID" --billing-account="$BILLING_ID"
fi

# 5. Execute OpenTofu
echo "Initializing Infrastructure with OpenTofu..."
if ! command -v tofu &> /dev/null; then
    echo "❌ Error: OpenTofu 'tofu' CLI is not installed."
    exit 1
fi

cd infra/
tofu init
tofu apply -var="telegram_bot_token=$TELEGRAM_BOT_TOKEN" \
           -var="authorized_user_id=$AUTHORIZED_USER_ID" \
           -var="enable_vpn=$ENABLE_VPN" \
           -var="vpn_user=${VPN_USER:-}" \
           -var="vpn_pass=${VPN_PASS:-}" \
           -auto-approve

echo "✅ GCP Environment successfully provisioned."
echo "You may now deploy the bot via: conda run -n pfirsichfest-bot gcloud run deploy"

#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Change to project root directory
cd "$(dirname "$0")/.."

echo "🍑 Starting Local Pfirsichfest Development Server 🍑"

# 1. Load configuration from .env
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found."
    echo "Please copy .env.example to .env and fill in the details first!"
    exit 1
fi

echo "Checking local pre-requisites..."

if ! command -v conda &> /dev/null; then
    echo "❌ Error: Conda is not installed or available in PATH."
    exit 1
fi

# Ensure conda env exists (silent attempt)
if ! conda env list | grep -q 'pfirsichfest-bot'; then
    echo "Conda environment 'pfirsichfest-bot' not found. Creating it locally..."
    conda env create -f bot/environment.yml
fi

echo "Starting Uvicorn Server on http://localhost:8080"
echo "Note: To receive real Telegram messages locally, you must use something like \`ngrok http 8080\` and set your webhook via the regular Telegram API."

conda run -n pfirsichfest-bot uvicorn bot.main:app --host 0.0.0.0 --port 8080 --reload

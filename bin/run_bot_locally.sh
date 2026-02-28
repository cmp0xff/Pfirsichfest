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

if command -v ngrok &> /dev/null; then
    echo "ngrok found. Automating webhook setup..."
    
    # Load .env to get bot token
    set +e
    source .env
    set -e

    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        echo "❌ Error: TELEGRAM_BOT_TOKEN is not set in .env."
        exit 1
    fi

    # Start ngrok in background
    ngrok http 8080 > /dev/null &
    NGROK_PID=$!
    
    # Cleanup trap
    cleanup() {
        echo "Stopping Uvicorn and ngrok..."
        kill $NGROK_PID 2>/dev/null || true
    }
    trap cleanup EXIT INT TERM
    
    echo "Waiting for ngrok to initialize..."
    sleep 3
    
    # Fetch public URL safely
    NGROK_URL=$(curl -s localhost:4040/api/tunnels | python3 -c "import sys, json; print(next((t['public_url'] for t in json.load(sys.stdin)['tunnels'] if t['public_url'].startswith('https')), ''))" 2>/dev/null || true)
    
    if [ -z "$NGROK_URL" ]; then
        echo "⚠️ Failed to extract ngrok URL. Skipping automated webhook setup."
    else
        echo "✅ ngrok tunnel established: $NGROK_URL"
        echo "Setting Telegram webhook..."
        RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" -d "url=${NGROK_URL}/webhook" || true)
        if echo "$RESPONSE" | grep -q '"ok":true'; then
             echo "✅ Webhook successfully set!"
        else
             echo "⚠️ Failed to set webhook: $RESPONSE"
        fi
    fi
else
    echo "⚠️ ngrok not installed in PATH. Skipping automated webhook setup."
    echo "Note: To receive real Telegram messages locally, you must use something like \`ngrok http 8080\` and set your webhook via the regular Telegram API."
    echo "      See docs/run_bot_locally.md for detailed instructions on using ngrok."
fi

echo "Starting Uvicorn Server on http://localhost:8080"
conda run --no-capture-output -n pfirsichfest-bot uvicorn bot.main:app --host 0.0.0.0 --port 8080 --reload

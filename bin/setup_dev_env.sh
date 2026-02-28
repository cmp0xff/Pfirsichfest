#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Change to project root directory
cd "$(dirname "$0")/.."

echo "🍑 Starting Pfirsichfest Developer Environment Setup 🍑"

if ! command -v conda &> /dev/null; then
    echo "❌ Error: Conda is not installed or available in PATH."
    exit 1
fi

echo "Creating the 'pfirsichfest-bot' environment..."
# Check if env exists
if conda env list | grep -q 'pfirsichfest-bot'; then
    echo "Environment 'pfirsichfest-bot' already exists. Updating..."
    conda env update -f bot/environment.yml --prune
else
    conda env create -f bot/environment.yml
fi
echo "✅ 'pfirsichfest-bot' environment ready."

echo "Creating the 'pfirsichfest-downloader' environment..."
if conda env list | grep -q 'pfirsichfest-downloader'; then
    echo "Environment 'pfirsichfest-downloader' already exists. Updating..."
    conda env update -f downloader/environment.yml --prune
else
    conda env create -f downloader/environment.yml
fi
echo "✅ 'pfirsichfest-downloader' environment ready."

echo "You can now select these Conda environments as your target Python Interpreters in VSCode!"
echo "If you use the 'pfirsichfest.code-workspace' file, the contexts are automatically routed."

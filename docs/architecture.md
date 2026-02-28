# Pfirsichfest Architecture & Documentation

## Overview
Pfirsichfest is a private, serverless proxy downloader. It allows a single authorized user to send magnet links to a Telegram Bot, which spins up a secure ephemeral VM (Spot VM). The VM connects to an optional VPN, downloads the file using `aria2`, uploads it back to Telegram or Google Cloud Storage, and then immediately destroys itself to save costs.

## For Users

### Getting Started
Because this bot provides direct execution access to cloud billing infrastructure, it uses strict ownership validation. It will **only respond to the Telegram ID configured in `AUTHORIZED_USER_ID`**. Any other users attempting to message the bot will be ignored silently.

### Commands
- `/start` - Displays the welcome message.
- `/help` - Displays detailed information about how to use the bot and its limits.
- `/download <magnet_link>` - Initiates a secure download process. The bot will automatically spin up an ephemeral Google Compute Engine VM and track its status.
- `/status` - Prompts the bot to query Firestore and return the active status of all your ongoing downloads.

### Storage Limits
- **Files < 2GB**: Will be uploaded directly back to you in the Telegram chat securely.
- **Files > 2GB**: Will be archived securely to your private Google Cloud Storage bucket (due to Telegram Bot API native limits).

---

## For Developers

### Prerequisites
- Python 3.13 via Conda
- OpenTofu (`tofu`)
- Google Cloud SDK (`gcloud`)

### 1. Infrastructure Setup
1. Copy `.env.example` to `.env`. Fill out your specific `TELEGRAM_BOT_TOKEN`, `AUTHORIZED_USER_ID`, and optional VPN connection parameters.
2. Run `./bin/setup_gcp.sh`. This script will automatically:
   - Authenticate your local environment (`gcloud auth login`).
   - Verify your Cloud Billing Account.
   - Execute OpenTofu (`infra/main.tf`) to securely provision the Google Cloud Storage bucket, the IAM Service Accounts, and inject your `.env` tokens into Google Secret Manager natively:
     ```bash
     tofu init
     tofu apply -var="..." -auto-approve
     ```

### 2. Conda & IDE Setup
You must configure the underlying Python runtimes before modifying the Bot logic locally. 
Run the developer setup script to compile the two distinct Conda environments (`pfirsichfest-bot` and `pfirsichfest-downloader`):
```bash
./bin/setup_dev_env.sh
```
*(Under the hood, this executes `conda env create -f bot/environment.yml` and `conda env create -f downloader/environment.yml` to set up environments)*

Alternatively, you may build the environments manually:
```bash
conda env create -f bot/environment.yml
conda env create -f downloader/environment.yml
```

*Note: We included a `pfirsichfest.code-workspace` definition. If you open this file inside VSCode, it separates the root folder horizontally, automatically applying the respective localized Conda environments to your workspace.*

### 3. Local Webhook Execution 
You don't need to deploy immediately to Cloud Run to test changes!
Use the local run script to spin up the FastAPI webhook directly on your machine (for details, see [run_bot_locally.md](./run_bot_locally.md)):
```bash
./bin/run_bot_locally.sh
```
*(This will execute `conda run -n pfirsichfest-bot uvicorn bot.main:app --host 0.0.0.0 --port 8080 --reload` behind the scenes)*
*Note: Telegram requires a public HTTPS URL for webhooks. You must use a reverse tunneling proxy (like `ngrok`) to pipe your public traffic to `localhost:8080`, and register that HTTPS URL via the Telegram `setWebhook` API.*

### 4. Cloud Deployment
Once your changes are verified locally, merge your branch to `main`. The underlying GitHub Actions will format, type-check, and automate tests.

To manually deploy the bot to Google Cloud Run:
```bash
conda run -n pfirsichfest-bot gcloud run deploy
```

### 5. Code Quality & Monitoring
Standard Python `logging` modules are utilized universally. Google Cloud automatically bridges these `stdout` interfaces into **Cloud Logging** natively (for both Cloud Run containers and Spot VMs), enabling seamless dashboard aggregation without configuring explicit stackdriver packages.

Code styling is checked strictly before commits:
- **Ruff**: Enforces rigorous formatting.
- **Pyright**: Enforces strict OOP type-checking.
Run `pre-commit run --all-files` to test your code locally.

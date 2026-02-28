"""Telegram Bot Webhook Service for Pfirsichfest."""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Update
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from google.cloud import (
    firestore,  # type: ignore - Missing type stubs for google-cloud-firestore
    secretmanager,  # type: ignore - Missing type stubs for google-cloud-secret-manager
)

from .compute_helper import SpotVMProvisioner

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Globals to hold our uninstantiated clients until startup
bot: Bot | None = None
dp: Dispatcher = Dispatcher()
db: firestore.Client | None = None

WEBHOOK_PATH = "/webhook"


# Load local environment variables (does not override existing OS env vars in Cloud)
load_dotenv(override=False)


def get_secret(secret_id: str, version_id: str = "latest") -> str | None:
    """Fetches a secret from environment (.env) or Google Secret Manager."""
    # Priority 1: .env or Local System OS Env
    if env_val := os.getenv(secret_id.upper().replace("-", "_")):
        return env_val

    # Priority 2: Google Secret Manager
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if not project_id or project_id == "your-gcp-project-id":
        logger.warning(
            "No valid GOOGLE_CLOUD_PROJECT set. Using dummy token for %s", secret_id
        )
        if secret_id == "telegram-bot-token":
            return "123456789:dummy-token-for-local-testing"
        return "dummy-secret"

    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("UTF-8")
        return str(payload)
    except Exception:
        logger.exception("Failed to fetch secret %s", secret_id)
        return None


@dp.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    """Handles the /start command."""
    await message.answer(
        "Welcome to the Pfirsichfest P2P Bot! 🍑\n"
        "Send /download <code>&lt;magnet_link&gt;</code> to begin a secure download instance.\n"
        "Send /status to check active instances.\n"
        "Send /help for more information.",
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Handles the /help command."""
    await message.answer(
        "🍑 <b>Pfirsichfest Bot Help</b> 🍑\n\n"
        "This bot is a private, serverless torrent downloader.\n\n"
        "<b>Commands:</b>\n"
        "/download <code>&lt;magnet_link&gt;</code> - Starts a secure ephemeral VM to download the torrent.\n"
        "/status - Shows the progress of active downloads.\n"
        "/help - Displays this message.\n\n"
        "Files under 2GB are sent directly here. Larger files are securely archived to your Google Cloud Storage bucket.",
        parse_mode=ParseMode.HTML,
    )


@dp.message(Command("download"))
async def cmd_download(message: types.Message, command: Command) -> None:
    """Handles the /download command."""
    if command.args:
        magnet_link = command.args.strip()
    elif message.reply_to_message and message.reply_to_message.text:
        magnet_link = message.reply_to_message.text.strip()
    else:
        await message.answer(
            "Please provide a magnet link: /download <code>&lt;magnet_link&gt;</code>"
        )
        return

    if not magnet_link.startswith("magnet:?"):
        await message.answer("That doesn't look like a valid magnet link.")
        return

    reply = await message.answer("Initializing secure downloader instance... ⏳")

    download_id = f"{message.chat.id}_{message.message_id}"
    if db:
        doc_ref = db.collection("downloads").document(download_id)
        doc_ref.set(
            {
                "chat_id": message.chat.id,
                "status": "provisioning_vm",
                "magnet": magnet_link,
                "message_id": reply.message_id,
            },
        )

    try:
        provisioner = SpotVMProvisioner(
            download_id=download_id, magnet_link=magnet_link
        )
        instance_name = provisioner.provision()

        if bot:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=reply.message_id,
                text=f"Started VM instance <code>{instance_name}</code>.\nWill report back on progress.",
            )
    except Exception:
        logger.exception("Failed to start VM")
        if bot:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=reply.message_id,
                text="❌ Failed to provision downstream VM instance.",
            )


@dp.message(Command("status"))
async def cmd_status(message: types.Message) -> None:
    """Handles the /status command."""
    if not db:
        await message.answer("Database connection not initialized.")
        return

    active_downloads = (
        db.collection("downloads").where("status", "!=", "completed").stream()
    )

    status_text = "📊 <b>Active Downloads:</b>\n\n"
    count: int = 0
    for doc in active_downloads:
        data = doc.to_dict()
        if data and data.get("chat_id") == message.chat.id:
            count += 1
            status_text += (
                f"ID: <code>{doc.id}</code>\nStatus: {data.get('status')}\n---\n"
            )

    if count == 0:
        status_text = "No active downloads."

    await message.answer(status_text, parse_mode=ParseMode.HTML)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan manager for starting up AIogram."""
    logger.info("Starting up FastAPI application...")

    global db  # noqa: PLW0603
    gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if gcp_project and gcp_project != "your-gcp-project-id":
        db = firestore.Client(project=gcp_project)
        logger.info("Firestore client initialized for %s.", gcp_project)
    else:
        logger.warning("No valid GOOGLE_CLOUD_PROJECT set. Running without Firestore.")

    global bot  # noqa: PLW0603
    token = get_secret("telegram-bot-token")
    if not token:
        logger.error("Could not retrieve telegram bot token. Bot will fail.")
    else:
        bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        logger.info("Bot instance created.")

    yield

    logger.info("Shutting down FastAPI application...")
    if bot:
        await bot.session.close()


app = FastAPI(lifespan=lifespan)


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request) -> dict[str, str]:
    """Receives Telegram Webhook payload updates."""
    if bot is None:
        raise HTTPException(status_code=500, detail="Bot not initialized")

    try:
        body = await request.json()
        update = Update(**body)

        # Authorization Check
        authorized_id_str = get_secret("authorized-user-id")
        user_id = None
        if update.message and update.message.from_user:
            user_id = update.message.from_user.id
        elif update.callback_query and update.callback_query.from_user:
            user_id = update.callback_query.from_user.id

        if authorized_id_str and user_id and str(user_id) != authorized_id_str:
            logger.warning("Unauthorized access attempt from %s", user_id)
            return {"status": "ok"}  # Return 200 OK so Telegram doesn't retry

        await dp.feed_update(bot=bot, update=update)
        return {"status": "ok"}
    except Exception:
        logger.exception("Error processing update")
        raise HTTPException(status_code=500, detail="Failed to process update")  # noqa: B904


@app.get("/health")
def health_check() -> dict[str, str]:
    """Returns a 200 health check response."""
    return {"status": "healthy"}

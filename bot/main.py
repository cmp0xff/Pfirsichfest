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
from fastapi import FastAPI, HTTPException, Request
from google.cloud import (
    firestore,  # type: ignore
    secretmanager,  # type: ignore
)

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Globals to hold our uninstantiated clients until startup
bot: Bot | None = None
dp: Dispatcher = Dispatcher()
db: firestore.Client | None = None

WEBHOOK_PATH = "/webhook"


def get_secret(secret_id: str, version_id: str = "latest") -> str | None:
    """Fetches a secret from Google Secret Manager."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if not project_id:
        logger.warning(
            "No GOOGLE_CLOUD_PROJECT set. Using dummy token for %s", secret_id
        )
        return "123456789:dummy-token-for-local-testing"

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
        "Send `/download <magnet_link>` to begin a secure download instance.\n"
        "Send `/status` to check active instances.",
    )


@dp.message(Command("download"))
async def cmd_download(message: types.Message, command: Command) -> None:
    """Handles the /download command."""
    if command.args:
        magnet_link = command.args.strip()
    elif message.reply_to_message and message.reply_to_message.text:
        magnet_link = message.reply_to_message.text.strip()
    else:
        await message.answer("Please provide a magnet link: `/download <magnet_link>`")
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
        # Example of where to call trigger_spot_vm(download_id, magnet_link)
        if bot:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=reply.message_id,
                text=f"Started VM instance `pfirsichfest-vm-{download_id}`.\nWill report back on progress.",
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

    status_text = "📊 **Active Downloads:**\n\n"
    count: int = 0
    for doc in active_downloads:
        data = doc.to_dict()
        if data and data.get("chat_id") == message.chat.id:
            count += 1
            status_text += f"ID: `{doc.id}`\nStatus: {data.get('status')}\n---\n"

    if count == 0:
        status_text = "No active downloads."

    await message.answer(status_text, parse_mode=ParseMode.MARKDOWN)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan manager for starting up AIogram."""
    logger.info("Starting up FastAPI application...")

    global db  # noqa: PLW0603
    if os.environ.get("GOOGLE_CLOUD_PROJECT", "") != "":
        db = firestore.Client()
        logger.info("Firestore client initialized.")

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
        await dp.feed_update(bot=bot, update=update)
        return {"status": "ok"}
    except Exception:
        logger.exception("Error processing update")
        raise HTTPException(status_code=500, detail="Failed to process update")  # noqa: B904


@app.get("/health")
def health_check() -> dict[str, str]:
    """Returns a 200 health check response."""
    return {"status": "healthy"}

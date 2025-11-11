from telethon import TelegramClient, events
import os
import asyncio
import requests
import logging

logger = logging.getLogger(__name__)

API_ID = int(os.environ.get("API_ID", 24289127))
API_HASH = os.environ.get("API_HASH", "cd63113435f4997590ee4a308fbf1e2c")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
RAILWAY_API_URL = os.environ.get("RAILWAY_API_URL")
CHAT_ID = os.environ.get("CHAT_ID")

bot = TelegramClient('bot_session', API_ID, API_HASH)

# ... [REST OF THE CODE SAMA, TAPI PASTIKAN GAK PAKE AIOHTTP] ...

async def start_bot():
    """Start the bot"""
    try:
        await bot.start(bot_token=BOT_TOKEN)
        logger.info("🤖 JINX Bot started successfully!")
        await bot.run_until_disconnected()
    except Exception as e:
        logger.error(f"Bot start error: {e}")
        raise

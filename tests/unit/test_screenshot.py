"""
Comprehensive test suite for the screenshot module.

This module tests screenshot capture, encryption, database operations,
and the ScreenshotCapture class functionality.
"""

import pytest
import os
import sys
import sqlite3
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from cryptography.fernet import Fernet as RealFernet
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from services.screenshot import (
        ScreenshotCapture, 
        start_screenshot_capture, 
        stop_screenshot_capture,
        get_recent_screenshots,
        get_screenshot_by_id,
        get_screenshot_stats,
        delete_screenshot
    )
except ImportError as e:
    pytest.skip(f"Screenshot module not available: {e}", allow_module_level=True)


class TestScreenshotCapture:
    """Test cases for the ScreenshotCapture class."""
    
    @pytest.mark.unit
    def test_screenshot_capture_init(self, temp_dir, temp_db_path):
        """Test ScreenshotCapture initialization."""
        with patch('services.screenshot.Fernet') as mock_fernet, \
             patch('services.screenshot.Fernet.generate_key', return_value=b'test_key'):
            
            capture = ScreenshotCapture(db_path=temp_db_path, interval=60)
            
            assert capture.db_path == temp_db_path
            assert capture.interval == 60
            assert capture.running is False
            assert capture.thread is None
            assert capture.cipher is not None
    
    @pytest.mark.unit
    def test_get_or_create_key_existing(self, temp_dir):
        """Test getting existing encryption key."""
        key_file = os.path.join(temp_dir, "screenshot_key.key")
        test_key = b"test_encryption_key_12345"
        
        with open(key_file, "wb") as f:
            f.write(test_key)
        
        with patch('services.screenshot.Fernet') as mock_fernet:
            # Change working directory so production code finds the key
            cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                capture = ScreenshotCapture(db_path=os.path.join(temp_dir, "test.db"))
            finally:
                os.chdir(cwd)
            mock_fernet.assert_called_with(test_key)
    
    @pytest.mark.unit
    def test_get_or_create_key_new(self, temp_dir):
        """Test creating new encryption key."""
        with patch('services.screenshot.Fernet') as mock_fernet, \
             patch('services.screenshot.Fernet.generate_key', return_value=b'new_key'):
            
            # Change working directory so production code writes key into temp_dir
            cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                capture = ScreenshotCapture(db_path=os.path.join(temp_dir, "test.db"))
            finally:
                os.chdir(cwd)
            
            # Verify key file was created
            key_file = os.path.join(temp_dir, "screenshot_key.key")
            assert os.path.exists(key_file)
            mock_fernet.assert_called_with(b'new_key')
    
    @pytest.mark.unit
    def test_init_database(self, temp_dir, temp_db_path):
        """Test database initialization."""
        with patch('services.screenshot.Fernet') as mock_fernet, \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()):
            capture = ScreenshotCapture(db_path=temp_db_path)
            
            # Verify database was created
            assert os.path.exists(temp_db_path)
            
            # Verify table structure
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='screenshots'")
            assert cursor.fetchone() is not None
            
            # Verify indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
            assert 'idx_timestamp' in indexes
            assert 'idx_application' in indexes
            
            conn.close()
    
    @pytest.mark.unit
    def test_get_active_window_info_success(self, mock_win32gui):
        """Test getting active window information successfully."""
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.name.return_value = 'test_app.exe'
            
            capture = ScreenshotCapture()
            window_info = capture._get_active_window_info()
            
            assert window_info['application'] == 'test_app.exe'
            assert window_info['window_title'] == 'Test Window'
            assert window_info['pid'] == 12345
    
    @pytest.mark.unit
    def test_get_active_window_info_error(self):
        """Test getting active window information with error."""
        with patch('win32gui.GetForegroundWindow', side_effect=Exception("Window error")):
            capture = ScreenshotCapture()
            window_info = capture._get_active_window_info()
            
            assert window_info['application'] == 'Unknown'
            assert window_info['window_title'] == 'Unknown'
            assert window_info['pid'] == 0
    
    @pytest.mark.unit
    def test_capture_screenshot_success(self, mock_pil_imagegrab):
        """Test successful screenshot capture."""
        capture = ScreenshotCapture()
        img_data = capture._capture_screenshot()
        
        assert img_data is not None
        assert isinstance(img_data, bytes)
    
    @pytest.mark.unit
    def test_capture_screenshot_error(self):
        """Test screenshot capture with error."""
        with patch('PIL.ImageGrab.grab', side_effect=Exception("Capture error")):
            capture = ScreenshotCapture()
            img_data = capture._capture_screenshot()
            
            assert img_data is None
    
    @pytest.mark.unit
    def test_encrypt_decrypt_data(self, temp_dir, temp_db_path):
        """Test data encryption and decryption."""
        with patch('services.screenshot.Fernet') as mock_fernet, \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()):
            mock_cipher = Mock()
            mock_cipher.encrypt.return_value = b'encrypted_data'
            mock_cipher.decrypt.return_value = b'original_data'
            mock_fernet.return_value = mock_cipher
            
            capture = ScreenshotCapture(db_path=temp_db_path)
            test_data = b'test_data'
            
            encrypted = capture._encrypt_data(test_data)
            decrypted = capture._decrypt_data(encrypted)
            
            assert encrypted == b'encrypted_data'
            assert decrypted == b'original_data'
            mock_cipher.encrypt.assert_called_once_with(test_data)
            mock_cipher.decrypt.assert_called_once_with(b'encrypted_data')
    
    @pytest.mark.unit
    def test_calculate_hash(self, temp_dir, temp_db_path):
        """Test hash calculation."""
        with patch('services.screenshot.Fernet'), \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()):
            capture = ScreenshotCapture(db_path=temp_db_path)
            test_data = b'test_data'
            
            hash1 = capture._calculate_hash(test_data)
            hash2 = capture._calculate_hash(test_data)
            
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA-256 hex length
            assert isinstance(hash1, str)
    
    @pytest.mark.unit
    def test_save_screenshot_success(self, temp_dir, temp_db_path, mock_screenshot_data):
        """Test successful screenshot saving."""
        with patch('services.screenshot.Fernet') as mock_fernet, \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()):
            mock_cipher = Mock()
            mock_cipher.encrypt.return_value = b'encrypted_data'
            mock_fernet.return_value = mock_cipher
            
            capture = ScreenshotCapture(db_path=temp_db_path)
            window_info = mock_screenshot_data['window_info']
            
            result = capture.save_screenshot(mock_screenshot_data['image_data'], window_info)
            
            assert result is True
            
            # Verify data was saved to database
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM screenshots")
            count = cursor.fetchone()[0]
            assert count == 1
            
            # Verify saved data
            cursor.execute("SELECT application, window_title, encrypted_data, file_hash FROM screenshots")
            row = cursor.fetchone()
            assert row[0] == 'test_app.exe'
            assert row[1] == 'Test Application'
            assert row[2] == b'encrypted_data'
            assert row[3] is not None
            
            conn.close()
    
    @pytest.mark.unit
    def test_save_screenshot_no_data(self, temp_dir, temp_db_path):
        """Test saving screenshot with no image data."""
        with patch('services.screenshot.Fernet'), \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()):
            capture = ScreenshotCapture(db_path=temp_db_path)
            window_info = {'application': 'test.exe', 'window_title': 'Test'}
            
            result = capture.save_screenshot(None, window_info)
            
            assert result is False
    
    @pytest.mark.unit
    def test_save_screenshot_error(self, temp_dir, temp_db_path, mock_screenshot_data):
        """Test saving screenshot with database error."""
        with patch('services.screenshot.Fernet') as mock_fernet, \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()):
            
            mock_cipher = Mock()
            mock_cipher.encrypt.return_value = b'encrypted_data'
            mock_fernet.return_value = mock_cipher
            
            capture = ScreenshotCapture(db_path=temp_db_path)
            window_info = mock_screenshot_data['window_info']
            
            # Trigger DB error when saving
            with patch('sqlite3.connect', side_effect=Exception("DB Error")):
                result = capture.save_screenshot(mock_screenshot_data['image_data'], window_info)
            
            assert result is False
    
    @pytest.mark.unit
    def test_capture_and_save(self, temp_dir, temp_db_path, mock_screenshot_data):
        """Test capture and save functionality."""
        with patch('services.screenshot.Fernet') as mock_fernet, \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()), \
             patch.object(ScreenshotCapture, '_get_active_window_info', 
                         return_value=mock_screenshot_data['window_info']), \
             patch.object(ScreenshotCapture, '_capture_screenshot', 
                         return_value=mock_screenshot_data['image_data']):
            
            mock_cipher = Mock()
            mock_cipher.encrypt.return_value = b'encrypted_data'
            mock_fernet.return_value = mock_cipher
            
            capture = ScreenshotCapture(db_path=temp_db_path)
            capture.capture_and_save()
            
            # Verify screenshot was saved
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM screenshots")
            count = cursor.fetchone()[0]
            assert count == 1
            conn.close()
    
    @pytest.mark.unit
    def test_start_capture(self, temp_dir, temp_db_path):
        """Test starting screenshot capture."""
        with patch('services.screenshot.Fernet'), \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()), \
             patch('threading.Thread') as mock_thread:
            
            capture = ScreenshotCapture(db_path=temp_db_path)
            capture.start_capture()
            
            assert capture.running is True
            mock_thread.assert_called_once()
    
    @pytest.mark.unit
    def test_stop_capture(self, temp_dir, temp_db_path):
        """Test stopping screenshot capture."""
        with patch('services.screenshot.Fernet'), \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()):
            capture = ScreenshotCapture(db_path=temp_db_path)
            capture.running = True
            capture.thread = Mock()
            capture.thread.join = Mock()
            
            capture.stop_capture()
            
            assert capture.running is False
            capture.thread.join.assert_called_once()
    
    @pytest.mark.unit
    def test_get_screenshots_with_filters(self, temp_dir, temp_db_path, mock_screenshot_records):
        """Test getting screenshots with various filters."""
        with patch('services.screenshot.Fernet'), \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()):
            capture = ScreenshotCapture(db_path=temp_db_path)
            
            # Insert test data
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            for record in mock_screenshot_records:
                cursor.execute('''
                    INSERT INTO screenshots (id, timestamp, application, window_title, encrypted_data, file_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (record[0], record[1], record[2], record[3], b'blob', record[4]))
            conn.commit()
            conn.close()
            
            # Test without filters
            results = capture.get_screenshots(limit=10)
            assert len(results) == 3
            
            # Test with application filter
            results = capture.get_screenshots(limit=10, application='minecraft.exe')
            assert len(results) == 1
            assert results[0][2] == 'minecraft.exe'
            
            # Test with date filters
            results = capture.get_screenshots(
                limit=10, 
                start_date='2024-01-01T09:59:00',
                end_date='2024-01-01T10:01:30'
            )
            assert len(results) == 2
    
    @pytest.mark.unit
    def test_get_screenshot_data(self, temp_dir, temp_db_path):
        """Test getting screenshot data by ID."""
        with patch('services.screenshot.Fernet') as mock_fernet, \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()):
            mock_cipher = Mock()
            mock_cipher.decrypt.return_value = b'decrypted_image_data'
            mock_fernet.return_value = mock_cipher
            
            capture = ScreenshotCapture(db_path=temp_db_path)
            
            # Insert test data
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO screenshots (id, timestamp, application, window_title, encrypted_data, file_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (1, '2024-01-01T10:00:00', 'test.exe', 'Test', b'encrypted_data', 'hash1'))
            conn.commit()
            conn.close()
            
            # Test getting data
            data = capture.get_screenshot_data(1)
            assert data == b'decrypted_image_data'
            mock_cipher.decrypt.assert_called_once_with(b'encrypted_data')
            
            # Test getting non-existent data
            data = capture.get_screenshot_data(999)
            assert data is None
    
    @pytest.mark.unit
    def test_get_stats(self, temp_dir, temp_db_path, mock_screenshot_records):
        """Test getting screenshot statistics."""
        with patch('services.screenshot.Fernet'), \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()):
            capture = ScreenshotCapture(db_path=temp_db_path)
            
            # Insert test data
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            for record in mock_screenshot_records:
                cursor.execute('''
                    INSERT INTO screenshots (id, timestamp, application, window_title, encrypted_data, file_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (record[0], record[1], record[2], record[3], b'blob', record[4]))
            conn.commit()
            conn.close()
            
            stats = capture.get_stats()
            
            assert stats['total_screenshots'] == 3
            assert len(stats['applications']) == 3
            assert stats['date_range'] == ('2024-01-01T10:00:00', '2024-01-01T10:02:00')
            
            # Check application counts
            app_counts = dict(stats['applications'])
            assert app_counts['minecraft.exe'] == 1
            assert app_counts['chrome.exe'] == 1
            assert app_counts['notepad.exe'] == 1

            # Ensure no lingering locks on Windows
            del capture
            _c = sqlite3.connect(temp_db_path)
            _c.close()


class TestScreenshotModuleFunctions:
    """Test cases for module-level functions."""
    
    @pytest.mark.unit
    def test_start_screenshot_capture(self, temp_dir, temp_db_path):
        """Test starting screenshot capture via module function."""
        with patch('services.screenshot.Fernet'), \
             patch('services.screenshot.screenshot_capture') as mock_capture:
            
            start_screenshot_capture(interval=45)
            
            assert mock_capture.interval == 45
            mock_capture.start_capture.assert_called_once()
    
    @pytest.mark.unit
    def test_stop_screenshot_capture(self, temp_dir, temp_db_path):
        """Test stopping screenshot capture via module function."""
        with patch('services.screenshot.screenshot_capture') as mock_capture:
            stop_screenshot_capture()
            mock_capture.stop_capture.assert_called_once()
    
    @pytest.mark.unit
    def test_get_recent_screenshots(self, temp_dir, temp_db_path):
        """Test getting recent screenshots via module function."""
        with patch('services.screenshot.screenshot_capture') as mock_capture:
            mock_capture.get_screenshots.return_value = [('test', 'data')]
            
            result = get_recent_screenshots(limit=5, application='test.exe')
            
            mock_capture.get_screenshots.assert_called_once_with(limit=5, application='test.exe')
            assert result == [('test', 'data')]
    
    @pytest.mark.unit
    def test_get_screenshot_by_id(self, temp_dir, temp_db_path):
        """Test getting screenshot by ID via module function."""
        with patch('services.screenshot.screenshot_capture') as mock_capture:
            mock_capture.get_screenshot_data.return_value = b'image_data'
            
            result = get_screenshot_by_id(123)
            
            mock_capture.get_screenshot_data.assert_called_once_with(123)
            assert result == b'image_data'
    
    @pytest.mark.unit
    def test_get_screenshot_stats(self, temp_dir, temp_db_path):
        """Test getting screenshot stats via module function."""
        with patch('services.screenshot.screenshot_capture') as mock_capture:
            mock_stats = {'total_screenshots': 10, 'applications': []}
            mock_capture.get_stats.return_value = mock_stats
            
            result = get_screenshot_stats()
            
            mock_capture.get_stats.assert_called_once()
            assert result == mock_stats
    
    @pytest.mark.unit
    def test_delete_screenshot_success(self):
        """Test successful screenshot deletion."""
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = Mock()
            mock_cursor.rowcount = 1
            mock_cursor.execute = Mock()
            mock_conn = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            result = delete_screenshot(123)
            
            assert result is True
            mock_cursor.execute.assert_called_once_with('DELETE FROM screenshots WHERE id = ?', (123,))
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()
    
    @pytest.mark.unit
    def test_delete_screenshot_not_found(self):
        """Test deleting non-existent screenshot."""
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = Mock()
            mock_cursor.rowcount = 0
            mock_cursor.execute = Mock()
            mock_conn = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            result = delete_screenshot(999)
            
            assert result is False
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()
    
    @pytest.mark.unit
    def test_delete_screenshot_error(self):
        """Test screenshot deletion with database error."""
        with patch('sqlite3.connect', side_effect=Exception("DB Error")):
            result = delete_screenshot(123)
            
            assert result is False


class TestScreenshotIntegration:
    """Integration tests for screenshot functionality."""
    
    @pytest.mark.integration
    def test_full_screenshot_workflow(self, temp_dir, temp_db_path, mock_screenshot_data):
        """Test complete screenshot capture and retrieval workflow."""
        with patch('services.screenshot.Fernet') as mock_fernet, \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()), \
             patch.object(ScreenshotCapture, '_get_active_window_info', 
                         return_value=mock_screenshot_data['window_info']), \
             patch.object(ScreenshotCapture, '_capture_screenshot', 
                         return_value=mock_screenshot_data['image_data']):
            
            mock_cipher = Mock()
            mock_cipher.encrypt.return_value = b'encrypted_data'
            mock_cipher.decrypt.return_value = mock_screenshot_data['image_data']
            mock_fernet.return_value = mock_cipher
            
            # Create capture instance
            capture = ScreenshotCapture(db_path=temp_db_path)
            
            # Capture and save screenshot
            capture.capture_and_save()
            
            # Verify screenshot was saved
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM screenshots")
            count = cursor.fetchone()[0]
            assert count == 1
            
            # Get screenshot data
            cursor.execute("SELECT id FROM screenshots LIMIT 1")
            screenshot_id = cursor.fetchone()[0]
            conn.close()
            
            # Retrieve screenshot data
            retrieved_data = capture.get_screenshot_data(screenshot_id)
            assert retrieved_data == mock_screenshot_data['image_data']
            
            # Get statistics
            stats = capture.get_stats()
            assert stats['total_screenshots'] == 1
            assert stats['applications'][0][0] == 'test_app.exe'
    
    @pytest.mark.integration
    def test_screenshot_capture_threading(self, temp_dir, temp_db_path):
        """Test screenshot capture in threading environment."""
        with patch('services.screenshot.Fernet') as mock_fernet, \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()), \
             patch.object(ScreenshotCapture, '_get_active_window_info', 
                         return_value={'application': 'test.exe', 'window_title': 'Test', 'pid': 123}), \
             patch.object(ScreenshotCapture, '_capture_screenshot', 
                         return_value=b'test_image_data'), \
             patch('threading.Thread') as mock_thread:
            
            mock_cipher = Mock()
            mock_cipher.encrypt.return_value = b'encrypted_data'
            mock_fernet.return_value = mock_cipher
            
            capture = ScreenshotCapture(db_path=temp_db_path, interval=1)
            
            # Start capture
            capture.start_capture()
            assert capture.running is True
            
            # Stop capture
            capture.stop_capture()
            assert capture.running is False


class TestScreenshotEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.unit
    def test_screenshot_capture_with_invalid_image_data(self, temp_dir, temp_db_path):
        """Test screenshot capture with invalid image data."""
        with patch('services.screenshot.Fernet'), \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()):
            capture = ScreenshotCapture(db_path=temp_db_path)
            window_info = {'application': 'test.exe', 'window_title': 'Test', 'pid': 123}
            
            # Test with empty data
            result = capture.save_screenshot(b'', window_info)
            assert result is False
            
            # Test with None data
            result = capture.save_screenshot(None, window_info)
            assert result is False
    
    
    @pytest.mark.unit
    def test_concurrent_database_access(self, temp_dir, temp_db_path, mock_screenshot_data):
        """Test concurrent database access scenarios."""
        with patch('services.screenshot.Fernet') as mock_fernet, \
             patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()):
            mock_cipher = Mock()
            mock_cipher.encrypt.return_value = b'encrypted_data'
            mock_fernet.return_value = mock_cipher
            
            capture = ScreenshotCapture(db_path=temp_db_path)
            window_info = mock_screenshot_data['window_info']
            
            # Simulate concurrent saves
            with patch('sqlite3.connect') as mock_connect:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_conn.cursor.return_value = mock_cursor
                mock_connect.return_value = mock_conn
                
                # First save should succeed
                result1 = capture.save_screenshot(mock_screenshot_data['image_data'], window_info)
                assert result1 is True
                
                # Second save with database lock should handle gracefully
                mock_cursor.execute.side_effect = sqlite3.OperationalError("database is locked")
                result2 = capture.save_screenshot(mock_screenshot_data['image_data'], window_info)
                assert result2 is False

"""
Shared pytest fixtures and configuration for the Pixly test suite.

This module provides common fixtures used across all test modules,
including mock objects, test data, and setup/teardown utilities.
"""

import os
import sys
import tempfile
import shutil
import sqlite3
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any
import pandas as pd
from fastapi.testclient import TestClient
from PIL import Image
import io
import base64
from types import SimpleNamespace
from cryptography.fernet import Fernet as RealFernet

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the FastAPI app
try:
    from backend import app
except ImportError:
    # Fallback for when backend module is not available
    app = None


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Robust cleanup on Windows where SQLite can hold file locks briefly
    def _retry_remove(func, path, exc_info):
        import time, os
        for _ in range(10):
            try:
                func(path)
                return
            except PermissionError:
                time.sleep(0.1)
        # Best-effort: ignore if still locked
        try:
            if os.path.isdir(path):
                os.rmdir(path)
            else:
                os.remove(path)
        except Exception:
            pass
    shutil.rmtree(temp_dir, onerror=_retry_remove)


@pytest.fixture
def temp_db_path(temp_dir):
    """Create a temporary database file path."""
    return os.path.join(temp_dir, "test_screenshots.db")


@pytest.fixture
def temp_vector_db_dir(temp_dir):
    """Create a temporary vector database directory."""
    vector_dir = os.path.join(temp_dir, "test_vector_db")
    os.makedirs(vector_dir, exist_ok=True)
    return vector_dir


@pytest.fixture
def temp_games_info_dir(temp_dir):
    """Create a temporary games info directory with test CSV files."""
    games_dir = os.path.join(temp_dir, "test_games_info")
    os.makedirs(games_dir, exist_ok=True)
    
    # Create test CSV files
    test_data = {
        'wiki': ['https://example.com/wiki1', 'https://example.com/wiki2'],
        'wiki_desc': ['Wiki description 1', 'Wiki description 2'],
        'youtube': ['https://youtube.com/watch?v=1', 'https://youtube.com/watch?v=2'],
        'yt_desc': ['YouTube description 1', 'YouTube description 2'],
        'forum': ['https://forum.com/thread1', 'https://forum.com/thread2'],
        'forum_desc': ['Forum description 1', 'Forum description 2']
    }
    
    df = pd.DataFrame(test_data)
    df.to_csv(os.path.join(games_dir, "test_game.csv"), index=False)
    
    return games_dir


@pytest.fixture
def mock_screenshot_data():
    """Create mock screenshot data for testing."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_data = img_buffer.getvalue()
    
    return {
        'image_data': img_data,
        'base64_data': base64.b64encode(img_data).decode('utf-8'),
        'window_info': {
            'application': 'test_app.exe',
            'window_title': 'Test Application',
            'pid': 12345
        }
    }


@pytest.fixture
def mock_game_mappings():
    """Mock game detection mappings for testing."""
    return {
        'minecraft': {
            'processes': ['minecraft.exe'],
            'keywords': ['minecraft', 'mc', 'mojang'],
            'window_titles': ['minecraft', 'minecraft launcher']
        },
        'test_game': {
            'processes': ['test_game.exe'],
            'keywords': ['test', 'game'],
            'window_titles': ['test game window']
        }
    }


@pytest.fixture
def mock_process_list():
    """Mock list of running processes for testing."""
    return ['chrome.exe', 'notepad.exe', 'minecraft.exe', 'steam.exe']


@pytest.fixture
def mock_screenshot_records():
    """Mock screenshot database records for testing."""
    return [
        (1, '2024-01-01T10:00:00', 'minecraft.exe', 'Minecraft', 'hash1'),
        (2, '2024-01-01T10:01:00', 'chrome.exe', 'Google Chrome', 'hash2'),
        (3, '2024-01-01T10:02:00', 'notepad.exe', 'Notepad', 'hash3'),
    ]


@pytest.fixture
def mock_knowledge_data():
    """Mock knowledge data for testing."""
    return {
        'wiki': [
            {
                'url': 'https://example.com/wiki1',
                'title': 'Test Wiki Page',
                'content': 'This is test wiki content about the game.',
                'description': 'Wiki description'
            }
        ],
        'youtube': [
            {
                'url': 'https://youtube.com/watch?v=1',
                'title': 'Test YouTube Video',
                'content': 'YouTube video description',
                'description': 'YouTube description'
            }
        ],
        'forum': [
            {
                'url': 'https://forum.com/thread1',
                'title': 'Test Forum Thread',
                'content': 'This is test forum content about the game.',
                'description': 'Forum description'
            }
        ]
    }


@pytest.fixture
def mock_vector_search_results():
    """Mock vector search results for testing."""
    return [
        {
            'content': 'Test content about game mechanics',
            'metadata': {
                'title': 'Game Mechanics Guide',
                'content_type': 'wiki',
                'url': 'https://example.com/guide',
                'game': 'test_game'
            },
            'distance': 0.1,
            'content_type': 'wiki'
        },
        {
            'content': 'Test content about strategies',
            'metadata': {
                'title': 'Strategy Guide',
                'content_type': 'forum',
                'url': 'https://forum.com/strategy',
                'game': 'test_game'
            },
            'distance': 0.2,
            'content_type': 'forum'
        }
    ]


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response for testing."""
    mock_response = Mock()
    mock_response.text = "This is a test response from Gemini AI."
    return mock_response


@pytest.fixture
def mock_chroma_collection():
    """Mock ChromaDB collection for testing."""
    collection = Mock()
    collection.add = Mock()
    collection.query = Mock(return_value={
        'documents': [['Test document content']],
        'metadatas': [[{'title': 'Test', 'content_type': 'wiki'}]],
        'distances': [[0.1]]
    })
    collection.count = Mock(return_value=10)
    return collection


@pytest.fixture
def mock_chroma_client(mock_chroma_collection):
    """Mock ChromaDB client for testing."""
    client = Mock()
    client.get_collection = Mock(return_value=mock_chroma_collection)
    client.create_collection = Mock(return_value=mock_chroma_collection)
    client.delete_collection = Mock()
    client.list_collections = Mock(return_value=[
        SimpleNamespace(name='test_game_wiki'),
        SimpleNamespace(name='test_game_forum')
    ])
    return client


@pytest.fixture
def mock_embedding_model():
    """Mock sentence transformer model for testing."""
    model = Mock()
    # Return an object with a tolist() method to match production behavior
    encode_result = Mock()
    encode_result.tolist.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]
    model.encode = Mock(return_value=encode_result)
    return model


@pytest.fixture(autouse=True)
def patch_fernet_generate_key():
    """Ensure Fernet.generate_key returns bytes in tests that don't patch it explicitly."""
    with patch('services.screenshot.Fernet.generate_key', return_value=RealFernet.generate_key()):
        yield


@pytest.fixture
def mock_requests_session():
    """Mock requests session for testing."""
    session = Mock()
    response = Mock()
    response.content = b'<html><body><h1>Test Content</h1></body></html>'
    response.raise_for_status = Mock()
    session.get = Mock(return_value=response)
    return session


@pytest.fixture
def test_client():
    """Create a test client for FastAPI app."""
    if app is None:
        pytest.skip("FastAPI app not available")
    return TestClient(app)


@pytest.fixture
def mock_environment_variables():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        'GOOGLE_API_KEY': 'test_api_key',
        'MISTRAL_API_KEY': 'test_mistral_key'
    }):
        yield


@pytest.fixture
def mock_psutil_processes(mock_process_list):
    """Mock psutil process iteration for testing."""
    mock_processes = []
    for proc_name in mock_process_list:
        mock_proc = Mock()
        mock_proc.name.return_value = proc_name
        mock_processes.append(mock_proc)
    
    with patch('psutil.process_iter', return_value=mock_processes):
        yield mock_processes


@pytest.fixture
def mock_win32gui():
    """Mock win32gui functions for testing."""
    with patch('win32gui.GetForegroundWindow', return_value=12345), \
         patch('win32gui.GetWindowText', return_value='Test Window'), \
         patch('win32process.GetWindowThreadProcessId', return_value=(123, 12345)):
        yield


@pytest.fixture
def mock_pil_imagegrab():
    """Mock PIL ImageGrab for testing."""
    mock_image = Mock()
    mock_image.save = Mock()
    
    with patch('PIL.ImageGrab.grab', return_value=mock_image):
        yield mock_image


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Automatically clean up test files after each test."""
    yield
    # Clean up any test files that might have been created
    test_files = [
        'test_screenshots.db',
        'screenshot_key.key',
        'test_vector_db',
        'test_games_info'
    ]
    
    for file_path in test_files:
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)


@pytest.fixture
def sample_chat_message():
    """Sample chat message for API testing."""
    return {
        "message": "How do I craft a sword in Minecraft?",
        "image_data": None
    }


@pytest.fixture
def sample_chat_message_with_image(mock_screenshot_data):
    """Sample chat message with image for API testing."""
    return {
        "message": "What can you see in this screenshot?",
        "image_data": mock_screenshot_data['base64_data']
    }


@pytest.fixture
def sample_api_key_request():
    """Sample API key request for testing."""
    return {
        "api_key": "test_google_api_key_12345"
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "api: mark test as API endpoint test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file location
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add slow marker for tests that might take longer
        if "vector" in item.name or "knowledge" in item.name:
            item.add_marker(pytest.mark.slow)

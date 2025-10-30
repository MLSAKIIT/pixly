"""
Comprehensive test suite for the backend API module.

This module tests FastAPI endpoints, request/response handling,
and API integration functionality.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from backend.backend import app
    from services.chatbot import chat_with_gemini, set_api_key
    from services.screenshot import get_recent_screenshots, get_screenshot_by_id, get_screenshot_stats, delete_screenshot
    from services.game_detection import detect_current_game, get_available_games as get_detection_games
    from services.knowledge_manager import get_available_games as get_csv_games, validate_csv_structure
    from services.vector_service import add_game_knowledge, search_knowledge, get_game_stats, list_available_games
except ImportError as e:
    pytest.skip(f"Backend modules not available: {e}", allow_module_level=True)


class TestBackendAPI:
    """Test cases for backend API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_chat_endpoint_success(self, client, sample_chat_message):
        """Test successful chat endpoint."""
        mock_response = {"response": "Test response from Gemini"}

        with patch('services.chatbot.chat_with_gemini', return_value=mock_response) as mock_chat:
            response = client.post("/chat", json=sample_chat_message)
            
            assert response.status_code == 200
            assert response.json() == mock_response
            mock_chat.assert_called_once_with(sample_chat_message["message"], sample_chat_message["image_data"])
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_chat_endpoint_with_image(self, client, sample_chat_message_with_image):
        """Test chat endpoint with image data."""
        mock_response = {"response": "I can see the image"}

        with patch('services.chatbot.chat_with_gemini', return_value=mock_response) as mock_chat:
            response = client.post("/chat", json=sample_chat_message_with_image)
            
            assert response.status_code == 200
            assert response.json() == mock_response
            mock_chat.assert_called_once_with(
                sample_chat_message_with_image["message"], 
                sample_chat_message_with_image["image_data"]
            )
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_chat_endpoint_invalid_json(self, client):
        """Test chat endpoint with invalid JSON."""
        response = client.post("/chat", json={"invalid": "data"})
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_chat_endpoint_missing_message(self, client):
        """Test chat endpoint with missing message field."""
        response = client.post("/chat", json={"image_data": "base64data"})
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_task_a_endpoint(self, client):
        """Test task A endpoint."""
        response = client.get("/taskA")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "message": "Task A executed"}
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_task_b_endpoint(self, client):
        """Test task B endpoint."""
        response = client.get("/taskB")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "message": "Task B executed"}
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_screenshots_recent_endpoint(self, client, mock_screenshot_records):
        """Test recent screenshots endpoint."""
        with patch('services.screenshot.get_recent_screenshots', return_value=mock_screenshot_records) as mock_get:
            response = client.get("/screenshots/recent")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "ok"
            assert "screenshots" in data
            assert len(data["screenshots"]) == 3
            mock_get.assert_called_once_with(limit=10, application=None)
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_screenshots_recent_with_limit(self, client, mock_screenshot_records):
        """Test recent screenshots endpoint with custom limit."""
        with patch('services.screenshot.get_recent_screenshots', return_value=mock_screenshot_records[:2]) as mock_get:
            response = client.get("/screenshots/recent?limit=2")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert len(data["screenshots"]) == 2
            mock_get.assert_called_once_with(limit=2, application=None)
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_screenshots_recent_with_application_filter(self, client, mock_screenshot_records):
        """Test recent screenshots endpoint with application filter."""
        filtered_records = [record for record in mock_screenshot_records if record[2] == 'minecraft.exe']
        
        with patch('services.screenshot.get_recent_screenshots', return_value=filtered_records) as mock_get:
            response = client.get("/screenshots/recent?application=minecraft.exe")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["screenshots"]) == 1
            mock_get.assert_called_once_with(limit=10, application='minecraft.exe')
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_screenshot_by_id_endpoint(self, client, mock_screenshot_data):
        """Test get screenshot by ID endpoint."""
        with patch('services.screenshot.get_screenshot_by_id', return_value=mock_screenshot_data['image_data']) as mock_get:
            response = client.get("/screenshots/123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "data" in data
            mock_get.assert_called_once_with(123)
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_screenshot_by_id_not_found(self, client):
        """Test get screenshot by ID endpoint when screenshot not found."""
        with patch('services.screenshot.get_screenshot_by_id', return_value=None) as mock_get:
            response = client.get("/screenshots/999")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert data["message"] == "Screenshot not found"
            mock_get.assert_called_once_with(999)
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_screenshot_stats_endpoint(self, client):
        """Test screenshot statistics endpoint."""
        mock_stats = {
            'total_screenshots': 10,
            'applications': [['minecraft.exe', 5], ['chrome.exe', 3], ['notepad.exe', 2]],
            'date_range': ['2024-01-01T10:00:00', '2024-01-01T12:00:00']
        }
        
        with patch('services.screenshot.get_screenshot_stats', return_value=mock_stats) as mock_get:
            response = client.get("/screenshots/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["stats"] == mock_stats
            mock_get.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_delete_screenshot_endpoint(self, client):
        """Test delete screenshot endpoint."""
        with patch('services.screenshot.delete_screenshot', return_value=True) as mock_delete:
            response = client.delete("/screenshots/123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["message"] == "Deleted screenshot 123"
            mock_delete.assert_called_once_with(123)
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_delete_screenshot_not_found(self, client):
        """Test delete screenshot endpoint when screenshot not found."""
        with patch('services.screenshot.delete_screenshot', return_value=False) as mock_delete:
            response = client.delete("/screenshots/999")
            
            assert response.status_code == 404
            assert response.json() == {"detail": "Screenshot not found"}
            mock_delete.assert_called_once_with(999)
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_game_detection_endpoint(self, client):
        """Test game detection endpoint."""
        with patch('services.screenshot.detect_current_game', return_value="minecraft") as mock_detect:
            response = client.post("/games/detect", json={"message": "How do I craft in minecraft?"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["detected_game"] == "minecraft"
            mock_detect.assert_called_once_with("How do I craft in minecraft?")
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_game_detection_endpoint_no_message(self, client):
        """Test game detection endpoint without message."""
        with patch('services.game_detection.detect_current_game', return_value="minecraft") as mock_detect:
            response = client.post("/games/detect", json={})
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["detected_game"] == "minecraft"
            mock_detect.assert_called_once_with(None)
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_game_detection_endpoint_no_game_detected(self, client):
        """Test game detection endpoint when no game is detected."""
        with patch('services.game_detection.detect_current_game', return_value=None) as mock_detect:
            response = client.post("/games/detect", json={"message": "random text"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["detected_game"] is None
            mock_detect.assert_called_once_with("random text")
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_games_available_endpoint(self, client):
        """Test available games endpoint."""
        mock_detection_games = ["minecraft", "elden_ring", "dark_souls_3"]
        mock_csv_games = ["minecraft", "black_myth_wukong"]
        mock_vector_games = ["minecraft", "elden_ring"]

        with patch('services.game_detection.get_detection_games', return_value=mock_detection_games) as mock_detect, \
             patch('services.game_detection.get_csv_games', return_value=mock_csv_games) as mock_csv, \
             patch('services.game_detection.list_available_games', return_value=mock_vector_games) as mock_vector:
            response = client.get("/games/list")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["detection_games"] == mock_detection_games
            assert data["csv_games"] == mock_csv_games
            assert data["vector_games"] == mock_vector_games
            mock_detect.assert_called_once()
            mock_csv.assert_called_once()
            mock_vector.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_games_csv_endpoint(self, client):
        """Test CSV games endpoint - now part of games/list."""
        # This endpoint is now part of /games/list, so we'll skip this test
        pytest.skip("CSV games endpoint is now part of /games/list")
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_games_csv_validate_endpoint(self, client):
        """Test CSV validation endpoint - now part of knowledge processing."""
        # CSV validation is now part of the knowledge processing endpoint
        pytest.skip("CSV validation is now part of knowledge processing endpoint")
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_games_csv_validate_endpoint_invalid(self, client):
        """Test CSV validation endpoint with invalid CSV - now part of knowledge processing."""
        # CSV validation is now part of the knowledge processing endpoint
        pytest.skip("CSV validation is now part of knowledge processing endpoint")
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_games_csv_validate_endpoint_missing_game_name(self, client):
        """Test CSV validation endpoint with missing game name - now part of knowledge processing."""
        # CSV validation is now part of the knowledge processing endpoint
        pytest.skip("CSV validation is now part of knowledge processing endpoint")
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_knowledge_add_endpoint(self, client):
        """Test add game knowledge endpoint."""
        mock_stats = {"wiki": 10, "youtube": 5, "forum": 15}
        
        with patch('services.knowledge_manager.validate_csv_structure', return_value=(True, [])) as mock_validate, \
             patch('services.knowledge_manager.add_game_knowledge', return_value=True) as mock_add, \
             patch('services.knowledge_manager.get_game_stats', return_value=mock_stats) as mock_stats_func:
            response = client.post("/games/minecraft/knowledge/process")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["message"] == "Successfully processed knowledge for minecraft"
            assert data["stats"] == mock_stats
            mock_validate.assert_called_once_with("minecraft")
            mock_add.assert_called_once_with("minecraft")
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_knowledge_add_endpoint_failure(self, client):
        """Test add game knowledge endpoint with failure."""
        with patch('services.knowledge_manager.validate_csv_structure', return_value=(True, [])) as mock_validate, \
             patch('services.knowledge_manager.add_game_knowledge', return_value=False) as mock_add:
            response = client.post("/games/nonexistent_game/knowledge/process")
            
            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "Failed to process game knowledge"
            mock_validate.assert_called_once_with("nonexistent_game")
            mock_add.assert_called_once_with("nonexistent_game")
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_knowledge_add_endpoint_missing_game_name(self, client):
        """Test add game knowledge endpoint with missing game name."""
        # Game name is now in the URL path, so this test is not applicable
        pytest.skip("Game name is now in URL path, not request body")
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_knowledge_search_endpoint(self, client, mock_vector_search_results):
        """Test search knowledge endpoint."""
        with patch('services.vector_service.search_knowledge', return_value=mock_vector_search_results) as mock_search:
            response = client.post("/games/minecraft/knowledge/search", json={
                "query": "How do I craft items?",
                "limit": 5
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["game_name"] == "minecraft"
            assert "results" in data
            assert len(data["results"]) == 2
            mock_search.assert_called_once_with(game_name="minecraft", query="How do I craft items?", content_types=None, limit=5)
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_knowledge_search_endpoint_with_content_types(self, client, mock_vector_search_results):
        """Test search knowledge endpoint with content types."""
        with patch('services.vector_service.search_knowledge', return_value=mock_vector_search_results) as mock_search:
            response = client.post("/games/minecraft/knowledge/search", json={
                "query": "How do I craft items?",
                "content_types": ["wiki", "forum"],
                "limit": 3
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "results" in data
            mock_search.assert_called_once_with(game_name="minecraft", query="How do I craft items?", content_types=["wiki", "forum"], limit=3)
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_knowledge_search_endpoint_missing_fields(self, client):
        """Test search knowledge endpoint with missing required fields."""
        response = client.post("/games/minecraft/knowledge/search", json={})
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_knowledge_stats_endpoint(self, client):
        """Test knowledge statistics endpoint."""
        mock_stats = {"wiki": 10, "youtube": 5, "forum": 15}
        
        with patch('services.vector_services.get_game_stats', return_value=mock_stats) as mock_get:
            response = client.get("/games/minecraft/knowledge/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["game_name"] == "minecraft"
            assert data["stats"] == mock_stats
            mock_get.assert_called_once_with("minecraft")
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_knowledge_games_endpoint(self, client):
        """Test knowledge games endpoint - now part of games/list."""
        # This endpoint is now part of /games/list, so we'll skip this test
        pytest.skip("Knowledge games endpoint is now part of /games/list")
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_api_key_update_endpoint(self, client, sample_api_key_request):
        """Test API key update endpoint."""
        with patch('services.chatbot.set_api_key', return_value=True) as mock_set, \
             patch('builtins.open', create=True) as mock_open, \
             patch('os.path.exists', return_value=True):
            response = client.post("/settings/api-key", json=sample_api_key_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["message"] == "API key updated"
            mock_set.assert_called_once_with(sample_api_key_request["api_key"])
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_api_key_update_endpoint_failure(self, client, sample_api_key_request):
        """Test API key update endpoint with failure."""
        with patch('services.chatbot.set_api_key', return_value=False) as mock_set, \
             patch('builtins.open', create=True) as mock_open, \
             patch('os.path.exists', return_value=True):
            response = client.post("/settings/api-key", json=sample_api_key_request)
            
            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "Failed to apply API key at runtime"
            mock_set.assert_called_once_with(sample_api_key_request["api_key"])
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_api_key_update_endpoint_missing_key(self, client):
        """Test API key update endpoint with missing API key."""
        response = client.post("/settings/api-key", json={})
        
        assert response.status_code == 422  # Validation error for missing key
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_api_key_update_endpoint_exception(self, client, sample_api_key_request):
        """Test API key update endpoint with exception."""
        with patch('services.chatbot.set_api_key', side_effect=Exception("API Error")) as mock_set:
            response = client.post("/settings/api-key", json=sample_api_key_request)
            
            assert response.status_code == 500
            data = response.json()
            assert "Error updating API key" in data["detail"]
            mock_set.assert_called_once_with(sample_api_key_request["api_key"])


class TestBackendIntegration:
    """Integration tests for backend API functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_full_chat_workflow(self, client, sample_chat_message):
        """Test complete chat workflow through API."""
        mock_response = {"response": "Here's how to craft a sword in Minecraft..."}
        
        with patch('backend.backend.chat_with_gemini', return_value=mock_response) as mock_chat:
            # Send chat request
            response = client.post("/chat", json=sample_chat_message)
            
            assert response.status_code == 200
            data = response.json()
            assert data["response"] == "Here's how to craft a sword in Minecraft..."
            mock_chat.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_full_screenshot_workflow(self, client, mock_screenshot_records, mock_screenshot_data):
        """Test complete screenshot workflow through API."""
        # Get recent screenshots
        with patch('services.screenshot.get_recent_screenshots', return_value=mock_screenshot_records):
            response = client.get("/screenshots/recent")
            assert response.status_code == 200
            data = response.json()
            assert len(data["screenshots"]) == 3
        
        # Get screenshot by ID
        with patch('services.screenshot.get_screenshot_by_id', return_value=mock_screenshot_data['image_data']):
            response = client.get("/screenshots/1")
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
        
        # Get screenshot stats
        mock_stats = {'total_screenshots': 3, 'applications': [], 'date_range': [None, None]}
        with patch('services.screenshot.get_screenshot_stats', return_value=mock_stats):
            response = client.get("/screenshots/stats")
            assert response.status_code == 200
            assert response.json() == {"status": "ok", "stats": mock_stats}
        
        # Delete screenshot
        with patch('services.screenshot.delete_screenshot', return_value=True):
            response = client.delete("/screenshots/1")
            assert response.status_code == 200
            assert response.json()["message"] == "Deleted screenshot 1"
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_full_knowledge_workflow(self, client, mock_vector_search_results):
        """Test complete knowledge workflow through API."""
        # Add knowledge
        with patch('services.vector_service.add_game_knowledge', return_value=True):
            response = client.post("/games/minecraft/knowledge/process")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"
        
        # Search knowledge
        with patch('services.vector_service.search_knowledge', return_value=mock_vector_search_results):
            response = client.post("/games/minecraft/knowledge/search", json={
                "query": "How do I craft items?",
                "limit": 5
            })
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 2
        
        # Get knowledge stats
        mock_stats = {"wiki": 10, "youtube": 5, "forum": 15}
        with patch('services.vector_service.get_game_stats', return_value=mock_stats):
            response = client.get("/games/minecraft/knowledge/stats")
            assert response.status_code == 200
            assert response.json() == {"status": "ok", "game_name": "minecraft", "stats": mock_stats}
        
        # List available games
        mock_games = ["minecraft", "elden_ring"]
        with patch('services.vector_service.list_available_games', return_value=mock_games):
            response = client.get("/games/list")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "ok"


class TestBackendEdgeCases:
    """Test edge cases and error conditions for backend API."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_chat_endpoint_with_very_long_message(self, client):
        """Test chat endpoint with very long message."""
        long_message = "This is a very long message. " * 1000
        mock_response = {"response": "Long message processed"}
        
        with patch('services.chatbot.chat_with_gemini', return_value=mock_response):
            response = client.post("/chat", json={"message": long_message})
            
            assert response.status_code == 200
            assert response.json() == mock_response
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_chat_endpoint_with_special_characters(self, client):
        """Test chat endpoint with special characters."""
        special_message = "Hello! 🎮 How do I craft? @#$%^&*()"
        mock_response = {"response": "Special characters handled"}
        
        with patch('services.chatbot.chat_with_gemini', return_value=mock_response):
            response = client.post("/chat", json={"message": special_message})
            
            assert response.status_code == 200
            assert response.json() == mock_response
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_screenshot_endpoint_with_invalid_id(self, client):
        """Test screenshot endpoint with invalid ID."""
        response = client.get("/screenshots/invalid_id")
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_screenshot_endpoint_with_negative_id(self, client):
        """Test screenshot endpoint with negative ID."""
        with patch('services.screenshot.get_screenshot_by_id', return_value=None):
            response = client.get("/screenshots/-1")
            
            assert response.status_code == 200  # FastAPI accepts negative integers
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_knowledge_search_with_empty_query(self, client):
        """Test knowledge search with empty query."""
        with patch('services.vector_service.search_knowledge', return_value=[]):
            response = client.post("/games/minecraft/knowledge/search", json={
                "query": "",
                "limit": 5
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["results"] == []
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_knowledge_search_with_very_long_query(self, client):
        """Test knowledge search with very long query."""
        long_query = "This is a very long query. " * 100
        mock_results = []
        
        with patch('services.vector_service.search_knowledge', return_value=mock_results):
            response = client.post("/games/minecraft/knowledge/search", json={
                "query": long_query,
                "limit": 5
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["results"] == []
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_api_key_update_with_empty_key(self, client):
        """Test API key update with empty key."""
        response = client.post("/settings/api-key", json={"api_key": ""})
        
        assert response.status_code == 400  # Bad request for empty key
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_api_key_update_with_very_long_key(self, client):
        """Test API key update with very long key."""
        long_key = "a" * 10000
        mock_response = {"status": "ok", "message": "API key updated"}
        
        with patch('backend.backend.set_api_key', return_value=True):
            response = client.post("/settings/api-key", json={"api_key": long_key})
            
            assert response.status_code == 200
            assert response.json() == mock_response
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_game_detection_with_unicode_message(self, client):
        """Test game detection with unicode message."""
        unicode_message = "How do I craft in minecraft? 🎮 中文测试"
        
        with patch('services.game_detection.detect_current_game', return_value="minecraft"):
            response = client.post("/games/detect", json={"message": unicode_message})
            
            assert response.status_code == 200
            data = response.json()
            assert data["detected_game"] == "minecraft"
    
    @pytest.mark.unit
    @pytest.mark.api
    def test_csv_validation_with_special_characters(self, client):
        """Test CSV validation with special characters in game name."""
        with patch('services.knowledge_manager.validate_csv_structure', return_value=(True, [])):
            response = client.get("/games/test-game_123/knowledge/validate")
            
            assert response.status_code == 200
            data = response.json()
            assert data["is_valid"] is True

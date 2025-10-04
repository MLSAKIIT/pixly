# backend/backend.py - Add these imports at the top

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os

# Import services
from backend.screenshot import screenshot_service
from backend.chatbot import chatbot
from backend.game_detection import game_detection
from backend.vector_service import vector_service

# Initialize FastAPI app
app = FastAPI(title="Pixly Backend API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# MODELS
# ============================================================================

class ChatRequest(BaseModel):
    message: str
    image_data: Optional[str] = None

class APIKeyRequest(BaseModel):
    api_key: str

# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Pixly Backend API",
        "version": "1.0.0"
    }

# ============================================================================
# SCREENSHOT ENDPOINTS
# ============================================================================

@app.post("/screenshots/start")
async def start_screenshot_capture(interval: int = 30, auto_analyze: bool = True):
    """
    Start automatic screenshot capture
    
    Args:
        interval: Time between captures in seconds (default: 30)
        auto_analyze: Whether to automatically analyze screenshots (default: True)
    """
    try:
        screenshot_service.start_capture(interval=interval, auto_analyze=auto_analyze)
        return {
            "status": "success",
            "message": f"Screenshot capture started (interval: {interval}s, auto-analyze: {auto_analyze})"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/screenshots/stop")
async def stop_screenshot_capture():
    """Stop automatic screenshot capture"""
    try:
        screenshot_service.stop_capture()
        return {"status": "success", "message": "Screenshot capture stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/screenshots/recent")
async def get_recent_screenshots(limit: int = 10, application: Optional[str] = None):
    """
    Get recent screenshots with optional filtering
    
    Args:
        limit: Maximum number of screenshots to return
        application: Filter by application name (optional)
    """
    try:
        screenshots = screenshot_service.get_recent_screenshots(limit=limit, application=application)
        return {
            "status": "success",
            "screenshots": screenshots,
            "count": len(screenshots)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/screenshots/{screenshot_id}")
async def get_screenshot(screenshot_id: int):
    """Get a specific screenshot by ID"""
    try:
        screenshot_data = screenshot_service.get_screenshot_by_id(screenshot_id)
        if not screenshot_data:
            raise HTTPException(status_code=404, detail="Screenshot not found")
        
        return {
            "status": "success",
            "data": screenshot_data['data'],
            "metadata": {
                "id": screenshot_data['id'],
                "timestamp": screenshot_data['timestamp'],
                "application": screenshot_data['application']
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/screenshots/{screenshot_id}")
async def delete_screenshot(screenshot_id: int):
    """Delete a specific screenshot by ID"""
    try:
        success = screenshot_service.delete_screenshot(screenshot_id)
        if not success:
            raise HTTPException(status_code=404, detail="Screenshot not found")
        
        return {
            "status": "success",
            "message": f"Screenshot {screenshot_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# CHAT ENDPOINT
# ============================================================================

@app.post("/chat")
async def chat_with_pixly(request: ChatRequest):
    """
    Chat with Pixly AI, optionally with screenshot analysis
    
    Args:
        message: User's message/prompt
        image_data: Optional base64 encoded screenshot data
    """
    try:
        # Detect current game
        game = game_detection.detect_game(message=request.message)
        
        # Get relevant knowledge if game is detected
        context = ""
        if game:
            # Retrieve relevant snippets from vector DB
            try:
                context = vector_service.get_context_for_game(game, request.message)
            except Exception as e:
                print(f"Warning: Could not retrieve context for {game}: {e}")
        
        # Generate response with or without image
        if request.image_data:
            response = chatbot.generate_response_with_image(
                prompt=request.message,
                image_data=request.image_data,
                context=context
            )
        else:
            response = chatbot.generate_response(
                prompt=request.message,
                context=context
            )
        
        return {
            "status": "success",
            "response": response,
            "game_detected": game
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# API KEY MANAGEMENT
# ============================================================================

@app.get("/settings/api-key")
async def get_api_key_status():
    """Check if API key is configured and return masked preview"""
    try:
        is_configured = chatbot.is_api_key_configured()
        preview = ""
        
        if is_configured:
            key = chatbot.get_api_key_preview()
            if key and len(key) > 8:
                preview = f"{key[:4]}...{key[-4:]}"
        
        return {
            "status": "success",
            "configured": is_configured,
            "preview": preview
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/settings/api-key")
async def save_api_key(request: APIKeyRequest):
    """Save API key to .env file and reconfigure chatbot"""
    try:
        if not request.api_key or len(request.api_key) < 10:
            raise HTTPException(status_code=400, detail="Invalid API key")
        
        # Save to .env file
        from pathlib import Path
        
        env_path = Path(".env")
        
        # Read existing .env or create new
        env_vars = {}
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        
        # Update API key
        env_vars['GEMINI_API_KEY'] = request.api_key
        
        # Write back to .env
        with open(env_path, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        # Reconfigure chatbot with new key
        chatbot.reconfigure_api_key(request.api_key)
        
        return {
            "status": "success",
            "message": "API key saved and configured successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# GAME DETECTION ENDPOINTS (if you need them)
# ============================================================================

@app.post("/games/detect")
async def detect_game(message: Optional[str] = None):
    """Detect current game from process or message"""
    try:
        game = game_detection.detect_game(message=message)
        return {
            "status": "success",
            "game": game
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/games/list")
async def list_games():
    """List available games"""
    try:
        games = game_detection.get_available_games()
        return {
            "status": "success",
            "games": games
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
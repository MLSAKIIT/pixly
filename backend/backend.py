"""All backend endpoints exist here"""
from fastapi import FastAPI, HTTPException
import os
import uvicorn
from .chatbot import chat_with_gemini, set_api_key
from .screenshot import start_screenshot_capture, stop_screenshot_capture, get_recent_screenshots, get_screenshot_by_id, get_screenshot_stats, delete_screenshot
from .game_detection import detect_current_game, get_available_games as get_detection_games
from .knowledge_manager import get_available_games as get_csv_games, validate_csv_structure
from .vector_service import add_game_knowledge, search_knowledge, get_game_stats, list_available_games
from pydantic import BaseModel
from typing import Optional, List
from . import app

class ChatMessage(BaseModel):
    message: str
    image_data: Optional[str] = None  # Base64 encoded image data

class GameDetectionRequest(BaseModel):
    message: Optional[str] = None

class KnowledgeSearchRequest(BaseModel):
    game_name: str
    query: str
    content_types: Optional[List[str]] = None
    limit: Optional[int] = 5

class ApiKeyRequest(BaseModel):
    api_key: str

@app.post("/chat")
async def chat(message: ChatMessage):
    return await chat_with_gemini(message.message, message.image_data)

# Dummy functions to test functionality,, carry no use
@app.get("/taskA")
def run_task_a():
    return {"status": "ok", "message": "Task A executed"}

@app.get("/taskB")
def run_task_b():
    return {"status": "ok", "message": "Task B executed"}

# Screenshot endpoints
@app.post("/screenshots/start")
def start_screenshots(interval: int = 30):
    """Start automatic screenshot capture."""
    start_screenshot_capture(interval)
    return {"status": "ok", "message": f"Screenshot capture started with {interval}s interval"}

@app.post("/screenshots/stop")
def stop_screenshots():
    """Stop automatic screenshot capture."""
    stop_screenshot_capture()
    return {"status": "ok", "message": "Screenshot capture stopped"}

@app.post("/screenshots/latest")
def latest_screenshots():
    """Latest screenshot """
    return {"status" : "ok"}

@app.get("/screenshots/recent")
def get_recent_screenshots_endpoint(limit: int = 10, application: str = None):
    """Get recent screenshots."""
    screenshots = get_recent_screenshots(limit=limit, application=application)
    return {"status": "ok", "screenshots": screenshots}

@app.get("/screenshots/stats")
def get_screenshot_stats_endpoint():
    """Get screenshot statistics."""
    stats = get_screenshot_stats()
    return {"status": "ok", "stats": stats}

@app.get("/screenshots/{screenshot_id}")
def get_screenshot_endpoint(screenshot_id: int):
    """Get screenshot data by ID."""
    screenshot_data = get_screenshot_by_id(screenshot_id)
    if screenshot_data:
        import base64
        return {"status": "ok", "data": base64.b64encode(screenshot_data).decode('utf-8')}
    else:
        return {"status": "error", "message": "Screenshot not found"}

@app.delete("/screenshots/{screenshot_id}")
def delete_screenshot_endpoint(screenshot_id: int):
    """Delete screenshot by ID."""
    try:
        deleted = delete_screenshot(screenshot_id)
        if deleted:
            return {"status": "ok", "message": f"Deleted screenshot {screenshot_id}"}
        else:
            raise HTTPException(status_code=404, detail="Screenshot not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting screenshot: {str(e)}")

# Game Detection endpoints
@app.post("/games/detect")
def detect_game(request: GameDetectionRequest):
    """Detect current game from process/screenshot/message."""
    try:
        detected_game = detect_current_game(request.message)
        return {
            "status": "ok", 
            "detected_game": detected_game,
            "message": f"Detected game: {detected_game}" if detected_game else "No game detected"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting game: {str(e)}")

@app.get("/games/list")
def list_games():
    """List all available games."""
    try:
        detection_games = get_detection_games()
        csv_games = get_csv_games()
        vector_games = list_available_games()
        
        return {
            "status": "ok",
            "detection_games": detection_games,
            "csv_games": csv_games,
            "vector_games": vector_games
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing games: {str(e)}")

# Knowledge Management endpoints
@app.post("/games/{game_name}/knowledge/process")
def process_game_knowledge(game_name: str):
    """Process and vectorize knowledge for a specific game."""
    try:
        # Validate CSV structure first
        is_valid, errors = validate_csv_structure(game_name)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid CSV structure: {errors}")
        
        # Process and add to vector database
        success = add_game_knowledge(game_name)
        if success:
            stats = get_game_stats(game_name)
            return {
                "status": "ok",
                "message": f"Successfully processed knowledge for {game_name}",
                "stats": stats
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to process game knowledge")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing knowledge: {str(e)}")

@app.post("/games/{game_name}/knowledge/search")
def search_game_knowledge(game_name: str, request: KnowledgeSearchRequest):
    """Search knowledge base for a specific game."""
    try:
        results = search_knowledge(
            game_name=game_name,
            query=request.query,
            content_types=request.content_types,
            limit=request.limit
        )
        
        return {
            "status": "ok",
            "game_name": game_name,
            "query": request.query,
            "results": results,
            "total_results": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching knowledge: {str(e)}")

@app.get("/games/{game_name}/knowledge/stats")
def get_game_knowledge_stats(game_name: str):
    """Get statistics for a game's knowledge base."""
    try:
        stats = get_game_stats(game_name)
        return {
            "status": "ok",
            "game_name": game_name,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@app.get("/games/{game_name}/knowledge/validate")
def validate_game_csv(game_name: str):
    """Validate CSV structure for a game."""
    try:
        is_valid, errors = validate_csv_structure(game_name)
        return {
            "status": "ok",
            "game_name": game_name,
            "is_valid": is_valid,
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating CSV: {str(e)}")

# Settings endpoints
@app.get("/settings/api-key")
def get_api_key_status():
    """Return whether an API key is configured (masked)."""
    import os
    key = os.getenv('GOOGLE_API_KEY') or ""
    masked = (len(key) >= 8)
    preview = f"{key[:4]}***{key[-4:]}" if masked else ""
    return {"status": "ok", "configured": bool(key), "preview": preview}

@app.post("/settings/api-key")
def update_api_key(req: ApiKeyRequest):
    """Save API key to .env and reconfigure the chatbot model."""
    try:
        key = (req.api_key or "").strip()
        if not key:
            raise HTTPException(status_code=400, detail="API key cannot be empty")
        # Persist to .env
        env_path = ".env"
        # Load existing lines if any
        lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
        # Update or append GOOGLE_API_KEY
        found = False
        for i, line in enumerate(lines):
            if line.startswith("GOOGLE_API_KEY="):
                lines[i] = f"GOOGLE_API_KEY={key}"
                found = True
                break
        if not found:
            lines.append(f"GOOGLE_API_KEY={key}")
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        # Reconfigure runtime
        if not set_api_key(key):
            raise HTTPException(status_code=500, detail="Failed to apply API key at runtime")
        return {"status": "ok", "message": "API key updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating API key: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)

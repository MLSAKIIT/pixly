from services.game_detection import detect_current_game, get_available_games as get_detection_games
from services.knowledge_manager import get_available_games as get_csv_games, validate_csv_structure
from services.vector_service import vector_service
from schemas.game_detection import GameDetectionRequest
from schemas.knowledge_search import KnowledgeSearchRequest
from fastapi import APIRouter,HTTPException

router = APIRouter()
# Game Detection endpoints
@router.post("/detect")
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

@router.get("/list")
def list_games():
    """List all available games."""
    try:
        detection_games = get_detection_games()
        csv_games = get_csv_games()
        vector_games = vector_service.list_available_games()
        
        return {
            "status": "ok",
            "detection_games": detection_games,
            "csv_games": csv_games,
            "vector_games": vector_games
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing games: {str(e)}")

# Knowledge Management endpoints
@router.post("/{game_name}/knowledge/process")
def process_game_knowledge(game_name: str):
    """Process and vectorize knowledge for a specific game."""
    try:
        # Validate CSV structure first
        is_valid, errors = validate_csv_structure(game_name)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid CSV structure: {errors}")
        
        # Process and add to vector database
        success = vector_service.add_game_knowledge(game_name)
        if success:
            stats = vector_service.get_game_stats(game_name)
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

@router.post("/{game_name}/knowledge/search")
def search_game_knowledge(game_name: str, request: KnowledgeSearchRequest):
    """Search knowledge base for a specific game."""
    try:
        results = vector_service.search_knowledge(
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

@router.get("/{game_name}/knowledge/stats")
def get_game_knowledge_stats(game_name: str):
    """Get statistics for a game's knowledge base."""
    try:
        stats = vector_service.get_game_stats(game_name)
        return {
            "status": "ok",
            "game_name": game_name,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@router.get("/{game_name}/knowledge/validate")
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

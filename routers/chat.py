"""
routers/chat.py - Updated with Chat History Support
"""

from fastapi import APIRouter, HTTPException
from services.chatbot import chat_with_gemini
from schemas.chat import ChatMessage
from backend.chat_history import ChatHistoryManager
from typing import Optional
from datetime import datetime

router = APIRouter()

# Initialize chat history manager
chat_history_manager = ChatHistoryManager(
    persist_directory="./vector_db",
    max_history=30  # Store last 30 messages per game
)


def parse_temporal_query(message: str) -> dict:
    """Check if user is asking about past conversation"""
    message_lower = message.lower()
    temporal_patterns = {
        "yesterday": 24,
        "last hour": 1,
        "past hour": 1,
        "last 2 hours": 2,
        "last few hours": 3,
        "today": 24,
        "last 24 hours": 24,
        "this morning": 12,
    }
    
    for pattern, hours in temporal_patterns.items():
        if pattern in message_lower:
            return {"hours_ago": hours, "is_temporal": True}
    
    return {"is_temporal": False}


@router.post("/chat")
async def chat(message: ChatMessage):
    """
    Enhanced chat endpoint with conversation history
    
    Now includes:
    - Persistent chat history per game
    - Context from previous conversations
    - Temporal query support ("What did I ask yesterday?")
    """
    try:
        # 1. Determine game context (default to 'general' if not specified)
        game = getattr(message, 'game', 'general')
        user_message = message.message
        image_data = message.image_data
        
        # 2. Check if this is a temporal query
        temporal_info = parse_temporal_query(user_message)
        
        if temporal_info["is_temporal"]:
            # User is asking about past conversation
            hours_ago = temporal_info["hours_ago"]
            history = chat_history_manager.get_recent_history(
                game=game,
                hours_ago=hours_ago
            )
            
            if not history:
                response_text = f"I don't have any conversation history from the last {hours_ago} hours for {game}."
            else:
                # Format historical conversation
                history_summary = []
                for msg in history:
                    timestamp = datetime.fromisoformat(msg["timestamp"])
                    time_str = timestamp.strftime("%H:%M")
                    history_summary.append(f"At {time_str}:")
                    history_summary.append(f"  You: {msg['user_message']}")
                    history_summary.append(f"  Me: {msg['assistant_response'][:100]}...")
                
                response_text = "\n".join(history_summary)
            
            # Store this exchange too
            chat_history_manager.add_message(
                game=game,
                user_message=user_message,
                assistant_response=response_text
            )
            
            return {
                "response": response_text,
                "game": game,
                "is_temporal_query": True
            }
        
        # 3. Get chat history for context
        include_history = getattr(message, 'include_history', True)
        history_limit = getattr(message, 'history_limit', 5)
        
        enhanced_message = user_message
        
        if include_history:
            history_context = chat_history_manager.get_history_context(
                game=game,
                limit=history_limit
            )
            
            if history_context:
                # Prepend history to the message
                enhanced_message = f"{history_context}\n\n---\n\nCurrent question: {user_message}"
        
        # 4. Call existing Gemini service with enhanced message
        response = await chat_with_gemini(enhanced_message, image_data)
        
        # Extract response text (adjust based on your response structure)
        if isinstance(response, dict):
            response_text = response.get("response", str(response))
        else:
            response_text = str(response)
        
        # 5. Store the exchange in chat history
        chat_history_manager.add_message(
            game=game,
            user_message=user_message,
            assistant_response=response_text
        )
        
        # 6. Return response in original format
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


# ============================================================================
# NEW ENDPOINTS: CHAT HISTORY MANAGEMENT
# ============================================================================

@router.get("/history/{game}")
async def get_chat_history(
    game: str,
    limit: Optional[int] = None,
    hours_ago: Optional[int] = None
):
    """
    Get chat history for a specific game
    
    Example: GET /chat/history/minecraft?limit=10&hours_ago=24
    """
    try:
        history = chat_history_manager.get_recent_history(
            game=game,
            limit=limit,
            hours_ago=hours_ago
        )
        
        return {
            "game": game,
            "message_count": len(history),
            "messages": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history/search")
async def search_chat_history(
    game: str,
    query: str,
    n_results: int = 5
):
    """
    Search chat history using semantic search
    
    Example: POST /chat/history/search?game=minecraft&query=diamond&n_results=5
    """
    try:
        results = chat_history_manager.search_history(
            game=game,
            query=query,
            n_results=n_results
        )
        
        return {
            "game": game,
            "query": query,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{game}")
async def clear_chat_history(game: str):
    """
    Clear all chat history for a specific game
    
    Example: DELETE /chat/history/minecraft
    """
    try:
        chat_history_manager.clear_history(game)
        return {
            "message": f"Chat history cleared for {game}",
            "game": game
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/history")
async def update_history_settings(max_history: int):
    """
    Update chat history settings
    
    Example: POST /chat/settings/history?max_history=50
    """
    try:
        if max_history < 1 or max_history > 100:
            raise HTTPException(
                status_code=400, 
                detail="max_history must be between 1 and 100"
            )
        
        chat_history_manager.max_history = max_history
        
        return {
            "message": "Chat history settings updated",
            "max_history": max_history
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/history")
async def get_history_settings():
    """
    Get current chat history settings
    
    Example: GET /chat/settings/history
    """
    try:
        return {
            "max_history": chat_history_manager.max_history,
            "persist_directory": "./vector_db"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

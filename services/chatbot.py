""" Includes gemini chatbot integration"""
import os
import google.generativeai as genai
from dotenv import load_dotenv
from services.screenshot import get_recent_screenshots, get_screenshot_by_id, get_screenshot_stats
from services.game_detection import detect_current_game
from services.vector_service import search_knowledge
import base64
import PIL.Image
import io
from agno.agent import Agent
from agno.models.google import Gemini
from agno.db.sqlite import SqliteDb
from agno.tools import tool
from agno.media import Image
from typing import Optional, Dict, Any

system_prompt_file = open("PROMPTS.txt", "r")
system_prompt = system_prompt_file.read()
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

@tool()
def get_game_screenshots(limit: int = 5) -> str:
    """Get recent game screenshots."""
    try:
        screenshots = get_recent_screenshots(limit=limit)
        stats = get_screenshot_stats()
        return {
            "screenshots": screenshots,
            "stats": stats
        }
    except Exception as e:
        return {"error": str(e)}

@tool()
def get_specific_screenshot(screenshot_id: str) -> str:
    """Get a specific screenshot by ID."""
    try:
        return get_screenshot_by_id(screenshot_id)
    except Exception as e:
        return {"error": str(e)}

@tool()
def detect_game_context(message: str) -> str:
    """Detect the current game from message."""
    try:
        return detect_current_game(message)
    except Exception as e:
        return {"error": str(e)}

@tool()
def search_game_knowledge(query: str) -> str:
    """Search the knowledge base for game information."""
    try:
        return search_knowledge(query)
    except Exception as e:
        return {"error": str(e)}

db = SqliteDb(db_file="chatbot.db")
agent = Agent(
    model=Gemini(
        id="gemini-2.5-flash-lite",
        api_key=os.getenv('GOOGLE_API_KEY')
    ),
    tools=[
        get_game_screenshots,
        get_specific_screenshot,
        detect_game_context,
        search_game_knowledge
    ],
    db=db,
    add_history_to_context=True,
    num_history_runs=3,
    read_chat_history=True,
    markdown=True,
    enable_session_summaries=True,
    store_media=True,
    description=system_prompt
)

def set_api_key(new_key: str) -> bool:
    """Update the Google API key at runtime."""
    try:
        if not new_key:
            raise ValueError("Empty API key")
        os.environ['GOOGLE_API_KEY'] = new_key
        genai.configure(api_key=new_key)
        global agent
        agent = Agent(
            model=Gemini(
                id="gemini-2.5-flash-lite",
                api_key=new_key
            ),
            tools=[
                get_game_screenshots,
                get_specific_screenshot,
                detect_game_context,
                search_game_knowledge
            ],
            db=db,
            add_history_to_context=True,
            num_history_runs=3,
            read_chat_history=True,
            markdown=True,
            enable_session_summaries=True,
            store_media=True,
            description=system_prompt
        )
        return True
    except Exception as e:
        print(f"Error setting API key: {e}")
        return False

async def chat_with_gemini(message: str, image_data: str = None):
    """Process chat message with context awareness."""
    try:
        # Detect current game context
        game_context = detect_current_game(message)
        
        run_params = {
            "stream": True
        }
        
        # Handle image input
        if image_data:
            enhanced_message = f"""
            {message}
            
            LIVE SCREENSHOT PROVIDED: I can see a screenshot that the user just captured. 
            Please analyze this image in the context of gaming and provide specific, actionable advice based on what you can see.
            Focus on game mechanics, strategies, UI elements, or any gaming-related aspects visible in the screenshot.
            """
            
            # Process image
            image_bytes = base64.b64decode(image_data)
            image = PIL.Image.open(io.BytesIO(image_bytes))
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            image_content = buf.getvalue()
            run_params["images"] = [Image(content=image_content)]
            message = enhanced_message
            
            # Add game context if detected
            if game_context:
                enhanced_message += f"\n\nDETECTED GAME: {game_context.upper()}"
        
        # Run agent with parameters
        response_content = ""
        async for response in agent.arun(
            message,
            **run_params
        ):
            response_content += getattr(response, "content", str(response))
        return {"response": response_content}
        
    except Exception as e:
        print(e)
        return {"response": f"Error processing request: {str(e)}"}
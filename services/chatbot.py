""" Includes gemini chatbot integration"""
import os
import google.generativeai as genai
from dotenv import load_dotenv
from services.screenshot import get_recent_screenshots, get_screenshot_by_id, get_screenshot_stats
from services.game_detection import detect_current_game
from services.vector_service import search_knowledge
import base64

system_prompt_file = open("PROMPTS.txt","r")
system_prompt = system_prompt_file.read()
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'),)
model = genai.GenerativeModel(model_name="gemini-2.5-flash-lite",system_instruction=system_prompt)

def set_api_key(new_key: str):
    """Update the Google API key at runtime and reinitialize the model."""
    try:
        if not new_key:
            raise ValueError("Empty API key")
        os.environ['GOOGLE_API_KEY'] = new_key
        genai.configure(api_key=new_key)
        global model
        model = genai.GenerativeModel(model_name="gemini-2.5-flash", system_instruction=system_prompt)
        return True
    except Exception as e:
        print(f"Error setting API key: {e}")
        return False

async def chat_with_gemini(message: str, image_data: str = None):
    try:
        # Detect current game
        detected_game = detect_current_game(message)
        
        # If image data is provided, use vision capabilities
        if image_data:
            import PIL.Image
            import io
            
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            image = PIL.Image.open(io.BytesIO(image_bytes))
            
            # Enhanced message for image analysis
            enhanced_message = f"""
            {message}
            
            LIVE SCREENSHOT PROVIDED: I can see a screenshot that the user just captured. 
            Please analyze this image in the context of gaming and provide specific, actionable advice based on what you can see.
            Focus on game mechanics, strategies, UI elements, or any gaming-related aspects visible in the screenshot.
            """
            
            # Add game context if detected
            if detected_game:
                enhanced_message += f"\n\nDETECTED GAME: {detected_game.upper()}"
            
            # Generate content with image
            response = model.generate_content([enhanced_message, image])
            return {"response": response.text}
        
        # Check if user is asking about screenshots (existing functionality)
        screenshot_keywords = ['screenshot', 'screen', 'capture', 'git', 'visual', 'see', 'show me']
        if any(keyword in message.lower() for keyword in screenshot_keywords):
            # Get recent screenshots
            recent_screenshots = get_recent_screenshots(limit=5)
            screenshot_stats = get_screenshot_stats()
            
            # Prepare screenshot context
            screenshot_context = f"""
            SCREENSHOT DATA AVAILABLE:
            - Total screenshots stored: {screenshot_stats['total_screenshots']}
            - Recent applications captured: {[app[0] for app in screenshot_stats['applications'][:5]]}
            - Recent screenshots: {recent_screenshots}
            
            You can analyze these screenshots to help with gaming-related questions. 
            The screenshots are automatically captured and show what applications the user was using.
            """
            
            # Add screenshot context to the message
            enhanced_message = f"{message}\n\n{screenshot_context}"
            response = model.generate_content(enhanced_message)
            return {"response": response.text}
        else:
            # Enhanced chat with game knowledge
            enhanced_message = message
            
            # Add game context and knowledge if detected
            if detected_game:
                enhanced_message += f"\n\nDETECTED GAME: {detected_game.lower()}"
                
                # Search for relevant knowledge
                try:
                    knowledge_results = search_knowledge(detected_game, message)
                    
                    if knowledge_results:
                        knowledge_context = "\n\nRELEVANT KNOWLEDGE FROM GAME DATABASE:\n"
                        for i, result in enumerate(knowledge_results, 1):
                            knowledge_context += f"\n{i}. {result['metadata'].get('title', 'Unknown Title')}\n"
                            knowledge_context += f"   Source: {result['metadata'].get('content_type', 'unknown').upper()}\n"
                            knowledge_context += f"   Content: {result['content'][:200]}...\n"
                            knowledge_context += f"   URL: {result['metadata'].get('url', 'N/A')}\n"
                        
                        enhanced_message += knowledge_context
                except Exception as e:
                    print(f"Error searching knowledge: {e}")
            
            response = model.generate_content(enhanced_message)
            return {"response": response.text}
    except Exception as e:
        print(e)
        return {"response": f"Error processing request: {str(e)}"}
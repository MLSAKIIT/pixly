# Add these methods to your backend/chatbot.py

import google.generativeai as genai
from PIL import Image
import io
import base64
import os
from pathlib import Path

class ChatbotService:
    def __init__(self):
        self.api_key = None
        self.model = None
        self._load_api_key()
        self._initialize_model()
    
    def _load_api_key(self):
        """Load API key from .env file"""
        env_path = Path(".env")
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('GEMINI_API_KEY='):
                        self.api_key = line.split('=', 1)[1].strip()
                        break
        
        # Fallback to environment variable
        if not self.api_key:
            self.api_key = os.getenv('GEMINI_API_KEY')
    
    def _initialize_model(self):
        """Initialize the Gemini model"""
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                print("Gemini model initialized successfully")
            except Exception as e:
                print(f"Error initializing Gemini model: {e}")
                self.model = None
        else:
            print("No API key found. Please configure in settings.")
    
    def is_api_key_configured(self):
        """Check if API key is configured"""
        return self.api_key is not None and len(self.api_key) > 0
    
    def get_api_key_preview(self):
        """Get masked preview of API key"""
        return self.api_key if self.api_key else ""
    
    def reconfigure_api_key(self, api_key: str):
        """Reconfigure with new API key"""
        self.api_key = api_key
        self._initialize_model()
    
    def generate_response(self, prompt: str, context: str = ""):
        """Generate a text-only response"""
        if not self.model:
            return "Error: AI model not initialized. Please configure your API key in settings."
        
        try:
            # Load system prompt
            system_prompt = self._load_system_prompt()
            
            # Combine prompts
            full_prompt = f"{system_prompt}\n\n"
            if context:
                full_prompt += f"RETRIEVED CONTEXT:\n{context}\n\n"
            full_prompt += f"USER: {prompt}\n\nASSISTANT:"
            
            # Generate response
            response = self.model.generate_content(full_prompt)
            return response.text
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def generate_response_with_image(self, prompt: str, image_data: str, context: str = ""):
        """Generate response with image analysis"""
        if not self.model:
            return "Error: AI model not initialized. Please configure your API key in settings."
        
        try:
            # Decode base64 image
            img_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(img_bytes))
            
            # Load system prompt
            system_prompt = self._load_system_prompt()
            
            # Combine prompts
            full_prompt = f"{system_prompt}\n\n"
            if context:
                full_prompt += f"RETRIEVED CONTEXT:\n{context}\n\n"
            full_prompt += f"USER: {prompt}\n\n"
            full_prompt += "The user has provided a screenshot. Please analyze it and provide relevant insights.\n\n"
            full_prompt += "ASSISTANT:"
            
            # Generate response with image
            response = self.model.generate_content([full_prompt, image])
            return response.text
            
        except Exception as e:
            return f"Error generating response with image: {str(e)}"
    
    def _load_system_prompt(self):
        """Load system prompt from PROMPTS.txt"""
        try:
            with open('PROMPTS.txt', 'r') as f:
                return f.read()
        except FileNotFoundError:
            return """You are Pixly, a helpful gaming assistant. You provide expert advice on games, 
analyze screenshots, and help users improve their gameplay. Always be friendly, concise, 
and focused on gaming topics. When analyzing screenshots, describe what you see and 
provide relevant tips or insights."""

# Initialize the service
chatbot = ChatbotService()
"""Game detection using process id, screenshots and user query"""
import psutil
from typing import Optional, Dict, List
# NEW (correct):
from .screenshot import screenshot_service

class GameDetection:
    def __init__(self):
        """Initialize game detection system."""
        # Game detection mappings - process names and keywords
        self.game_mappings = {
            'minecraft': {
                'processes': ['minecraft.exe'],
                'keywords': ['minecraft', 'mc', 'mojang'],
                'window_titles': ['minecraft', 'minecraft launcher', 'minecraft: java edition']
            },
            'elden_ring': {
                'processes': ['eldenring.exe', 'elden ring.exe'],
                'keywords': ['elden ring', 'eldenring', 'fromsoftware'],
                'window_titles': ['elden ring', 'eldenring']
            },
            'dark_souls_3': {
                'processes': ['darksouls3.exe', 'dark souls iii.exe'],
                'keywords': ['dark souls 3', 'darksouls3', 'ds3'],
                'window_titles': ['dark souls iii', 'darksouls3']
            },
            'black_myth_wukong': {
            'processes': ['b1.exe', 'b1-win64-shipping.exe'],
            'keywords': ['black myth wukong', 'blackmythwukong', 'bmw'],
            'window_titles': ['black myth: wukong', 'black myth wukong']
        }
}
        
        # Cache for detected game
        self._detected_game = None
        self._last_detection_time = 0
        self._cache_duration = 30  # Cache for 30 seconds
    
    def detect_game_from_process(self) -> Optional[str]:
        """Detect game from running processes."""
        try:
            running_processes = [proc.name().lower() for proc in psutil.process_iter(['name'])]
            
            for game_name, game_info in self.game_mappings.items():
                for process in game_info['processes']:
                    if process.lower() in running_processes:
                        return game_name
            
            return None
        except Exception as e:
            print(f"Error detecting game from process: {e}")
            return None
    
    def detect_game_from_screenshots(self) -> Optional[str]:
        """Detect game from recent screenshots."""
        try:
            recent = screenshot_service.get_recent_screenshots(limit=5)
            
            for screenshot in recent:
                app_name = screenshot[2].lower()  # application name
                window_title = screenshot[3].lower() if screenshot[3] else ""  # window title
                
                for game_name, game_info in self.game_mappings.items():
                    # Check application name
                    if any(keyword in app_name for keyword in game_info['keywords']):
                        return game_name
                    
                    # Check window title
                    if any(keyword in window_title for keyword in game_info['keywords']):
                        return game_name
            
            return None
        except Exception as e:
            print(f"Error detecting game from screenshots: {e}")
            return None
    
    def detect_game_from_message(self, message: str) -> Optional[str]:
        """Detect game from user message using keyword matching."""
        try:
            message_lower = message.lower()
            
            for game_name, game_info in self.game_mappings.items():
                for keyword in game_info['keywords']:
                    if keyword in message_lower:
                        return game_name
            
            return None
        except Exception as e:
            print(f"Error detecting game from message: {e}")
            return None
    
    def detect_current_game(self, user_message: str = None) -> Optional[str]:
        """Main game detection method with caching."""
        import time
        current_time = time.time()
        
        # Return cached result if still valid
        if (self._detected_game and 
            current_time - self._last_detection_time < self._cache_duration):
            return self._detected_game
        
        detected_game = None
        
        # Try manual detection first (from user message)
        if user_message:
            detected_game = self.detect_game_from_message(user_message)
            if detected_game:
                self._detected_game = detected_game
                self._last_detection_time = current_time
                return detected_game
        
        # Try process detection
        detected_game = self.detect_game_from_process()
        if detected_game:
            self._detected_game = detected_game
            self._last_detection_time = current_time
            return detected_game
        
        # Try screenshot detection
        detected_game = self.detect_game_from_screenshots()
        if detected_game:
            self._detected_game = detected_game
            self._last_detection_time = current_time
            return detected_game
        
        # No game detected
        self._detected_game = None
        self._last_detection_time = current_time
        return None
    
    def add_game_mapping(self, game_name: str, processes: List[str], 
                        keywords: List[str], window_titles: List[str] = None):
        """Add a new game mapping for detection."""
        self.game_mappings[game_name] = {
            'processes': processes,
            'keywords': keywords,
            'window_titles': window_titles or []
        }
    
    def get_available_games(self) -> List[str]:
        """Get list of available games for detection."""
        return list(self.game_mappings.keys())
    
    def clear_cache(self):
        """Clear the detection cache."""
        self._detected_game = None
        self._last_detection_time = 0

# Global instance
game_detector = GameDetection()

def detect_current_game(user_message: str = None) -> Optional[str]:
    """Detect the current game being played."""
    return game_detector.detect_current_game(user_message)

def add_game_mapping(game_name: str, processes: List[str], 
                    keywords: List[str], window_titles: List[str] = None):
    """Add a new game mapping for detection."""
    game_detector.add_game_mapping(game_name, processes, keywords, window_titles)

def get_available_games() -> List[str]:
    """Get list of available games for detection."""
    return game_detector.get_available_games()

# At the END of backend/game_detection.py

# Initialize the service
game_detection = GameDetection()
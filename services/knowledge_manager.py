import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
import re
from urllib.parse import urlparse
import time
import random

class KnowledgeManager:
    def __init__(self, games_info_dir: str = "games_info"):
        """Initialize knowledge manager for CSV processing and content extraction."""
        self.games_info_dir = games_info_dir
        self.session = requests.Session()
        
        # ENHANCEMENT: Rotating User-Agents
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        ]
        
        # ENHANCEMENT: Set initial headers
        self._update_session_headers()
        
        # Ensure games_info directory exists
        os.makedirs(games_info_dir, exist_ok=True)
    
    def _update_session_headers(self):
        """ENHANCEMENT: Update session with realistic browser headers"""
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'DNT': '1',
        })
    
    def _human_delay(self, min_seconds: float = 2.0, max_seconds: float = 4.0):
        """ENHANCEMENT: Add random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        print(f"[DEBUG] Waiting {delay:.2f}s (human-like behavior)")
        time.sleep(delay)
    
    def _fetch_with_retry(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """ENHANCEMENT: Fetch URL with retry logic and exponential backoff"""
        for attempt in range(max_retries):
            try:
                # Rotate User-Agent for each attempt
                self._update_session_headers()
                
                print(f"[DEBUG] Fetching {url} (attempt {attempt + 1}/{max_retries})")
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                
                print(f"[SUCCESS] Fetched {url} ({len(response.content)} bytes)")
                return response
                
            except requests.exceptions.RequestException as e:
                print(f"[WARNING] Attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff: 2s, 4s, 8s
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"[DEBUG] Retrying in {wait_time:.2f}s...")
                    time.sleep(wait_time)
                else:
                    print(f"[ERROR] All {max_retries} attempts failed for {url}")
                    return None
    
    def get_available_games(self) -> List[str]:
        """Get list of available games from CSV files."""
        try:
            csv_files = [f for f in os.listdir(self.games_info_dir) if f.endswith('.csv')]
            return [f.replace('.csv', '') for f in csv_files]
        except Exception as e:
            print(f"Error getting available games: {e}")
            return []
    
    def load_game_csv(self, game_name: str) -> Optional[pd.DataFrame]:
        """Load CSV file for a specific game."""
        try:
            csv_path = os.path.join(self.games_info_dir, f"{game_name}.csv")
            if not os.path.exists(csv_path):
                return None
            
            df = pd.read_csv(csv_path)
            
            # Validate required columns
            required_columns = ['wiki', 'wiki_desc', 'youtube', 'yt_desc', 'forum', 'forum_desc']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                print(f"Missing required columns in {game_name}.csv: {missing_columns}")
                return None
            
            return df
        except Exception as e:
            print(f"Error loading CSV for {game_name}: {e}")
            return None
    
    def extract_wiki_content(self, url: str) -> Optional[Dict[str, str]]:
        """Extract content from wiki URLs."""
        try:
            if pd.isna(url) or not url or not isinstance(url, str):
                return None
            
            # ENHANCEMENT: Use fetch with retry
            response = self._fetch_with_retry(url)
            if response is None:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "Unknown Title"
            
            # Extract main content - try different selectors
            content_selectors = [
                'div.mw-content-ltr',
                'div.content',
                'div.main-content',
                'article',
                'div#content',
                'div#mw-content-text'
            ]
            
            content_text = ""
            for selector in content_selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    content_text = content_div.get_text()
                    break
            
            if not content_text:
                # Fallback: get all text from body
                body = soup.find('body')
                if body:
                    content_text = body.get_text()
            
            # Clean up the text
            content_text = self._clean_text(content_text)
            
            if len(content_text) < 50:  # Too short, probably not useful
                return None
            
            return {
                'title': title_text,
                'content': content_text,
                'url': url
            }
            
        except Exception as e:
            print(f"Error extracting wiki content from {url}: {e}")
            return None
    
    def extract_forum_content(self, url: str) -> Optional[Dict[str, str]]:
        """Extract content from forum URLs."""
        try:
            if pd.isna(url) or not url or not isinstance(url, str):
                return None
            
            # ENHANCEMENT: Use fetch with retry
            response = self._fetch_with_retry(url)
            if response is None:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "Unknown Title"
            
            # Extract forum content - try different selectors
            content_selectors = [
                'div.post-content',
                'div.entry-content',
                'div.content',
                'div.post',
                'article',
                'div[class*="post"]',
                'div[class*="content"]'
            ]
            
            content_text = ""
            for selector in content_selectors:
                content_divs = soup.select(selector)
                if content_divs:
                    content_text = " ".join([div.get_text() for div in content_divs])
                    break
            
            if not content_text:
                # Fallback: get all text from body
                body = soup.find('body')
                if body:
                    content_text = body.get_text()
            
            # Clean up the text
            content_text = self._clean_text(content_text)
            
            if len(content_text) < 50:  # Too short, probably not useful
                return None
            
            return {
                'title': title_text,
                'content': content_text,
                'url': url
            }
            
        except Exception as e:
            print(f"Error extracting forum content from {url}: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common unwanted patterns
        text = re.sub(r'Advertisement\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Cookie\s*Policy\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Privacy\s*Policy\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Terms\s*of\s*Service\s*', '', text, flags=re.IGNORECASE)
        
        # Remove navigation elements
        text = re.sub(r'Home\s*>\s*.*?>\s*', '', text)
        text = re.sub(r'You are here:\s*.*?>\s*', '', text)
        
        return text.strip()
    
    def process_game_knowledge(self, game_name: str) -> Dict[str, List[Dict]]:
        """Process all knowledge sources for a game."""
        df = self.load_game_csv(game_name)
        if df is None:
            return {'wiki': [], 'youtube': [], 'forum': []}
        
        processed_knowledge = {
            'wiki': [],
            'youtube': [],
            'forum': []
        }
        
        print(f"Processing knowledge for {game_name}...")
        
        # Process wiki entries
        for idx, row in df.iterrows():
            if not pd.isna(row['wiki']) and row['wiki']:
                print(f"Processing wiki: {row['wiki']}")
                wiki_content = self.extract_wiki_content(row['wiki'])
                if wiki_content:
                    processed_knowledge['wiki'].append({
                        'url': row['wiki'],
                        'description': row['wiki_desc'] if not pd.isna(row['wiki_desc']) else "",
                        'title': wiki_content['title'],
                        'content': wiki_content['content']
                    })
                # ENHANCEMENT: Human-like delay between requests
                self._human_delay(2.0, 4.0)
        
        # Process YouTube entries (just store descriptions)
        for idx, row in df.iterrows():
            if not pd.isna(row['youtube']) and row['youtube']:
                processed_knowledge['youtube'].append({
                    'url': row['youtube'],
                    'description': row['yt_desc'] if not pd.isna(row['yt_desc']) else "",
                    'title': f"YouTube Video: {row['yt_desc'] if not pd.isna(row['yt_desc']) else 'Unknown'}"
                })
        
        # Process forum entries
        for idx, row in df.iterrows():
            if not pd.isna(row['forum']) and row['forum']:
                print(f"Processing forum: {row['forum']}")
                forum_content = self.extract_forum_content(row['forum'])
                if forum_content:
                    processed_knowledge['forum'].append({
                        'url': row['forum'],
                        'description': row['forum_desc'] if not pd.isna(row['forum_desc']) else "",
                        'title': forum_content['title'],
                        'content': forum_content['content']
                    })
                # ENHANCEMENT: Human-like delay between requests
                self._human_delay(2.0, 4.0)
        
        print(f"Processed {len(processed_knowledge['wiki'])} wiki entries, "
            f"{len(processed_knowledge['youtube'])} YouTube entries, "
            f"{len(processed_knowledge['forum'])} forum entries for {game_name}")
        
        return processed_knowledge
    
    def validate_csv_structure(self, game_name: str) -> Tuple[bool, List[str]]:
        """Validate CSV structure for a game."""
        df = self.load_game_csv(game_name)
        if df is None:
            return False, ["CSV file not found"]
        
        required_columns = ['wiki', 'wiki_desc', 'youtube', 'yt_desc', 'forum', 'forum_desc']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return False, [f"Missing columns: {missing_columns}"]
        
        # Check for empty rows
        empty_rows = df.isnull().all(axis=1).sum()
        if empty_rows > 0:
            return False, [f"Found {empty_rows} completely empty rows"]
        
        return True, []

# Global instance
knowledge_manager = KnowledgeManager()

def get_available_games() -> List[str]:
    """Get list of available games."""
    return knowledge_manager.get_available_games()

def process_game_knowledge(game_name: str) -> Dict[str, List[Dict]]:
    """Process all knowledge sources for a game."""
    return knowledge_manager.process_game_knowledge(game_name)

def validate_csv_structure(game_name: str) -> Tuple[bool, List[str]]:
    """Validate CSV structure for a game."""
    return knowledge_manager.validate_csv_structure(game_name)

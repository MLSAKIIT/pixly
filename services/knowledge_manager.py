import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
import re
from urllib.parse import urlparse
import time

# ENHANCEMENT: Import Scrapy (only used when requests fails)
try:
    import scrapy
    from scrapy.crawler import CrawlerProcess
    from scrapy.http import Request
    from scrapy.utils.log import configure_logging
    import logging
    SCRAPY_AVAILABLE = True
    
    # Configure Scrapy logging to be quiet
    configure_logging(install_root_handler=False)
    logging.basicConfig(
        filename='scraper.log',
        format='%(levelname)s: %(message)s',
        level=logging.WARNING
    )
except ImportError:
    SCRAPY_AVAILABLE = False
    print("[WARNING] Scrapy not available. Install with: pip install scrapy")


# ENHANCEMENT: Scrapy Spider (only used as fallback)
if SCRAPY_AVAILABLE:
    class ContentSpider(scrapy.Spider):
        """Scrapy spider with anti-blocking features - used as fallback"""
        name = 'content_spider'
        
        custom_settings = {
            'ROBOTSTXT_OBEY': False,
            'CONCURRENT_REQUESTS': 1,
            'DOWNLOAD_DELAY': 3,
            'RANDOMIZE_DOWNLOAD_DELAY': True,
            'RETRY_ENABLED': True,
            'RETRY_TIMES': 3,
            'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429, 403],
            'LOG_ENABLED': False,
        }
        
        def __init__(self, urls=None, *args, **kwargs):
            super(ContentSpider, self).__init__(*args, **kwargs)
            self.start_urls = urls or []
            self.results = {}
        
        def start_requests(self):
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            ]
            import random
            for url in self.start_urls:
                yield Request(
                    url,
                    callback=self.parse,
                    errback=self.errback_handler,
                    headers={'User-Agent': random.choice(user_agents)},
                    meta={'url': url}
                )
        
        def parse(self, response):
            print(f"[SCRAPY SUCCESS] Fetched {response.url}")
            self.results[response.meta['url']] = response.text
        
        def errback_handler(self, failure):
            print(f"[SCRAPY FAILED] {failure.request.url}")
            self.results[failure.request.url] = None


class KnowledgeManager:
    def __init__(self, games_info_dir: str = "games_info"):
        """Initialize knowledge manager for CSV processing and content extraction."""
        self.games_info_dir = games_info_dir
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Ensure games_info directory exists
        os.makedirs(games_info_dir, exist_ok=True)
        
        # ENHANCEMENT: Track failed URLs for Scrapy fallback
        self.failed_urls = []
    
    # ENHANCEMENT: New method for Scrapy fallback
    def _fetch_with_scrapy(self, urls: List[str]) -> Dict[str, str]:
        """Fetch URLs using Scrapy as fallback when requests fails"""
        if not SCRAPY_AVAILABLE or not urls:
            return {}
        
        print(f"[DEBUG] Trying Scrapy for {len(urls)} failed URLs...")
        
        try:
            process = CrawlerProcess(settings={
                'ROBOTSTXT_OBEY': False,
                'CONCURRENT_REQUESTS': 1,
                'DOWNLOAD_DELAY': 3,
                'RANDOMIZE_DOWNLOAD_DELAY': True,
                'RETRY_TIMES': 3,
                'LOG_ENABLED': False,
            })
            
            spider = ContentSpider
            process.crawl(spider, urls=urls)
            process.start()
            
            return spider.results if hasattr(spider, 'results') else {}
        except Exception as e:
            print(f"[ERROR] Scrapy fallback failed: {e}")
            return {}
    
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
            
            # ORIGINAL: Try with requests first
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                html_content = response.content
                print(f"[SUCCESS] Fetched {url} with requests")
            except Exception as e:
                print(f"[WARNING] requests failed for {url}: {e}")
                # ENHANCEMENT: Mark for Scrapy fallback
                self.failed_urls.append(url)
                return None
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
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
            
            # ORIGINAL: Try with requests first
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                html_content = response.content
                print(f"[SUCCESS] Fetched {url} with requests")
            except Exception as e:
                print(f"[WARNING] requests failed for {url}: {e}")
                # ENHANCEMENT: Mark for Scrapy fallback
                self.failed_urls.append(url)
                return None
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
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
        
        # ENHANCEMENT: Reset failed URLs tracker
        self.failed_urls = []
        
        # ORIGINAL: Process wiki entries
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
                time.sleep(1)  # Be respectful to servers
        
        # ORIGINAL: Process YouTube entries (just store descriptions)
        for idx, row in df.iterrows():
            if not pd.isna(row['youtube']) and row['youtube']:
                processed_knowledge['youtube'].append({
                    'url': row['youtube'],
                    'description': row['yt_desc'] if not pd.isna(row['yt_desc']) else "",
                    'title': f"YouTube Video: {row['yt_desc'] if not pd.isna(row['yt_desc']) else 'Unknown'}"
                })
        
        # ORIGINAL: Process forum entries
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
                time.sleep(1)  # Be respectful to servers
        
        # ENHANCEMENT: Retry failed URLs with Scrapy if available
        if self.failed_urls and SCRAPY_AVAILABLE:
            print(f"\n[INFO] Retrying {len(self.failed_urls)} failed URLs with Scrapy...")
            scrapy_results = self._fetch_with_scrapy(self.failed_urls)
            
            # Process Scrapy results
            for url, html_content in scrapy_results.items():
                if html_content:
                    # Check if it's a wiki or forum URL
                    is_wiki = any(url == row['wiki'] for _, row in df.iterrows() if not pd.isna(row.get('wiki')))
                    
                    if is_wiki:
                        # Process as wiki
                        soup = BeautifulSoup(html_content, 'html.parser')
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        title = soup.find('title')
                        title_text = title.get_text().strip() if title else "Unknown Title"
                        
                        content_div = soup.select_one('div.mw-content-ltr') or soup.find('body')
                        content_text = self._clean_text(content_div.get_text() if content_div else "")
                        
                        if len(content_text) >= 50:
                            # Find the matching row
                            for _, row in df.iterrows():
                                if row['wiki'] == url:
                                    processed_knowledge['wiki'].append({
                                        'url': url,
                                        'description': row['wiki_desc'] if not pd.isna(row['wiki_desc']) else "",
                                        'title': title_text,
                                        'content': content_text
                                    })
                                    break
                    else:
                        # Process as forum
                        soup = BeautifulSoup(html_content, 'html.parser')
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        title = soup.find('title')
                        title_text = title.get_text().strip() if title else "Unknown Title"
                        
                        content_divs = soup.select('div.post-content') or [soup.find('body')]
                        content_text = self._clean_text(" ".join([div.get_text() for div in content_divs if div]))
                        
                        if len(content_text) >= 50:
                            # Find the matching row
                            for _, row in df.iterrows():
                                if row.get('forum') == url:
                                    processed_knowledge['forum'].append({
                                        'url': url,
                                        'description': row['forum_desc'] if not pd.isna(row['forum_desc']) else "",
                                        'title': title_text,
                                        'content': content_text
                                    })
                                    break
        
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

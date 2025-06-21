import os
import json
import sqlite3
import time
import uuid
import random
import platform
import requests
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import schedule
import pytz
import toml
import re
import signal
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from discord_webhook import DiscordWebhook, DiscordEmbed

from image_collage import combine_images, resize_gif
from PIL import Image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('weibo_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load configuration
def load_config() -> Dict[str, Any]:
    """Load and validate configuration file."""
    try:
        config = toml.load('config.toml')
        
        # Validate required sections
        if 'weibo' not in config:
            raise ValueError("Missing 'weibo' section in config.toml")
        if 'status' not in config:
            raise ValueError("Missing 'status' section in config.toml")
        
        # Validate webhook URLs
        for account_name, account_config in config['weibo'].items():
            if 'message_webhook' not in account_config:
                raise ValueError(f"Missing message_webhook for account {account_name}")
            
            webhook_url = account_config['message_webhook']
            if not webhook_url.startswith('https://discord.com/api/webhooks/'):
                raise ValueError(f"Invalid Discord webhook URL for account {account_name}")
        
        if 'message_webhook' not in config['status']:
            raise ValueError("Missing status message_webhook in config.toml")
        
        status_webhook = config['status']['message_webhook']
        if not status_webhook.startswith('https://discord.com/api/webhooks/'):
            raise ValueError("Invalid Discord status webhook URL")
        
        return config
        
    except FileNotFoundError:
        logger.error("Error: config.toml not found. Please copy config_example.toml to config.toml and configure it.")
        exit(1)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        exit(1)

CONFIG = load_config()


class WebDriverManager:
    """Manages webdriver creation and configuration for different platforms."""
    
    @staticmethod
    def create_driver() -> webdriver.Remote:
        """Create and configure webdriver based on platform."""
        system = platform.system()
        
        if system == 'Windows':
            return WebDriverManager._create_windows_driver()
        elif system == 'Darwin':  # macOS
            return WebDriverManager._create_macos_driver()
        elif system == 'Linux':
            return WebDriverManager._create_linux_driver()
        else:
            raise Exception(f'Unsupported operating system: {system}')
    
    @staticmethod
    def _get_chrome_options() -> ChromeOptions:
        """Get optimized Chrome options for all platforms."""
        options = ChromeOptions()
        
        # Basic options for headless operation
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')  # Don't load images to speed up scraping
        
        # Security options
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Suppress USB and other device warnings
        options.add_argument('--disable-usb-discovery')
        options.add_argument('--disable-usb-keyboard-detect')
        options.add_argument('--disable-device-discovery-notifications')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')  # Only show fatal errors
        options.add_argument('--silent')
        
        # Suppress voice transcription and other features
        options.add_argument('--disable-speech-api')
        options.add_argument('--disable-speech-synthesis-api')
        options.add_argument('--disable-voice-transcription')
        options.add_argument('--disable-media-session')
        options.add_argument('--disable-audio-service')
        
        # Suppress more Chrome internal logs
        options.add_argument('--disable-logging-redirect')
        options.add_argument('--disable-breakpad')
        options.add_argument('--disable-crash-reporter')
        options.add_argument('--disable-in-process-stack-traces')
        options.add_argument('--disable-hang-monitor')
        
        # Performance optimizations
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-ipc-flooding-protection')
        
        # Memory optimizations
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        
        # User agent to avoid detection
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        return options
    
    @staticmethod
    def _create_windows_driver() -> webdriver.Remote:
        """Create Chrome driver for Windows using webdriver-manager."""
        try:
            options = WebDriverManager._get_chrome_options()
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Execute script to remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
                
        except Exception as e:
            logger.warning(f"Failed to create Chrome driver: {e}")
            logger.info("Trying Firefox as fallback...")
            return WebDriverManager._create_firefox_driver()
    
    @staticmethod
    def _create_macos_driver() -> webdriver.Remote:
        """Create Firefox driver for macOS."""
        try:
            options = FirefoxOptions()
            options.add_argument('--headless')
            options.set_preference('devtools.jsonview.enabled', False)
            
            # Use webdriver-manager to automatically download and manage GeckoDriver
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
            return driver
        except Exception as e:
            logger.warning(f"Failed to create Firefox driver: {e}")
            logger.info("Trying Chrome as fallback...")
            return WebDriverManager._create_chrome_driver()
    
    @staticmethod
    def _create_linux_driver() -> webdriver.Remote:
        """Create Chrome driver for Linux."""
        try:
            options = WebDriverManager._get_chrome_options()
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Execute script to remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
        except Exception as e:
            logger.warning(f"Failed to create Chrome driver: {e}")
            logger.info("Trying Firefox as fallback...")
            return WebDriverManager._create_firefox_driver()
    
    @staticmethod
    def _create_chrome_driver() -> webdriver.Chrome:
        """Create Chrome webdriver with optimized options."""
        try:
            options = WebDriverManager._get_chrome_options()
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Execute script to remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
        except Exception as e:
            logger.error(f"Error creating Chrome driver: {e}")
            raise
    
    @staticmethod
    def _create_firefox_driver() -> webdriver.Remote:
        """Create Firefox driver as fallback."""
        try:
            options = FirefoxOptions()
            options.add_argument('--headless')
            options.set_preference('devtools.jsonview.enabled', False)
            
            # Use webdriver-manager to automatically download and manage GeckoDriver
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
            return driver
        except Exception as e:
            logger.error(f"Failed to create Firefox driver: {e}")
            raise Exception("Could not create any webdriver. Please check your browser installation.")
    
    @staticmethod
    def _is_running_in_china() -> bool:
        """Check if the current IP location is within China."""
        try:
            response = requests.get("http://ip-api.com/json/?fields=countryCode", timeout=5)
            if response.status_code == 200:
                json_response = response.json()
                return json_response.get("countryCode") == "CN"
            return False
        except requests.RequestException:
            return False


class DatabaseManager:
    """Manages SQLite database operations with improved security."""
    
    def __init__(self, db_path: str = 'weibo.db'):
        # Validate database path
        if not isinstance(db_path, str) or not db_path.strip():
            raise ValueError("Database path must be a non-empty string")
        
        # Prevent path traversal attacks
        db_path = Path(db_path).resolve()
        if not str(db_path).startswith(str(Path.cwd().resolve())):
            raise ValueError("Database path must be within current working directory")
        
        self.db_path = str(db_path)
        self.connection = None
        self.cursor = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the database and create tables if they don't exist."""
        try:
            self.connection = sqlite3.connect(self.db_path, timeout=30.0)
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.execute("PRAGMA journal_mode = WAL")
            self.cursor = self.connection.cursor()
            
            # Create table with proper constraints
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS weibo (
                    id INTEGER PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index for better performance
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_weibo_id ON weibo(id)
            ''')
            
            self.connection.commit()
            logger.info(f"Database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def check_and_add_id(self, weibo_id: int) -> bool:
        """Check if ID exists in database, add if not, return True if new."""
        try:
            # Validate input
            if not isinstance(weibo_id, int) or weibo_id <= 0:
                logger.warning(f"Invalid weibo_id: {weibo_id}")
                return False
            
            self.cursor.execute('''SELECT id FROM weibo WHERE id = ?''', (weibo_id,))
            if self.cursor.fetchone() is None:
                self.cursor.execute('''
                    INSERT INTO weibo (id, processed_at) VALUES (?, CURRENT_TIMESTAMP)
                ''', (weibo_id,))
                self.connection.commit()
                logger.debug(f"Added new weibo ID: {weibo_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Database operation error: {e}")
            return False
    
    def add_all_ids(self, weibo_items: List[Dict[str, Any]]):
        """Add all IDs from weibo items to database."""
        try:
            if not isinstance(weibo_items, list):
                logger.warning("weibo_items must be a list")
                return
            
            # Validate and extract IDs
            valid_ids = []
            for item in weibo_items:
                if isinstance(item, dict) and 'id' in item:
                    weibo_id = item['id']
                    if isinstance(weibo_id, int) and weibo_id > 0:
                        valid_ids.append(weibo_id)
                    else:
                        logger.warning(f"Invalid weibo_id in item: {weibo_id}")
            
            if valid_ids:
                # Use executemany for better performance
                self.cursor.executemany('''
                    INSERT OR IGNORE INTO weibo (id, processed_at) VALUES (?, CURRENT_TIMESTAMP)
                ''', [(id,) for id in valid_ids])
                self.connection.commit()
                logger.info(f"Added {len(valid_ids)} weibo IDs to database")
            
        except Exception as e:
            logger.error(f"Error adding IDs to database: {e}")
    
    def get_recent_ids(self, limit: int = 100) -> List[int]:
        """Get recent weibo IDs for debugging."""
        try:
            if not isinstance(limit, int) or limit <= 0:
                limit = 100
            
            self.cursor.execute('''
                SELECT id FROM weibo ORDER BY processed_at DESC LIMIT ?
            ''', (limit,))
            return [row[0] for row in self.cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error getting recent IDs: {e}")
            return []
    
    def cleanup_old_records(self, days: int = 30):
        """Clean up old records to prevent database bloat."""
        try:
            if not isinstance(days, int) or days <= 0:
                days = 30
            
            self.cursor.execute('''
                DELETE FROM weibo WHERE processed_at < datetime('now', '-{} days')
            '''.format(days))
            
            deleted_count = self.cursor.rowcount
            self.connection.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old records")
                
        except Exception as e:
            logger.error(f"Error cleaning up old records: {e}")
    
    def close(self):
        """Close database connection safely."""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class ImageManager:
    """Manages image download, processing, and cleanup with improved security."""
    
    def __init__(self, image_dir: Path):
        # Validate image directory
        if not isinstance(image_dir, Path):
            image_dir = Path(image_dir)
        
        # Ensure directory is within current working directory for security
        image_dir = image_dir.resolve()
        if not str(image_dir).startswith(str(Path.cwd().resolve())):
            raise ValueError("Image directory must be within current working directory")
        
        self.image_dir = image_dir
        self.image_dir.mkdir(exist_ok=True)
        self.should_delete_images = True
        
        # Track downloaded files for cleanup
        self.downloaded_files = set()
        
        logger.info(f"Image manager initialized: {self.image_dir}")
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL for security."""
        if not isinstance(url, str) or not url.strip():
            return False
        
        # Check for valid image URLs
        valid_domains = [
            'wx1.sinaimg.cn', 'wx2.sinaimg.cn', 'wx3.sinaimg.cn', 'wx4.sinaimg.cn',
            'sinaimg.cn', 'weibo.com', 'weibo.cn'
        ]
        
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            
            # Must be HTTPS
            if parsed.scheme != 'https':
                return False
            
            # Must be from valid domains
            if not any(domain in parsed.netloc for domain in valid_domains):
                return False
            
            # Must have valid image extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            if not any(parsed.path.lower().endswith(ext) for ext in valid_extensions):
                return False
            
            return True
            
        except Exception:
            return False
    
    def download_image(self, url: str) -> Optional[Path]:
        """Download a single image from URL with security validation."""
        try:
            # Validate URL
            if not self._validate_url(url):
                logger.warning(f"Invalid or unsafe URL: {url}")
                return None
            
            # Set up headers to mimic browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://weibo.com/',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site'
            }
            
            # Download with timeout and size limit
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            
            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} for URL: {url}")
                return None
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                logger.warning(f"Invalid content type: {content_type} for URL: {url}")
                return None
            
            # Check file size (limit to 50MB)
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > 50 * 1024 * 1024:
                logger.warning(f"File too large: {content_length} bytes for URL: {url}")
                return None
            
            # Generate safe filename
            file_extension = Path(url).suffix
            if not file_extension or file_extension not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                file_extension = '.jpg'  # Default to jpg
            
            file_name = f"{uuid.uuid4()}{file_extension}"
            file_path = self.image_dir / file_name
            
            # Download file with size tracking
            downloaded_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        downloaded_size += len(chunk)
                        if downloaded_size > 50 * 1024 * 1024:  # 50MB limit
                            f.close()
                            file_path.unlink(missing_ok=True)
                            logger.warning(f"File exceeded size limit during download: {url}")
                            return None
                        f.write(chunk)
            
            # Track downloaded file
            self.downloaded_files.add(file_path)
            logger.debug(f"Downloaded image: {file_path.name} ({downloaded_size} bytes)")
            return file_path
            
        except requests.RequestException as e:
            logger.error(f"Request error downloading image {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading image {url}: {e}")
            return None
    
    def download_images(self, urls: List[str]) -> List[Path]:
        """Download multiple images from URLs with validation."""
        if not isinstance(urls, list):
            logger.warning("URLs must be a list")
            return []
        
        downloaded_images = []
        for url in urls:
            if not isinstance(url, str):
                logger.warning(f"Invalid URL type: {type(url)}")
                continue
            
            image_path = self.download_image(url)
            if image_path:
                downloaded_images.append(image_path)
        
        logger.info(f"Downloaded {len(downloaded_images)}/{len(urls)} images")
        return downloaded_images
    
    def delete_images(self, file_paths: List[Path]):
        """Delete multiple image files safely."""
        if not isinstance(file_paths, list):
            logger.warning("file_paths must be a list")
            return
        
        deleted_count = 0
        for file_path in file_paths:
            try:
                if isinstance(file_path, (str, Path)):
                    path = Path(file_path)
                    
                    # Security check: ensure file is in our image directory
                    if not str(path.resolve()).startswith(str(self.image_dir.resolve())):
                        logger.warning(f"Attempted to delete file outside image directory: {path}")
                        continue
                    
                    if path.exists():
                        path.unlink()
                        deleted_count += 1
                        
                        # Remove from tracked files
                        if path in self.downloaded_files:
                            self.downloaded_files.remove(path)
                            
            except Exception as e:
                logger.error(f"Error deleting file {file_path}: {e}")
        
        if deleted_count > 0:
            logger.debug(f"Deleted {deleted_count} image files")
    
    def cleanup_all(self):
        """Clean up all downloaded images."""
        try:
            for file_path in list(self.downloaded_files):
                try:
                    if file_path.exists():
                        file_path.unlink()
                except Exception as e:
                    logger.error(f"Error cleaning up {file_path}: {e}")
            
            self.downloaded_files.clear()
            logger.info("Cleaned up all downloaded images")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_downloaded_files(self) -> List[Path]:
        """Get list of currently downloaded files."""
        return list(self.downloaded_files)


class RateLimiter:
    """Rate limiter to prevent overwhelming the target server."""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def can_proceed(self) -> bool:
        """Check if we can make another request."""
        now = time.time()
        
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        
        # Check if we're under the limit
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def wait_if_needed(self):
        """Wait if we need to respect rate limits."""
        while not self.can_proceed():
            sleep_time = 1
            logger.debug(f"Rate limit reached, waiting {sleep_time} second")
            time.sleep(sleep_time)


class WeiboScraper:
    """Main scraper class for Weibo posts with improved security and error handling."""
    
    def __init__(self, account_names: List[str] = 'auto'):
        # Initialize components
        self.driver = None
        self.db_manager = None
        self.image_manager = None
        self.rate_limiter = RateLimiter(max_requests=5, time_window=60)  # 5 requests per minute
        
        try:
            self.driver = WebDriverManager.create_driver()
            self.db_manager = DatabaseManager()
            self.image_manager = ImageManager(Path(__file__).parent / 'images')
        except Exception as e:
            logger.error(f"Failed to initialize scraper components: {e}")
            self.cleanup()
            raise
        
        # Load kawaii content
        self._load_kawaii_content()
        
        # Set account names
        if account_names == 'auto':
            self.account_names = list(CONFIG['weibo'].keys())
        else:
            self.account_names = account_names
            for account in account_names:
                if account not in CONFIG['weibo'].keys():
                    raise Exception(f'Account {account} not found in config.toml')
        
        logger.info(f"WeiboScraper initialized with {len(self.account_names)} accounts")
    
    def _load_kawaii_content(self):
        """Load kawaii content from JSON file with fallback."""
        try:
            with open('kawaii_content.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.kawaii_emojis = data.get('kawaii_emojis', ["(✿ ♥‿♥)", "(｡♥‿♥｡)"])
            self.kawaii_texts = data.get('kawaii_texts', ["ぴーかぴかに動いてるよ！", "全システム、ばっちりだよ！"])
            self.kawaii_titles = data.get('kawaii_titles', ["ぴょんぴょんアップデート！🐰", "ちゅるちゅるスクリプト！🍜"])
        except Exception as e:
            logger.warning(f"Error loading kawaii content: {e}")
            # Fallback content
            self.kawaii_emojis = ["(✿ ♥‿♥)", "(｡♥‿♥｡)"]
            self.kawaii_texts = ["ぴーかぴかに動いてるよ！", "全システム、ばっちりだよ！"]
            self.kawaii_titles = ["ぴょんぴょんアップデート！🐰", "ちゅるちゅるスクリプト！🍜"]
    
    def start(self):
        """Start the scraper with scheduled tasks."""
        logger.info("Starting Weibo scraper...")
        
        try:
            # Run initial scan
            for account in self.account_names:
                try:
                    self.scan(CONFIG['weibo'][account])
                except Exception as e:
                    logger.error(f"Error scanning account {account}: {e}")
            
            # Schedule recurring tasks
            schedule.every(10).minutes.do(self._scan_all_accounts)
            schedule.every(6).hours.do(self.send_status, CONFIG['status']['message_webhook'])
            schedule.every(24).hours.do(self._cleanup_old_data)  # Daily cleanup
            
            # Send initial status
            self.send_status(CONFIG['status']['message_webhook'])
            
            logger.info("Scraper started. Press Ctrl+C to stop.")
            
            # Main loop
            while True:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\nStopping scraper...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            self.cleanup()
    
    def _scan_all_accounts(self):
        """Scan all configured accounts."""
        for account in self.account_names:
            try:
                self.scan(CONFIG['weibo'][account])
            except Exception as e:
                logger.error(f"Error scanning account {account}: {e}")
    
    def _cleanup_old_data(self):
        """Clean up old data periodically."""
        try:
            if self.db_manager:
                self.db_manager.cleanup_old_records(days=30)
            if self.image_manager:
                self.image_manager.cleanup_all()
            logger.info("Periodic cleanup completed")
        except Exception as e:
            logger.error(f"Error during periodic cleanup: {e}")
    
    def cleanup(self):
        """Clean up resources safely."""
        logger.info("Starting cleanup...")
        
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
                logger.info("WebDriver closed")
        except Exception as e:
            logger.error(f"Error closing webdriver: {e}")
        
        try:
            if hasattr(self, 'db_manager') and self.db_manager:
                self.db_manager.close()
        except Exception as e:
            logger.error(f"Error closing database: {e}")
        
        try:
            if hasattr(self, 'image_manager') and self.image_manager:
                self.image_manager.cleanup_all()
        except Exception as e:
            logger.error(f"Error cleaning up images: {e}")
        
        logger.info("Cleanup completed.")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def get_weibo_content_once(self, endpoints: Dict[str, str]) -> Optional[List[Dict[str, Any]]]:
        """Get Weibo content once from the AJAX endpoint with rate limiting."""
        try:
            # Rate limiting
            self.rate_limiter.wait_if_needed()
            
            # Check if driver is still alive
            if not self._is_driver_alive():
                self._recreate_driver()
            
            self.driver.get(endpoints['ajax_url'])
            time.sleep(10)  # Wait for dynamic content
            self.driver.implicitly_wait(20)
            
            pre_tag = self.driver.find_element(By.TAG_NAME, 'pre')
            json_text = pre_tag.text
            
            # Validate JSON before parsing
            if not json_text.strip():
                logger.warning("Empty response from Weibo API")
                return None
            
            content = json.loads(json_text)
            
            # Validate response structure
            if not isinstance(content, dict) or 'data' not in content:
                logger.warning("Invalid response structure from Weibo API")
                return None
            
            data = content['data']
            if not isinstance(data, dict) or 'list' not in data:
                logger.warning("Invalid data structure in Weibo API response")
                return None
            
            return data['list']
            
        except Exception as e:
            logger.error(f"Error getting Weibo content: {e}")
            return None
    
    def _is_driver_alive(self) -> bool:
        """Check if the webdriver is still alive."""
        try:
            # Try to get current URL to test if driver is responsive
            self.driver.current_url
            return True
        except Exception:
            return False
    
    def _recreate_driver(self):
        """Recreate the webdriver."""
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            logger.warning(f"Error closing old driver: {e}")
        
        try:
            self.driver = WebDriverManager.create_driver()
            logger.info("WebDriver recreated successfully")
        except Exception as e:
            logger.error(f"Failed to recreate WebDriver: {e}")
            raise
    
    def get_weibo_content_loop(self, endpoints: Dict[str, str]) -> Optional[List[Dict[str, Any]]]:
        """Get Weibo content with retry logic and improved error handling."""
        max_retries = 10
        retry_count = 0
        
        logger.info(f'Getting Weibo content... @ {datetime.now()}')
        
        while retry_count < max_retries:
            try:
                content = self.get_weibo_content_once(endpoints)
                if content:
                    logger.info(f"Successfully retrieved {len(content)} posts")
                    return content
                
                retry_count += 1
                logger.warning(f'Retrying... ({retry_count}/{max_retries})')
                time.sleep(60)
                
            except Exception as e:
                retry_count += 1
                logger.error(f'Error during retry {retry_count}/{max_retries}: {e}')
                time.sleep(60)
        
        logger.error('Failed to get content after maximum retries')
        return None
    
    def scan(self, endpoints: Dict[str, str]):
        """Scan for new Weibo posts and process them."""
        try:
            content = self.get_weibo_content_loop(endpoints)
            if content:
                # Process in reverse order (oldest first)
                processed_count = 0
                for item in reversed(content):
                    try:
                        if self.db_manager.check_and_add_id(item['id']):
                            self.parse_item(item, endpoints)
                            processed_count += 1
                            time.sleep(5)  # Rate limiting
                    except Exception as e:
                        logger.error(f"Error processing item {item.get('id', 'unknown')}: {e}")
                
                if processed_count > 0:
                    logger.info(f"Processed {processed_count} new posts")
            else:
                logger.warning('Failed to get content')
                
        except Exception as e:
            logger.error(f"Error during scan: {e}")
    
    def create_webhook_instance(self, endpoints: Dict[str, str], **kwargs) -> DiscordWebhook:
        """Create a Discord webhook instance with validation."""
        webhook_url = endpoints.get('message_webhook')
        if not webhook_url or not webhook_url.startswith('https://discord.com/api/webhooks/'):
            raise ValueError("Invalid Discord webhook URL")
        
        avatar_url = endpoints.get('avatar_url')
        return DiscordWebhook(url=webhook_url, avatar_url=avatar_url, **kwargs)
    
    def parse_item(self, item: Dict[str, Any], endpoints: Dict[str, str]) -> int:
        """Parse and send a Weibo item to Discord with improved error handling."""
        try:
            webhook_message = self.create_webhook_instance(endpoints)
            
            # Create embed
            embed = self._create_base_embed(item, endpoints)
            
            # Debug image sizes if available
            if 'pic_infos' in item or ('retweeted_status' in item and 'pic_infos' in item['retweeted_status']):
                self.debug_image_sizes(item)
            
            # Handle different content types
            if 'retweeted_status' in item:
                return self.parse_item_retweet(item, embed, endpoints)
            elif 'pic_infos' in item:
                return self.parse_item_with_images(item, embed, endpoints)
            elif 'page_info' in item:
                if 'media_info' in item['page_info']:
                    return self.parse_item_with_video(item, embed, endpoints)
                elif 'page_pic' in item['page_info']:
                    return self.parse_item_with_page_pic(item, embed, endpoints)
                else:
                    # Log unknown page_info structure
                    debug_file = f'debug_{str(uuid.uuid4())[-10:]}.json'
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        json.dump(item, f, indent=2, ensure_ascii=False)
                    logger.warning(f'Unknown page_info structure logged to {debug_file}')
                    return self.parse_item_text_only(item, embed, endpoints)
            else:
                return self.parse_item_text_only(item, embed, endpoints)
                
        except Exception as e:
            logger.error(f"Error parsing item {item.get('id', 'unknown')}: {e}")
            return 500
    
    def _create_base_embed(self, item: Dict[str, Any], endpoints: Dict[str, str]) -> DiscordEmbed:
        """Create base Discord embed for a Weibo item."""
        try:
            text_raw = item.get('text_raw', '')
            created_at = item.get('created_at', '')
            title = endpoints.get('title', 'Weibo Post')
            source = item.get('source', 'Unknown')
            
            embed_color = 16738740
            dt = datetime.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
            discord_timestamp = dt.timestamp()
            
            embed = DiscordEmbed(
                title=title,
                description=text_raw,
                color=embed_color,
                url=endpoints.get('read_link_url', '')
            )
            embed.set_footer(text=f"来自 {source}")
            embed.set_timestamp(discord_timestamp)
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating base embed: {e}")
            # Return minimal embed as fallback
            embed = DiscordEmbed(
                title="Weibo Post",
                description="Error processing post",
                color=16738740
            )
            return embed
    
    def parse_item_text_only(self, item: Dict[str, Any], embed: DiscordEmbed, endpoints: Dict[str, str]) -> int:
        """Parse and send text-only Weibo post."""
        try:
            webhook_message = self.create_webhook_instance(endpoints)
            webhook_message.add_embed(embed)
            response = webhook_message.execute()
            return response.status_code
        except Exception as e:
            logger.error(f"Error sending text-only post: {e}")
            return 500
    
    def parse_item_with_page_pic(self, item: Dict[str, Any], embed: DiscordEmbed, endpoints: Dict[str, str]) -> int:
        """Parse and send Weibo post with page picture."""
        try:
            image_url = item['page_info']['page_pic']
            image_path = self.image_manager.download_image(image_url)
            
            if image_path:
                webhook_message = self.create_webhook_instance(endpoints)
                with image_path.open('rb') as f:
                    webhook_message.add_file(file=f.read(), filename=image_path.name)
                embed.set_image(url=f'attachment://{image_path.name}')
                webhook_message.add_embed(embed)
                response = webhook_message.execute()
                
                if self.image_manager.should_delete_images:
                    self.image_manager.delete_images([image_path])
                
                return response.status_code
            else:
                return self.parse_item_text_only(item, embed, endpoints)
                
        except Exception as e:
            logger.error(f"Error processing page pic: {e}")
            return self.parse_item_text_only(item, embed, endpoints)
    
    def parse_item_with_images(self, item: Dict[str, Any], embed: DiscordEmbed, endpoints: Dict[str, str]) -> int:
        """Parse and send Weibo post with images."""
        try:
            # Try to get lower resolution images first to reduce file sizes
            image_urls = []
            for k, v in item['pic_infos'].items():
                # Try different image sizes in order of preference (smaller first)
                if 'bmiddle' in v:
                    image_urls.append(v['bmiddle']['url'])
                elif 'large' in v:
                    image_urls.append(v['large']['url'])
                elif 'mw1024' in v:
                    image_urls.append(v['mw1024']['url'])
                elif 'mw690' in v:
                    image_urls.append(v['mw690']['url'])
                elif 'mw480' in v:
                    image_urls.append(v['mw480']['url'])
                elif 'original' in v:
                    image_urls.append(v['original']['url'])
                else:
                    # Fallback to original if no other sizes available
                    image_urls.append(v['original']['url'])
            
            image_paths = self.image_manager.download_images(image_urls)
            
            if not image_paths:
                return self.parse_item_text_only(item, embed, endpoints)
            
            # Compress individual images first
            compressed_paths = []
            for image_path in image_paths:
                compressed_path = self.compress_image(image_path, max_size_mb=3.0)
                compressed_paths.append(compressed_path)
            
            # Create collage or use single image
            if len(compressed_paths) == 1:
                collage_path = compressed_paths[0]
            else:
                try:
                    collage_path = combine_images(compressed_paths)
                except Exception as e:
                    logger.error(f"Error creating image collage: {e}")
                    # Fallback to text-only if collage fails
                    return self.parse_item_text_only(item, embed, endpoints)
            
            # Check file size before sending
            try:
                file_size_mb = collage_path.stat().st_size / (1024 ** 2)
                if file_size_mb > 3:  # Discord webhook limit is 8MB, use 3MB to be safe
                    logger.warning(f"Image collage too large ({file_size_mb:.1f}MB), sending text-only")
                    return self.parse_item_text_only(item, embed, endpoints)
            except Exception as e:
                logger.error(f"Error checking file size: {e}")
                return self.parse_item_text_only(item, embed, endpoints)
            
            webhook_message = self.create_webhook_instance(endpoints)
            try:
                with collage_path.open("rb") as f:
                    webhook_message.add_file(file=f.read(), filename=collage_path.name)
                embed.set_image(url=f'attachment://{collage_path.name}')
                webhook_message.add_embed(embed)
                response = webhook_message.execute()
                
                # Send animated images separately
                if len(image_paths) > 1:
                    time.sleep(1)
                    self.send_animated_images(image_paths, endpoints)
                
                # Cleanup
                if self.image_manager.should_delete_images and compressed_paths:
                    self.image_manager.delete_images(compressed_paths)
                    if collage_path and collage_path not in compressed_paths:
                        self.image_manager.delete_images([collage_path])
                
                return response.status_code
            except Exception as e:
                logger.error(f"Error sending image post: {e}")
                # Fallback to text-only
                return self.parse_item_text_only(item, embed, endpoints)
                
        except Exception as e:
            logger.error(f"Error processing images: {e}")
            return self.parse_item_text_only(item, embed, endpoints)
    
    def send_animated_images(self, image_paths: List[Path], endpoints: Dict[str, str]) -> int:
        """Send animated images (GIFs) separately."""
        try:
            gif_webhook = self.create_webhook_instance(endpoints)
            files_to_delete = []
            
            for image_path in image_paths:
                if image_path.suffix.lower() == ".gif":
                    # Check file size first - Discord has 8MB limit for webhooks
                    file_size_mb = image_path.stat().st_size / (1024 ** 2)
                    
                    # Resize if too large (keep under 3MB to be safe)
                    while file_size_mb > 3:
                        try:
                            image_path = resize_gif(image_path)
                            files_to_delete.append(image_path)
                            file_size_mb = image_path.stat().st_size / (1024 ** 2)
                        except Exception as e:
                            logger.error(f"Error resizing GIF {image_path}: {e}")
                            break
                    
                    # Only add if file is small enough
                    if file_size_mb <= 3:
                        try:
                            with image_path.open("rb") as f:
                                gif_webhook.add_file(file=f.read(), filename=image_path.name)
                        except Exception as e:
                            logger.error(f"Error reading GIF file {image_path}: {e}")
                    else:
                        logger.warning(f"Skipping GIF {image_path.name} - too large ({file_size_mb:.1f}MB)")
            
            # Execute only if there are GIFs
            if gif_webhook.files:
                try:
                    response = gif_webhook.execute()
                    if self.image_manager.should_delete_images:
                        self.image_manager.delete_images(files_to_delete)
                    return response.status_code
                except Exception as e:
                    logger.error(f"Error sending animated images: {e}")
                    return 500
            else:
                return 204  # No content
                
        except Exception as e:
            logger.error(f"Error in send_animated_images: {e}")
            return 500
    
    def parse_item_with_video(self, item: Dict[str, Any], embed: DiscordEmbed, endpoints: Dict[str, str]) -> int:
        """Parse and send Weibo post with video."""
        try:
            video_url = item['page_info']['media_info']['stream_url']
            
            # Send embed and video separately
            webhook_message = self.create_webhook_instance(endpoints)
            video_webhook = self.create_webhook_instance(endpoints, content=video_url)
            
            webhook_message.add_embed(embed)
            response1 = webhook_message.execute()
            response2 = video_webhook.execute()
            
            # Return appropriate status code
            if response1.status_code < 300 and response2.status_code < 300:
                return 200
            elif response1.status_code < 300:
                return response2.status_code
            else:
                return response1.status_code
                
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return self.parse_item_text_only(item, embed, endpoints)
    
    def parse_item_retweet(self, item: Dict[str, Any], embed: DiscordEmbed, endpoints: Dict[str, str]) -> int:
        """Parse and send retweeted Weibo post."""
        try:
            retweeted_status = item['retweeted_status']
            retweet_text = retweeted_status['text_raw']
            user_name = retweeted_status['user']['screen_name']
            
            # Handle images in retweet
            image_paths = []
            collage_path = None
            
            if 'pic_infos' in retweeted_status:
                # Try to get lower resolution images first to reduce file sizes
                image_urls = []
                for k, v in retweeted_status['pic_infos'].items():
                    # Try different image sizes in order of preference (smaller first)
                    if 'bmiddle' in v:
                        image_urls.append(v['bmiddle']['url'])
                    elif 'large' in v:
                        image_urls.append(v['large']['url'])
                    elif 'mw1024' in v:
                        image_urls.append(v['mw1024']['url'])
                    elif 'mw690' in v:
                        image_urls.append(v['mw690']['url'])
                    elif 'mw480' in v:
                        image_urls.append(v['mw480']['url'])
                    elif 'original' in v:
                        image_urls.append(v['original']['url'])
                    else:
                        # Fallback to original if no other sizes available
                        image_urls.append(v['original']['url'])
                
                image_paths = self.image_manager.download_images(image_urls)
                
                # Compress individual images first
                compressed_paths = []
                for image_path in image_paths:
                    compressed_path = self.compress_image(image_path, max_size_mb=3.0)
                    compressed_paths.append(compressed_path)
                
                if len(compressed_paths) == 1:
                    collage_path = compressed_paths[0]
                elif len(compressed_paths) > 1:
                    try:
                        collage_path = combine_images(compressed_paths)
                    except Exception as e:
                        logger.error(f"Error creating retweet image collage: {e}")
                        collage_path = None
            
            # Add image to embed if available and not too large
            if collage_path:
                try:
                    file_size_mb = collage_path.stat().st_size / (1024 ** 2)
                    if file_size_mb <= 3:  # Check file size
                        webhook_message = self.create_webhook_instance(endpoints)
                        with collage_path.open("rb") as f:
                            webhook_message.add_file(file=f.read(), filename=collage_path.name)
                        embed.set_image(url=f'attachment://{collage_path.name}')
                    else:
                        logger.warning(f"Retweet image too large ({file_size_mb:.1f}MB), sending without image")
                        webhook_message = self.create_webhook_instance(endpoints)
                except Exception as e:
                    logger.error(f"Error processing retweet image: {e}")
                    webhook_message = self.create_webhook_instance(endpoints)
            else:
                webhook_message = self.create_webhook_instance(endpoints)
            
            embed.add_embed_field(name=f"@{user_name}", value=retweet_text)
            webhook_message.add_embed(embed)
            
            try:
                response = webhook_message.execute()
                
                # Cleanup
                if self.image_manager.should_delete_images and image_paths:
                    self.image_manager.delete_images(image_paths)
                    if collage_path and collage_path not in image_paths:
                        self.image_manager.delete_images([collage_path])
                
                return response.status_code
            except Exception as e:
                logger.error(f"Error sending retweet: {e}")
                return 500
                
        except Exception as e:
            logger.error(f"Error processing retweet: {e}")
            return self.parse_item_text_only(item, embed, endpoints)
    
    def send_status(self, status_webhook_url: str) -> int:
        """Send status update to Discord."""
        try:
            webhook_status = DiscordWebhook(url=status_webhook_url)
            embed_color = 16738740
            
            emoji = random.choice(self.kawaii_emojis)
            text = random.choice(self.kawaii_texts)
            title = random.choice(self.kawaii_titles)
            
            # Get machine info
            if platform.system() == 'Windows':
                machine_info = f"{platform.node()} {platform.machine()}"
            else:
                machine_info = f"{os.uname().nodename} {os.uname().machine}"
            
            # Get current time in GMT+9
            timezone = pytz.timezone('Etc/GMT-9')
            time_now = datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
            
            embed = DiscordEmbed(
                title=title,
                description=f"{emoji} {text} @ {time_now} -- {machine_info}",
                color=embed_color
            )
            embed.set_timestamp()
            
            webhook_status.add_embed(embed)
            response = webhook_status.execute()
            return response.status_code
            
        except Exception as e:
            logger.error(f"Error sending status: {e}")
            return 500

    def debug_image_sizes(self, item: Dict[str, Any]):
        """Debug function to see what image sizes are available."""
        try:
            if 'pic_infos' in item:
                logger.debug("Available image sizes:")
                for k, v in item['pic_infos'].items():
                    logger.debug(f"  Image {k}:")
                    for size_key in v.keys():
                        if isinstance(v[size_key], dict) and 'url' in v[size_key]:
                            logger.debug(f"    {size_key}: {v[size_key]['url']}")
            elif 'retweeted_status' in item and 'pic_infos' in item['retweeted_status']:
                logger.debug("Available retweet image sizes:")
                for k, v in item['retweeted_status']['pic_infos'].items():
                    logger.debug(f"  Retweet Image {k}:")
                    for size_key in v.keys():
                        if isinstance(v[size_key], dict) and 'url' in v[size_key]:
                            logger.debug(f"    {size_key}: {v[size_key]['url']}")
        except Exception as e:
            logger.error(f"Error in debug_image_sizes: {e}")

    def compress_image(self, image_path: Path, max_size_mb: float = 5.0) -> Path:
        """Compress a single image to reduce file size."""
        try:
            file_size_mb = image_path.stat().st_size / (1024 ** 2)
            if file_size_mb <= max_size_mb:
                return image_path
            
            logger.info(f"Compressing {image_path.name} from {file_size_mb:.1f}MB")
            
            # Open and compress the image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary for JPEG compression
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparent images
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Drastically resize to max 1024x1024 while preserving aspect ratio
                original_width, original_height = img.size
                max_dimension = 1024
                
                # Calculate new dimensions preserving aspect ratio
                if original_width > max_dimension or original_height > max_dimension:
                    # Calculate scale factor to fit within 1024x1024
                    scale_factor = min(max_dimension / original_width, max_dimension / original_height)
                    new_width = int(original_width * scale_factor)
                    new_height = int(original_height * scale_factor)
                    
                    # Ensure dimensions don't exceed 1024
                    new_width = min(new_width, max_dimension)
                    new_height = min(new_height, max_dimension)
                    
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    logger.debug(f"Resized from {original_width}x{original_height} to {new_width}x{new_height}")
                
                # Try to compress with aggressive quality reduction
                quality = 70  # Start with lower quality
                compression_attempts = 0
                max_attempts = 10
                
                while file_size_mb > max_size_mb and compression_attempts < max_attempts:
                    compression_attempts += 1
                    
                    # Create compressed version
                    compressed_path = image_path.parent / f"compressed_{image_path.name}"
                    img.save(compressed_path, 'JPEG', quality=quality, optimize=True)
                    
                    # Check new size
                    new_size_mb = compressed_path.stat().st_size / (1024 ** 2)
                    
                    if new_size_mb <= max_size_mb:
                        # Success! Replace original with compressed version
                        image_path.unlink()
                        compressed_path.rename(image_path)
                        logger.info(f"Compressed to {new_size_mb:.1f}MB with quality {quality}")
                        return image_path
                    else:
                        # Try again with much lower quality
                        quality = max(10, quality - 15)  # Reduce quality more aggressively
                        compressed_path.unlink()
                
                # If still too large, resize even more aggressively
                if file_size_mb > max_size_mb:
                    logger.info(f"Resizing {image_path.name} more aggressively to reduce size")
                    
                    # Calculate target dimensions based on file size
                    # Estimate: each pixel is roughly 3 bytes for RGB
                    target_pixels = int((max_size_mb * 1024 * 1024) / 3)
                    current_pixels = img.width * img.height
                    
                    if current_pixels > target_pixels:
                        scale_factor = (target_pixels / current_pixels) ** 0.5
                        new_width = max(100, int(img.width * scale_factor))
                        new_height = max(100, int(img.height * scale_factor))
                        
                        # Ensure we don't exceed 1024x1024
                        new_width = min(new_width, max_dimension)
                        new_height = min(new_height, max_dimension)
                        
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        img.save(image_path, 'JPEG', quality=40, optimize=True)
                        
                        new_size_mb = image_path.stat().st_size / (1024 ** 2)
                        logger.info(f"Resized to {new_width}x{new_height} ({new_size_mb:.1f}MB)")
                
                return image_path
                
        except Exception as e:
            logger.error(f"Error compressing image {image_path}: {e}")
            return image_path


def main():
    """Main entry point."""
    scraper = None
    try:
        scraper = WeiboScraper()
        scraper.start()
    except KeyboardInterrupt:
        print("\nReceived interrupt signal. Shutting down gracefully...")
    except Exception as e:
        print(f"Fatal error: {e}")
        exit(1)
    finally:
        if scraper:
            try:
                scraper.cleanup()
            except Exception as e:
                print(f"Error during cleanup: {e}")
        print("Bot stopped.")


if __name__ == "__main__":
    main()
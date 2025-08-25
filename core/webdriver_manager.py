from __future__ import annotations

import platform
import logging
import subprocess
import shutil

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

logger = logging.getLogger(__name__)


class WebDriverManager:
    @staticmethod
    def create_driver(headless: bool = True) -> webdriver.Chrome:
        """Create Chrome driver - simplified and reliable"""
        return WebDriverManager._create_chrome_driver(headless)

    @staticmethod
    def _get_chrome_options(headless: bool = True) -> ChromeOptions:
        options = ChromeOptions()
        if headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Additional options to prevent redirect loops and improve stability
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-ipc-flooding-protection')
        
        # Set a realistic user agent
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        except Exception:
            pass
        return options

    @staticmethod
    def _find_chromedriver() -> str:
        """Find ChromeDriver in system PATH or common locations"""
        # First try to use webdriver-manager with the latest version
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            # Use the latest version that should be compatible
            return ChromeDriverManager().install()
        except Exception as e:
            logger.warning(f"Failed to use webdriver-manager: {e}")
        
        # Check if chromedriver is in PATH
        chromedriver_path = shutil.which('chromedriver')
        if chromedriver_path:
            return chromedriver_path
        
        # Check common macOS locations
        common_paths = [
            '/opt/homebrew/bin/chromedriver',
            '/usr/local/bin/chromedriver',
            '/usr/bin/chromedriver'
        ]
        
        for path in common_paths:
            if shutil.which(path):
                return path
        
        # If nothing works, raise an error
        raise Exception("ChromeDriver not found. Please install it manually: brew install --cask chromedriver")
    
    @staticmethod
    def _create_chrome_driver(headless: bool = True) -> webdriver.Chrome:
        """Create Chrome driver with optimized options for Weibo scraping"""
        options = WebDriverManager._get_chrome_options(headless)
        chromedriver_path = WebDriverManager._find_chromedriver()
        
        logger.info(f"Using ChromeDriver at: {chromedriver_path}")
        service = ChromeService(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        
        # Hide webdriver property to avoid detection
        try:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception:
            pass
            
        return driver



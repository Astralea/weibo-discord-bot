from __future__ import annotations

import platform
import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager


logger = logging.getLogger(__name__)


class WebDriverManager:
    @staticmethod
    def create_driver(headless: bool = True) -> webdriver.Remote:
        system = platform.system()
        if system == 'Windows':
            return WebDriverManager._create_windows_driver(headless)
        if system == 'Darwin':
            return WebDriverManager._create_macos_driver(headless)
        if system == 'Linux':
            return WebDriverManager._create_linux_driver(headless)
        raise Exception(f'Unsupported operating system: {system}')

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
        try:
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        except Exception:
            pass
        return options

    @staticmethod
    def _create_windows_driver(headless: bool = True) -> webdriver.Remote:
        try:
            options = WebDriverManager._get_chrome_options(headless)
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            try:
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception:
                pass
            return driver
        except Exception as e:
            logger.warning(f"Failed to create Chrome driver: {e}")
            logger.info("Trying Firefox as fallback...")
            return WebDriverManager._create_firefox_driver(headless)

    @staticmethod
    def _create_macos_driver(headless: bool = True) -> webdriver.Remote:
        try:
            options = FirefoxOptions()
            if headless:
                options.add_argument('--headless')
            options.set_preference('devtools.jsonview.enabled', False)
            return webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
        except Exception as e:
            logger.warning(f"Failed to create Firefox driver: {e}")
            logger.info("Trying Chrome as fallback...")
            return WebDriverManager._create_chrome_driver(headless)

    @staticmethod
    def _create_linux_driver(headless: bool = True) -> webdriver.Remote:
        try:
            options = WebDriverManager._get_chrome_options(headless)
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            try:
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception:
                pass
            return driver
        except Exception as e:
            logger.warning(f"Failed to create Chrome driver: {e}")
            logger.info("Trying Firefox as fallback...")
            return WebDriverManager._create_firefox_driver(headless)

    @staticmethod
    def _create_chrome_driver(headless: bool = True) -> webdriver.Chrome:
        options = WebDriverManager._get_chrome_options(headless)
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        try:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception:
            pass
        return driver

    @staticmethod
    def _create_firefox_driver(headless: bool = True) -> webdriver.Remote:
        options = FirefoxOptions()
        if headless:
            options.add_argument('--headless')
        options.set_preference('devtools.jsonview.enabled', False)
        service = FirefoxService(GeckoDriverManager().install())
        return webdriver.Firefox(service=service, options=options)



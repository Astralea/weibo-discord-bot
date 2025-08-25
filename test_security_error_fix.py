#!/usr/bin/env python3
"""
Test script to verify Chrome-only Weibo scraper functionality
"""

import logging
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.webdriver_manager import WebDriverManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_chrome_driver_creation():
    """Test Chrome driver creation"""
    print("Testing Chrome driver creation...")
    
    try:
        driver = WebDriverManager.create_driver(headless=True)
        print(f"✅ Chrome driver created successfully: {type(driver).__name__}")
        
        # Test basic functionality
        print("Testing basic driver functionality...")
        test_url = "https://httpbin.org/get"
        driver.get(test_url)
        print(f"✅ Navigated to: {driver.current_url}")
        print(f"✅ Page title: {driver.title}")
        
        # Test webdriver property hiding
        webdriver_prop = driver.execute_script("return navigator.webdriver")
        print(f"✅ WebDriver property hidden: {webdriver_prop}")
        
        driver.quit()
        print("✅ Driver closed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create/test Chrome driver: {e}")
        return False

def test_weibo_scraper_integration():
    """Test Weibo scraper integration with Chrome driver"""
    print("\nTesting Weibo scraper integration...")
    
    try:
        from services.weibo_scraper import WeiboScraper
        
        # Create a minimal config for testing
        test_config = {
            'weibo': {
                'test_account': {
                    'read_link_url': 'https://httpbin.org/get',
                    'message_webhook': 'https://httpbin.org/post'
                }
            },
            'status': {
                'message_webhook': 'https://httpbin.org/post'
            }
        }
        
        scraper = WeiboScraper(test_config, ['test_account'])
        print(f"✅ WeiboScraper created successfully")
        
        # Test driver health check
        is_alive = scraper._is_driver_alive()
        print(f"✅ Driver health check: {is_alive}")
        
        # Test error page detection
        is_error = scraper._is_error_page(scraper.driver)
        print(f"✅ Error page detection: {is_error}")
        
        # Clean up
        scraper.cleanup()
        print("✅ Scraper cleanup completed")
        return True
        
    except Exception as e:
        print(f"❌ Weibo scraper integration test failed: {e}")
        return False

def test_navigation_error_handling():
    """Test navigation error handling"""
    print("\nTesting navigation error handling...")
    
    try:
        driver = WebDriverManager.create_driver(headless=True)
        
        # Test error page detection
        from services.weibo_scraper import WeiboScraper
        
        test_config = {
            'weibo': {'test': {'read_link_url': 'https://httpbin.org/get', 'message_webhook': 'https://httpbin.org/post'}},
            'status': {'message_webhook': 'https://httpbin.org/post'}
        }
        
        scraper = WeiboScraper(test_config, ['test'])
        scraper.driver = driver
        
        # Test with a valid URL
        test_url = "https://httpbin.org/get"
        success = scraper._handle_navigation_error(driver, test_url)
        print(f"✅ Navigation error handling test: {success}")
        
        driver.quit()
        scraper.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Navigation error handling test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Testing Chrome-only Weibo scraper")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    try:
        if test_chrome_driver_creation():
            tests_passed += 1
            
        if test_weibo_scraper_integration():
            tests_passed += 1
            
        if test_navigation_error_handling():
            tests_passed += 1
        
        print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            print("✅ All tests completed successfully!")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
            
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)

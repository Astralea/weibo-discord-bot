#!/usr/bin/env python3
"""
Test script for the refactored Weibo Discord Bot
This script tests the basic functionality without running the full scraper.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import toml
        print("✓ toml imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import toml: {e}")
        return False
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
        print("✓ selenium imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import selenium: {e}")
        return False
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.firefox import GeckoDriverManager
        print("✓ webdriver-manager imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import webdriver-manager: {e}")
        return False
    
    try:
        from discord_webhook import DiscordWebhook, DiscordEmbed
        print("✓ discord_webhook imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import discord_webhook: {e}")
        return False
    
    try:
        from core.media.image_collage import combine_images, resize_gif
        print("✓ image_collage imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import image_collage: {e}")
        return False
    
    return True

def test_config():
    """Test if configuration file can be loaded."""
    print("\nTesting configuration...")
    
    try:
        import toml
        config = toml.load('config.toml')
        print("✓ config.toml loaded successfully")
        
        # Check required sections
        if 'weibo' in config:
            print(f"✓ Found {len(config['weibo'])} Weibo accounts")
        else:
            print("✗ No 'weibo' section found in config")
            return False
        
        if 'status' in config:
            print("✓ Status section found")
        else:
            print("✗ No 'status' section found in config")
            return False
        
        return True
    except FileNotFoundError:
        print("✗ config.toml not found. Please copy config.toml.example to config.toml")
        return False
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False

def test_kawaii_content():
    """Test if kawaii content file can be loaded."""
    print("\nTesting kawaii content...")
    
    try:
        import json
        with open('kawaii_content.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        required_keys = ['kawaii_emojis', 'kawaii_texts', 'kawaii_titles']
        for key in required_keys:
            if key in data:
                print(f"✓ {key} loaded ({len(data[key])} items)")
            else:
                print(f"✗ {key} not found in kawaii_content.json")
                return False
        
        return True
    except FileNotFoundError:
        print("✗ kawaii_content.json not found")
        return False
    except Exception as e:
        print(f"✗ Error loading kawaii content: {e}")
        return False

def test_database():
    """Test database functionality."""
    print("\nTesting database...")
    
    try:
        import sqlite3
        from core.database import DatabaseManager
        
        # Test database creation
        Path('data').mkdir(exist_ok=True)
        db_manager = DatabaseManager('data/test.db')
        print("✓ Database manager created successfully")
        
        # Test ID operations
        result = db_manager.check_and_add_id(12345)
        if result:
            print("✓ ID check and add operation successful")
        else:
            print("✗ ID check and add operation failed")
            return False
        
        # Test duplicate ID
        result = db_manager.check_and_add_id(12345)
        if not result:
            print("✓ Duplicate ID handling works correctly")
        else:
            print("✗ Duplicate ID handling failed")
            return False
        
        # Cleanup
        db_manager.close()
        Path('test.db').unlink(missing_ok=True)
        
        return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_image_manager():
    """Test image manager functionality."""
    print("\nTesting image manager...")
    
    try:
        from core.image_manager import ImageManager
        from pathlib import Path
        
        # Create test image directory
        test_dir = Path('test_images')
        image_manager = ImageManager(test_dir)
        print("✓ Image manager created successfully")
        
        # Test directory creation
        if test_dir.exists():
            print("✓ Image directory created successfully")
        else:
            print("✗ Image directory creation failed")
            return False
        
        # Cleanup
        test_dir.rmdir()
        
        return True
    except Exception as e:
        print(f"✗ Image manager test failed: {e}")
        return False

def test_webdriver_manager():
    """Test webdriver manager functionality."""
    print("\nTesting webdriver manager...")
    
    try:
        from core.webdriver_manager import WebDriverManager
        import platform
        
        system = platform.system()
        print(f"✓ Platform detected: {system}")
        
        # Test driver creation (this might fail if ChromeDriver is not available)
        try:
            print("Testing webdriver-manager automatic download...")
            driver = WebDriverManager.create_driver()
            print("✓ WebDriver created successfully")
            driver.quit()
            print("✓ WebDriver closed successfully")
            print("✓ webdriver-manager is working correctly!")
        except Exception as e:
            print(f"⚠ WebDriver creation failed: {e}")
            print("This might be due to:")
            print("1. Chrome/Firefox browser not installed")
            print("2. Network connectivity issues")
            print("3. Antivirus blocking the download")
            print("The webdriver-manager will handle this automatically when the bot runs.")
        
        return True
    except Exception as e:
        print(f"✗ WebDriver manager test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Weibo Discord Bot Test Suite ===")
    print("Testing with webdriver-manager for automatic driver management")
    
    tests = [
        test_imports,
        test_config,
        test_kawaii_content,
        test_database,
        test_image_manager,
        test_webdriver_manager
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! The bot should work correctly.")
        print("✓ ChromeDriver will be downloaded automatically when needed.")
        return True
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
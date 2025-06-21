#!/usr/bin/env python3
"""
Windows setup script for Weibo Discord Bot
This script helps set up the environment and install dependencies for Windows.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 7):
        print("Error: Python 3.7 or higher is required.")
        print(f"Current version: {sys.version}")
        return False
    print(f"✓ Python version: {sys.version.split()[0]}")
    return True

def install_requirements():
    """Install required packages."""
    print("\nInstalling required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error installing requirements: {e}")
        return False

def create_config_file():
    """Create config.toml from example if it doesn't exist."""
    if not Path("config.toml").exists():
        if Path("config_example.toml").exists():
            print("\nCreating config.toml from config_example.toml...")
            import shutil
            shutil.copy("config_example.toml", "config.toml")
            print("✓ config.toml created. Please edit it with your settings.")
            return True
        else:
            print("✗ config_example.toml not found")
            return False
    else:
        print("✓ config.toml already exists")
        return True

def test_selenium():
    """Test if Selenium works with webdriver-manager."""
    print("\nTesting Selenium setup...")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        print("✓ webdriver-manager imported successfully")
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        print("Downloading ChromeDriver automatically...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://www.google.com")
        title = driver.title
        driver.quit()
        
        print(f"✓ Selenium test successful: {title}")
        print("✓ ChromeDriver downloaded and working automatically!")
        return True
    except Exception as e:
        print(f"✗ Selenium test failed: {e}")
        print("This might be due to:")
        print("1. Chrome browser not installed")
        print("2. Network connectivity issues")
        print("3. Antivirus blocking the download")
        return False

def test_imports():
    """Test if all required modules can be imported."""
    print("\nTesting imports...")
    
    try:
        import toml
        print("✓ toml imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import toml: {e}")
        return False
    
    try:
        from selenium import webdriver
        print("✓ selenium imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import selenium: {e}")
        return False
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
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
        from image_collage import combine_images, resize_gif
        print("✓ image_collage imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import image_collage: {e}")
        return False
    
    return True

def main():
    """Main setup function."""
    print("=== Weibo Discord Bot Windows Setup ===")
    print(f"Platform: {platform.system()} {platform.release()}")
    print("Note: ChromeDriver will be downloaded automatically!")
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install requirements
    if not install_requirements():
        return False
    
    # Test imports
    if not test_imports():
        return False
    
    # Create config file
    if not create_config_file():
        return False
    
    # Test Selenium
    if not test_selenium():
        print("\nSelenium test failed. Please check:")
        print("1. Chrome browser is installed")
        print("2. Internet connection is working")
        print("3. Antivirus is not blocking downloads")
        return False
    
    print("\n=== Setup Complete ===")
    print("✓ All dependencies installed successfully")
    print("✓ ChromeDriver will be downloaded automatically when needed")
    print("\nNext steps:")
    print("1. Edit config.toml with your Weibo and Discord settings")
    print("2. Run: python app.py")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\nSetup failed. Please check the errors above.")
        sys.exit(1) 
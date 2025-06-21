@echo off
echo ========================================
echo Weibo Discord Bot - Windows Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher from https://python.org
    pause
    exit /b 1
)

echo Python found. Running setup script...
echo.

REM Run the Python setup script
python setup_windows.py

if errorlevel 1 (
    echo.
    echo Setup failed. Please check the errors above.
    pause
    exit /b 1
)

echo.
echo Setup completed successfully!
echo.
echo Next steps:
echo 1. Edit config.toml with your Weibo and Discord settings
echo 2. Run: python app.py
echo.
pause 
@echo off
echo ========================================
echo Weibo Discord Bot
echo ========================================
echo.

REM Check if config.toml exists
if not exist "config.toml" (
    echo Error: config.toml not found
    echo Please run setup_windows.bat first or copy config_example.toml to config.toml
    pause
    exit /b 1
)

echo Starting Weibo Discord Bot...
echo Press Ctrl+C to stop
echo.

REM Run the bot
python app.py

pause 
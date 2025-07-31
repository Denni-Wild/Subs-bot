@echo off
echo Installing YouTube Subtitle Bot dependencies...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

REM Install FFmpeg if not already installed
echo.
echo Checking FFmpeg installation...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo FFmpeg not found. Installing...
    winget install ffmpeg
    echo.
    echo Please restart your terminal after FFmpeg installation
    echo Then run: .venv\Scripts\Activate.ps1
    echo And test with: python test_ffmpeg.py
) else (
    echo FFmpeg is already installed.
)

echo.
echo Installation complete!
echo To start the bot, run: python bot.py
echo To test FFmpeg, run: python test_ffmpeg.py
pause 
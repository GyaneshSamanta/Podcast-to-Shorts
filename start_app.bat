@echo off
cd /d "%~dp0"
echo =========================================
echo Starting Podcast-to-Shorts Engine...
echo (It may take a few seconds to load the AI models)
echo =========================================
call venv\Scripts\activate.bat
python main.py
if %errorlevel% neq 0 (
    echo.
    echo An error occurred while running the application.
    pause
)

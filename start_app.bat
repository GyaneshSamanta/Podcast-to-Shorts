@echo off
cd /d "%~dp0.."
echo Starting Podcast-to-Shorts...
call venv\Scripts\activate.bat
python main.py

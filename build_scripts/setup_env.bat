@echo off
echo Setting up virtual environment...
python -m venv venv
call venv\Scripts\activate.bat
echo Upgrading pip...
python -m pip install --upgrade pip
echo Installing requirements...
pip install -r requirements.txt
echo Environment setup complete!
pause

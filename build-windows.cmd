@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv || exit /b 1
.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller || exit /b 1
set PLAYWRIGHT_BROWSERS_PATH=0
.venv\Scripts\python.exe -m playwright install chromium || exit /b 1
.venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --name ClickerBot --collect-all playwright --collect-all keyring --add-data "capture.js;." --add-data "logo.png;." --add-data "mascot;mascot" app.py || exit /b 1
echo dist\ClickerBot.exe

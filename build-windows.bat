@echo off
REM Double-click on Windows to build a standalone AARPO Metronome executable.
REM Produces dist\aarpo-metronome.exe — runs without Python installed.
setlocal
cd /d "%~dp0"

where py >nul 2>nul && (set "PY=py") || (set "PY=python")

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import textual, pygame, PyInstaller" >nul 2>nul && goto have_venv
)

echo Setting up build environment...
if exist ".venv" rmdir /s /q ".venv"
%PY% -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt pyinstaller
goto build

:have_venv
call ".venv\Scripts\activate.bat"

:build
python build.py

echo.
echo Build complete:  dist\aarpo-metronome.exe
echo Double-click it to start - no Python needed.
pause
endlocal
